class_name CoreBridge
extends Node

signal response_ready(payload: Dictionary)

signal preview_ready(payload: Dictionary)
signal preview_failed(error: Dictionary)
signal event_received(payload: Dictionary)
signal explanation_ready(payload: Dictionary, generation: int)
signal explanation_failed(error: Dictionary, generation: int)
signal explanation_cancelled(generation: int)

const MAX_DIAGNOSTIC_CHARS := 65536

var _preview_thread: Thread
var _process_data: Dictionary = {}
var _saw_terminal_event := false
var _pending_terminal_event: Dictionary = {}
var _explain_data: Dictionary = {}
var _explain_stdout := ""
var _explain_stderr := ""
var _explain_generation := 0


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
		var parsed = JSON.parse_string(lines[index])
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
	_read_available_lines()
	if OS.is_process_running(_process_data["pid"]):
		return
	_read_available_lines()
	var exit_code := OS.get_process_exit_code(_process_data["pid"])
	var stderr_text: String = _process_data["stderr"].get_as_text()
	if not _pending_terminal_event.is_empty() and (exit_code == 0 or _pending_terminal_event.get("event") != "completed"):
		var terminal_event := _pending_terminal_event
		_cleanup_process()
		event_received.emit(terminal_event)
		return
	if exit_code != 0 or not _saw_terminal_event:
		_cleanup_process()
		event_received.emit(
			{
				"schema_version": "1.0",
				"event": "failed",
				"progress": 0.0,
				"error": {"code": "process_failed", "message": stderr_text if not stderr_text.is_empty() else "Process exited without a valid completion event."},
			}
		)
	else:
		_cleanup_process()


func start_explanation(arguments: PackedStringArray, command_override := PackedStringArray()) -> bool:
	if is_explaining():
		return false
	var command := PackedStringArray()
	if command_override.is_empty():
		command.append_array(_command_prefix())
		command.append_array(arguments)
	else:
		command = command_override
	_explain_generation += 1
	_explain_stdout = ""
	_explain_stderr = ""
	_explain_data = OS.execute_with_pipe(python_executable(), command, false)
	if _explain_data.is_empty():
		_explain_data = {}
		explanation_failed.emit(
			{
				"code": "process_start_failed",
				"message": "Could not start the PsyML Python process.",
			},
			_explain_generation,
		)
		return false
	set_process(true)
	return true


func explanation_generation() -> int:
	return _explain_generation


func is_explaining() -> bool:
	return not _explain_data.is_empty() and OS.is_process_running(_explain_data["pid"])


func cancel_explanation() -> void:
	if _explain_data.is_empty():
		return
	if OS.is_process_running(_explain_data["pid"]):
		OS.kill(_explain_data["pid"])
	_cleanup_explanation()
	explanation_cancelled.emit(_explain_generation)


func _poll_explanation() -> void:
	var generation := _explain_generation
	_explain_stdout += _drain_fragments(_explain_data["stdio"])
	if _explain_data.has("stderr"):
		_explain_stderr = _bounded_tail(_explain_stderr + _drain_fragments(_explain_data["stderr"]))
	if OS.is_process_running(_explain_data["pid"]):
		return
	# Final tail after exit.
	_explain_stdout += _drain_fragments(_explain_data["stdio"])
	if _explain_data.has("stderr"):
		_explain_stderr = _bounded_tail(_explain_stderr + _drain_fragments(_explain_data["stderr"]))
	var exit_code := OS.get_process_exit_code(_explain_data["pid"])
	_cleanup_explanation()
	if generation != _explain_generation:
		return
	var payload = _parse_complete_json(_explain_stdout)
	if exit_code == 0 and payload is Dictionary:
		explanation_ready.emit(payload, generation)
		return
	var message := _explain_stderr.strip_edges()
	if payload is Dictionary and payload.has("error"):
		message = str(payload.error.get("message", message))
	if message.is_empty():
		message = "Explanation exited without a valid result."
	explanation_failed.emit({"code": "explanation_failed", "message": message}, generation)


func _parse_complete_json(text: String):
	if text.strip_edges().is_empty():
		return null
	var parsed = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	# Fall back to the last complete line (multi-line framing).
	var lines := text.split("\n")
	for index in range(lines.size() - 1, -1, -1):
		if lines[index].strip_edges().is_empty():
			continue
		parsed = JSON.parse_string(lines[index])
		if parsed is Dictionary:
			return parsed
	return null


func _bounded_tail(text: String) -> String:
	if text.length() <= MAX_DIAGNOSTIC_CHARS:
		return text
	return text.substr(text.length() - MAX_DIAGNOSTIC_CHARS)


func _drain_fragments(stream: FileAccess) -> String:
	# Accumulate every available fragment; partial JSON chunks are retained
	# across polls instead of keeping only the last line.
	var buffer := ""
	while true:
		var line := stream.get_line()
		if line.is_empty():
			break
		buffer += line
	return buffer


func _read_available_lines() -> void:
	var stdio: FileAccess = _process_data["stdio"]
	while true:
		var line := stdio.get_line()
		if line.is_empty():
			break
		var payload = JSON.parse_string(line)
		if payload is Dictionary:
			if payload.get("event", "") in ["completed", "failed", "cancelled"]:
				_saw_terminal_event = true
				_pending_terminal_event = payload
			else:
				event_received.emit(payload)


func _cleanup_process() -> void:
	_process_data = {}
	_pending_terminal_event = {}


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
