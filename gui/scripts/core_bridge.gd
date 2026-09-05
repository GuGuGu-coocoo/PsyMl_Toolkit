class_name CoreBridge
extends Node

signal preview_ready(payload: Dictionary)
signal preview_failed(error: Dictionary)
signal event_received(payload: Dictionary)

var _preview_thread: Thread
var _process_data: Dictionary = {}
var _saw_terminal_event := false
var _pending_terminal_event: Dictionary = {}


static func bundle_directory() -> String:
	var directory := OS.get_executable_path().get_base_dir()
	return directory.path_join("../Resources") if OS.get_name() == "macOS" else directory


static func examples_directory() -> String:
	var bundled := bundle_directory().path_join("examples/synthetic")
	if DirAccess.dir_exists_absolute(bundled):
		return bundled
	return ProjectSettings.globalize_path("res://../examples/synthetic")


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
	if _process_data.is_empty():
		set_process(false)
		return
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
	set_process(false)


func _exit_tree() -> void:
	if _preview_thread != null:
		_preview_thread.wait_to_finish()
	if is_running():
		OS.kill(_process_data["pid"])
