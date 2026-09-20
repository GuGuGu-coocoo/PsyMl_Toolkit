class_name CoreBridge
extends Node

signal response_ready(payload: Dictionary)

signal preview_ready(payload: Dictionary)
signal preview_failed(error: Dictionary)
signal event_received(payload: Dictionary)
signal explanation_ready(payload: Dictionary, generation: int)
signal explanation_failed(error: Dictionary, generation: int)
signal explanation_cancelled(generation: int)
signal coefficients_ready(payload: Dictionary, generation: int)
signal coefficients_failed(error: Dictionary, generation: int)
signal coefficients_cancelled(generation: int)

const MAX_DIAGNOSTIC_CHARS := 65536
const PIPE_READ_CHUNK := 4096
const PIPE_READ_ROUNDS := 32
const MAX_STREAM_PENDING_BYTES := 65536

var _preview_thread: Thread
var _process_data: Dictionary = {}
var _saw_terminal_event := false
var _pending_terminal_event: Dictionary = {}
var _analysis_stdout_partial := ""
var _analysis_stdout_pending := PackedByteArray()
var _analysis_stderr_pending := PackedByteArray()
var _analysis_stderr_tail := ""
var _analysis_last_exit_code := -1
var _explain_data: Dictionary = {}
var _explain_stdout := ""
var _explain_stderr := ""
var _explain_stdout_pending := PackedByteArray()
var _explain_stderr_pending := PackedByteArray()
var _explain_generation := 0
var _task_kind := "explanation"


static func canonical_path(path: String) -> String:
	# Canonical form for comparing or showing paths that come back from the
	# core: Windows pathlib emits `\` separators while Godot joins with `/`.
	return path.simplify_path()


static func parse_json_document(text: String):
	# The instance API returns the parse error instead of logging one; the
	# static JSON.parse_string prints engine errors for expected noise lines.
	var json := JSON.new()
	if json.parse(text) != OK:
		return null
	return json.data


static func utf8_complete_prefix_length(buffer: PackedByteArray) -> int:
	# Length of the longest valid UTF-8 prefix; a short trailing multi-byte
	# sequence stays buffered so decoding never emits replacement characters.
	var size := buffer.size()
	if size == 0:
		return 0
	var index := size - 1
	var scanned := 0
	while index >= 0 and scanned < 4:
		var byte := buffer[index]
		if byte & 0xC0 == 0x80:
			index -= 1
			scanned += 1
			continue
		var expected := 1
		if byte & 0xE0 == 0xC0:
			expected = 2
		elif byte & 0xF0 == 0xE0:
			expected = 3
		elif byte & 0xF8 == 0xF0:
			expected = 4
		if size - index < expected:
			return index
		return size
	return size


static func bundle_directory() -> String:
	var directory := OS.get_executable_path().get_base_dir()
	return directory.path_join("../Resources") if OS.get_name() == "macOS" else directory


static func examples_directory() -> String:
	var bundled := bundle_directory().path_join("examples/synthetic")
	if DirAccess.dir_exists_absolute(bundled):
		return bundled
	return ProjectSettings.globalize_path("res://../examples/synthetic")


static func quickstart_directory() -> String:
	var bundled := bundle_directory().path_join("examples/quickstart")
	if DirAccess.dir_exists_absolute(bundled):
		return bundled
	var source := ProjectSettings.globalize_path("res://../examples/quickstart")
	return source if DirAccess.dir_exists_absolute(source) else examples_directory()


func _command_prefix() -> PackedStringArray:
	return PackedStringArray([]) if FileAccess.file_exists(_bundled_core()) else PackedStringArray(["-m", "psyml"])


func _bundled_core() -> String:
	return bundle_directory().path_join("core/psyml-core.exe" if OS.get_name() == "Windows" else "core/psyml-core")


func python_executable() -> String:
	if FileAccess.file_exists(_bundled_core()):
		return _bundled_core()
	if OS.has_environment("PSYML_PYTHON"):
		return OS.get_environment("PSYML_PYTHON")
	return "python" if OS.get_name() == "Windows" else "python3"


func execute_json_sync(arguments: PackedStringArray) -> Dictionary:
	var output: Array = []
	var command := _command_prefix()
	command.append_array(arguments)
	var exit_code := OS.execute(python_executable(), command, output, true)
	var combined := "\n".join(output)
	var lines := combined.split("\n", false)
	for index in range(lines.size() - 1, -1, -1):
		var parsed = parse_json_document(lines[index])
		if parsed is Dictionary:
			if exit_code != 0 and not parsed.has("error"):
				return {"error": {"code": "process_failed", "message": combined}}
			return parsed
	return {"error": {"code": "invalid_response", "message": combined}}


func request_preview(path: String, include_sample := true) -> void:
	if _preview_thread != null and _preview_thread.is_started():
		return
	_preview_thread = Thread.new()
	_preview_thread.start(_preview_worker.bind(path, include_sample))


func _preview_worker(path: String, include_sample: bool) -> void:
	var arguments := PackedStringArray(["preview", "--input", path, "--rows", "5"])
	if include_sample:
		arguments.append("--include-sample")
	var payload := execute_json_sync(arguments)
	call_deferred("_finish_preview", payload)


func _finish_preview(payload: Dictionary) -> void:
	if _preview_thread != null:
		_preview_thread.wait_to_finish()
		_preview_thread = null
	if payload.has("error"):
		preview_failed.emit(payload["error"])
	else:
		preview_ready.emit(payload)


func start_analysis(config_path: String) -> bool:
	if is_running():
		return false
	var arguments := _command_prefix()
	arguments.append_array(["run", "--config", config_path, "--events"])
	_process_data = OS.execute_with_pipe(python_executable(), arguments, false)
	if _process_data.is_empty():
		event_received.emit(
			{
				"schema_version": "1.0",
				"event": "failed",
				"progress": 0.0,
				"error": {
					"code": "process_start_failed",
					"message": "Could not start the PsyML Python process."
				},
			}
		)
		return false
	_saw_terminal_event = false
	_pending_terminal_event = {}
	_analysis_stdout_partial = ""
	_analysis_stdout_pending = PackedByteArray()
	_analysis_stderr_pending = PackedByteArray()
	_analysis_stderr_tail = ""
	_analysis_last_exit_code = -1
	set_process(true)
	return true


func is_running() -> bool:
	return not _process_data.is_empty() and OS.is_process_running(_process_data["pid"])


func cancel_analysis() -> void:
	if _process_data.is_empty():
		return
	if OS.is_process_running(_process_data["pid"]):
		OS.kill(_process_data["pid"])
	_cleanup_process()
	event_received.emit(
		{
			"schema_version": "1.0",
			"event": "cancelled",
			"progress": 0.0,
			"error": {
				"code": "cancelled",
				"type": "CancellationRequested",
				"message": "Analysis cancelled by the user."
			},
		}
	)


func _process(_delta: float) -> void:
	if not _process_data.is_empty():
		_poll_analysis()
	if not _explain_data.is_empty():
		_poll_explanation()
	if _process_data.is_empty() and _explain_data.is_empty():
		set_process(false)


func _poll_analysis() -> void:
	_drain_analysis_streams()
	if _process_data.is_empty():
		return
	if OS.is_process_running(_process_data["pid"]):
		return
	# Final drain after exit; a closed pipe simply returns no bytes.
	_drain_analysis_streams()
	var exit_code := OS.get_process_exit_code(_process_data["pid"])
	_analysis_last_exit_code = exit_code
	if not _pending_terminal_event.is_empty() and (exit_code == 0 or _pending_terminal_event.get("event") != "completed"):
		var terminal_event := _pending_terminal_event
		_cleanup_process()
		event_received.emit(terminal_event)
		return
	if exit_code != 0 or not _saw_terminal_event:
		_cleanup_process()
		var stderr_text := _analysis_stderr_tail
		var message := stderr_text if not stderr_text.strip_edges().is_empty() else "Process exited without a valid completion event."
		event_received.emit(
			{
				"schema_version": "1.0",
				"event": "failed",
				"progress": 0.0,
				"error": {"code": "process_failed", "message": message},
			}
		)
	else:
		_cleanup_process()


func start_explanation(arguments: PackedStringArray, command_override := PackedStringArray()) -> bool:
	return _start_task("explanation", arguments, command_override)


func start_coefficients(arguments: PackedStringArray, command_override := PackedStringArray()) -> bool:
	return _start_task("coefficients", arguments, command_override)


func _start_task(kind: String, arguments: PackedStringArray, command_override := PackedStringArray()) -> bool:
	if is_explaining():
		return false
	_task_kind = kind
	var command := PackedStringArray()
	if command_override.is_empty():
		command.append_array(_command_prefix())
		command.append_array(arguments)
	else:
		command = command_override
	_explain_generation += 1
	_explain_stdout = ""
	_explain_stderr = ""
	_explain_stdout_pending = PackedByteArray()
	_explain_stderr_pending = PackedByteArray()
	_explain_data = OS.execute_with_pipe(python_executable(), command, false)
	if _explain_data.is_empty():
		_explain_data = {}
		_fail_task(
			{
				"code": "process_start_failed",
				"message": "Could not start the PsyML Python process.",
			},
			_explain_generation,
		)
		return false
	set_process(true)
	return true


func _fail_task(error: Dictionary, generation: int) -> void:
	if _task_kind == "coefficients":
		coefficients_failed.emit(error, generation)
	else:
		explanation_failed.emit(error, generation)


func explanation_generation() -> int:
	return _explain_generation


func is_explaining() -> bool:
	return not _explain_data.is_empty() and OS.is_process_running(_explain_data["pid"])


func cancel_explanation() -> void:
	if _explain_data.is_empty():
		return
	var kind := _task_kind
	if OS.is_process_running(_explain_data["pid"]):
		OS.kill(_explain_data["pid"])
	_cleanup_explanation()
	if kind == "coefficients":
		coefficients_cancelled.emit(_explain_generation)
	else:
		explanation_cancelled.emit(_explain_generation)


func _poll_explanation() -> void:
	var generation := _explain_generation
	_drain_explanation_streams()
	if OS.is_process_running(_explain_data["pid"]):
		return
	# Final tail after exit.
	_drain_explanation_streams()
	var exit_code := OS.get_process_exit_code(_explain_data["pid"])
	_cleanup_explanation()
	if generation != _explain_generation:
		return
	var payload = _parse_complete_json(_explain_stdout)
	if exit_code == 0 and payload is Dictionary:
		if _task_kind == "coefficients":
			coefficients_ready.emit(payload, generation)
		else:
			explanation_ready.emit(payload, generation)
		return
	var message := _explain_stderr.strip_edges()
	if payload is Dictionary and payload.has("error"):
		message = str(payload.error.get("message", message))
	if message.is_empty():
		message = "Explanation exited without a valid result."
	# Bounded diagnostics (no payload content) make platform-specific framing
	# failures actionable from CI logs alone.
	_fail_task(
		{
			"code": "explanation_failed",
			"message": message,
			"exit_code": exit_code,
			"stdout_chars": _explain_stdout.length(),
			"stderr_chars": _explain_stderr.length(),
			"stdout_parsed": payload is Dictionary,
		},
		generation,
	)


func _parse_complete_json(text: String):
	if text.strip_edges().is_empty():
		return null
	var parsed = parse_json_document(text)
	if parsed is Dictionary:
		return parsed
	# Fall back to the last complete line (multi-line framing).
	var lines := text.split("\n")
	for index in range(lines.size() - 1, -1, -1):
		if lines[index].strip_edges().is_empty():
			continue
		parsed = parse_json_document(lines[index])
		if parsed is Dictionary:
			return parsed
	return null


func _bounded_tail(text: String) -> String:
	if text.length() <= MAX_DIAGNOSTIC_CHARS:
		return text
	return text.substr(text.length() - MAX_DIAGNOSTIC_CHARS)


func _read_stream_text(stream: FileAccess, pending: PackedByteArray) -> Dictionary:
	# Non-blocking byte reads. Pipes must never use get_as_text()/get_length():
	# on Windows those call PeekNamedPipe and print engine errors once the
	# writer has closed, and get_line() can drop a fragment without newline.
	var collected := PackedByteArray()
	for _round in range(PIPE_READ_ROUNDS):
		var chunk := stream.get_buffer(PIPE_READ_CHUNK)
		if chunk.is_empty():
			break
		collected.append_array(chunk)
	if not collected.is_empty():
		pending.append_array(collected)
	var text := ""
	if not pending.is_empty():
		var complete := utf8_complete_prefix_length(pending)
		if complete > 0:
			text = pending.slice(0, complete).get_string_from_utf8()
			pending = pending.slice(complete)
		if pending.size() > MAX_STREAM_PENDING_BYTES:
			pending = pending.slice(pending.size() - MAX_STREAM_PENDING_BYTES)
	return {"text": text, "pending": pending}


func _drain_analysis_stdout() -> void:
	var read := _read_stream_text(_process_data["stdio"], _analysis_stdout_pending)
	_analysis_stdout_pending = read["pending"]
	var text := str(read["text"])
	if not text.is_empty():
		_consume_analysis_stdout(text)


func _consume_analysis_stdout(text: String) -> void:
	# Buffer partial writes so a JSON event is only parsed when its line
	# arrived completely, including the last event before the process exits.
	_analysis_stdout_partial = _bounded_tail(_analysis_stdout_partial + text)
	while true:
		var newline := _analysis_stdout_partial.find("\n")
		if newline < 0:
			break
		var line := _analysis_stdout_partial.substr(0, newline)
		_analysis_stdout_partial = _analysis_stdout_partial.substr(newline + 1)
		_dispatch_analysis_line(line)


func _dispatch_analysis_line(line: String) -> void:
	var payload = parse_json_document(line)
	if not payload is Dictionary:
		return
	if payload.get("event", "") in ["completed", "failed", "cancelled"]:
		_saw_terminal_event = true
		_pending_terminal_event = payload
	else:
		event_received.emit(payload)


func _drain_analysis_stderr() -> void:
	var read := _read_stream_text(_process_data["stderr"], _analysis_stderr_pending)
	_analysis_stderr_pending = read["pending"]
	var text := str(read["text"])
	if not text.is_empty():
		_analysis_stderr_tail = _bounded_tail(_analysis_stderr_tail + text)


func _drain_analysis_streams() -> void:
	_drain_analysis_stdout()
	if _process_data.has("stderr"):
		_drain_analysis_stderr()


func _drain_explanation_streams() -> void:
	var stdout_read := _read_stream_text(_explain_data["stdio"], _explain_stdout_pending)
	_explain_stdout_pending = stdout_read["pending"]
	var stdout_text := str(stdout_read["text"])
	if not stdout_text.is_empty():
		_explain_stdout += stdout_text
	if _explain_data.has("stderr"):
		var stderr_read := _read_stream_text(_explain_data["stderr"], _explain_stderr_pending)
		_explain_stderr_pending = stderr_read["pending"]
		var stderr_text := str(stderr_read["text"])
		if not stderr_text.is_empty():
			_explain_stderr = _bounded_tail(_explain_stderr + stderr_text)


func _cleanup_process() -> void:
	_process_data = {}
	_pending_terminal_event = {}
	_analysis_stdout_partial = ""
	_analysis_stdout_pending = PackedByteArray()
	_analysis_stderr_pending = PackedByteArray()


func last_process_exit_code() -> int:
	return _analysis_last_exit_code


func last_stderr_tail(limit: int = 4000) -> String:
	if limit <= 0 or _analysis_stderr_tail.length() <= limit:
		return _analysis_stderr_tail
	return _analysis_stderr_tail.substr(_analysis_stderr_tail.length() - limit)


func _cleanup_explanation() -> void:
	_explain_data = {}


func _exit_tree() -> void:
	if _preview_thread != null:
		_preview_thread.wait_to_finish()
	if is_running():
		OS.kill(_process_data["pid"])
	if not _explain_data.is_empty() and OS.is_process_running(_explain_data["pid"]):
		OS.kill(_explain_data["pid"])


func request_json(arguments: PackedStringArray) -> void:
	if _preview_thread != null:
		return
	_preview_thread = Thread.new()
	_preview_thread.start(_json_worker.bind(arguments))


func _json_worker(arguments: PackedStringArray) -> void:
	var payload := execute_json_sync(arguments)
	call_deferred("_finish_json", payload)


func _finish_json(payload: Dictionary) -> void:
	_preview_thread.wait_to_finish()
	_preview_thread = null
	response_ready.emit(payload)
