extends SceneTree
## GUI end-to-end for the single-sample explanation section: prepare, run,
## cancel, failure cleanup, artifact delivery/persistence, context guards,
## language switching and the nonblocking bridge framing.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_run")


func _expect(condition: bool, message: String = "assertion failed") -> void:
	if not condition:
		printerr("PSYML_EXPLANATION_UI_FAILURE: " + message)
		quit(1)


func _write(path: String, content: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(content)
	file.close()


func _file_size(path: String) -> int:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return -1
	var length := file.get_length()
	file.close()
	return length


func _user_output_state() -> Dictionary:
	# Snapshot the hidden application-data folders with a bounded depth so a
	# failed operation can be checked to not have fallen back there.
	var state := {}
	for family in ["prediction", "explanation", "coefficients"]:
		_collect_user_files(ProjectSettings.globalize_path("user://" + family), family, state, 0)
	return state


func _collect_user_files(path: String, label: String, state: Dictionary, depth: int) -> void:
	var directory := DirAccess.open(path)
	if directory == null:
		return
	for name in directory.get_files():
		state[label.path_join(name)] = _file_size(path.path_join(name))
	if depth >= 3:
		return
	for name in directory.get_directories():
		_collect_user_files(path.path_join(name), label.path_join(name), state, depth + 1)


func _wait_busy(page) -> void:
	var deadline := Time.get_ticks_msec() + 30000
	while page.busy and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	_expect(not page.busy, "Prediction operation timed out")


func _wait_explain(page) -> void:
	var deadline := Time.get_ticks_msec() + 180000
	while page.explain_busy and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	_expect(not page.explain_busy, "Explanation timed out")


func _run() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var page = main.prediction_page
	# Page 4 writes into the page-2 result root: a Chinese path with spaces.
	var output_root := TestPaths.temp_dir().path_join("psyml 输出 解释 %d" % Time.get_ticks_usec())
	page.set_output_root(output_root)
	_expect(main.output_edit.text == output_root)
	_expect(page.output_edit.text == output_root)
	var directory := TestPaths.temp_dir().path_join("psyml-explain-ui-%d" % Time.get_ticks_usec())
	DirAccess.make_dir_recursive_absolute(directory)
	var input := ProjectSettings.globalize_path("res://../examples/quickstart/classification_train.csv")
	var predict_input := ProjectSettings.globalize_path("res://../examples/quickstart/classification_predict.csv")
	var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../examples/quickstart/classification_config.json"))
	config.input_path = input
	config.output_dir = directory.path_join("run")
	config.figure_types = []
	for field in ["n_splits", "random_seed", "inner_splits", "max_candidates"]:
		if config.has(field):
			config[field] = int(config[field])
	config.model_name = "logistic_regression"
	config.model_names = ["logistic_regression"]
	config.tuning_mode = "none"
	config.parameter_grids = {}
	var config_path := directory.path_join("config.json")
	_write(config_path, JSON.stringify(config))
	var response: Dictionary = main.bridge.execute_json_sync(PackedStringArray(["run", "--config", config_path]))
	_expect(not response.has("error"), str(response))
	var model_path: String = str(config.output_dir).path_join(response.model_export.model_path)

	page.trust.button_pressed = true
	page.load_model(model_path)
	await _wait_busy(page)
	page.load_data(predict_input)
	await _wait_busy(page)
	_expect(page.compatibility.compatible and not page.metadata.is_empty())

	# A background file is mandatory before running.
	page.run_explanation()
	_expect(not page.explain_error.is_empty(), "missing background must be reported")
	page.load_background(predict_input)
	_expect(page.explain_error.is_empty())
	page.explain_class.select(0)
	# A missing or unwritable root is a visible error; never a user:// fallback.
	var user_before := _user_output_state()
	page.set_output_root("")
	page.run_explanation()
	_expect(page.explain_error == main.tr("PREDICTION_OUTPUT_REQUIRED"), page.explain_error)
	_expect(not page.explain_busy and page.explanation.is_empty())
	page.explain_error = ""
	var blocked_root := directory.path_join("blocked-root")
	_write(blocked_root, "not a directory")
	page.set_output_root(blocked_root)
	page.run_explanation()
	_expect(page.explain_error == main.tr("OUTPUT_NOT_WRITABLE"), page.explain_error)
	_expect(not page.explain_busy)
	_expect(_user_output_state() == user_before, "explanation must not fall back to user://")
	page.set_output_root(output_root)
	page.explain_error = ""
	# The background path label must stay on one line: a wrapped/auto-wrapping label
	# inside the control row is the layout bug that squeezed the path into a column.
	# Check both a normal 1280-wide window and a narrower one.
	for width in [1280, 900]:
		root.size = Vector2i(width, 800)
		await process_frame
		await process_frame
		_expect(page.background_label.get_line_count() <= 1,
			"background path label wrapped at width %d" % width)
		_expect(page.background_label.size.x >= 100.0,
			"background path label collapsed to a column at width %d" % width)
		_expect(page.background_label.size.y < 60.0,
			"background path label grew vertically at width %d" % width)
		_expect(page.background_button.size.y < 60.0,
			"background button stretched at width %d" % width)
	root.size = Vector2i(1280, 1000)
	await process_frame
	_expect(not page.explain_button.disabled, "explain should be enabled once ready")
	_expect(page.explain_class_box.visible and page.explain_class.item_count >= 2)
	page.explain_row.value = 1
	page.explain_cycles.value = 2
	page.explain_background_size.value = 10
	page.explain_class.select(0)

	# Successful run renders contributions and clears old state first.
	page.run_explanation()
	_expect(page.explain_busy)
	await _wait_explain(page)
	_expect(page.explain_error.is_empty(), page.explain_error)
	_expect(not page.explanation.is_empty())
	_expect(page.explanation.task == "classification")
	_expect(page.explain_tree.get_root().get_first_child() != null)
	_expect(page.explain_summary.text.contains("基值") or page.explain_summary.text.contains("Base") or page.explain_summary.text.contains("Base"))
	# All four artifacts are delivered and reachable from the UI.
	for key in ["json", "csv", "png", "notes"]:
		_expect(page.explain_artifacts.has(key), "missing artifact " + key)
		_expect(FileAccess.file_exists(str(page.explain_artifacts[key])), str(page.explain_artifacts))
	# FR-014: they really live under the selected root, inside a new
	# explanation/run_* folder owned by this operation.
	_expect(page.explain_output_dir.begins_with(output_root + "/"), page.explain_output_dir)
	_expect(page.explain_output_dir.get_base_dir() == output_root.path_join("explanation"), page.explain_output_dir)
	_expect(page.explain_output_dir.get_file().begins_with("run_"), page.explain_output_dir)
	for key in ["json", "csv", "png", "notes"]:
		_expect(
			str(page.explain_artifacts[key]).begins_with(page.explain_output_dir + "/"),
			str(page.explain_artifacts[key]))
	_expect(not page.explain_open_button.disabled)
	_expect(not page.explain_folder_button.disabled)
	_expect(not page.explain_export_button.disabled)
	_expect(page.explain_view.texture != null, "waterfall image should be displayed")

	# Export into a new directory delivers all four artifacts and reports success.
	var export_dir := directory.path_join("exported")
	page.export_explanation(export_dir)
	_expect(page.explain_error.is_empty(), page.explain_error)
	_expect(not page.explain_note.is_empty(), "export must report success")
	for key in ["json", "csv", "png", "notes"]:
		var name := str(page.explain_artifacts[key]).get_file()
		_expect(FileAccess.file_exists(export_dir.path_join(name)), "export missing " + name)

	# A destination holding a same-named CSV, model or background file must not be
	# overwritten; export falls back to a unique new subdirectory and keeps the
	# original file content byte-for-byte.
	var occupied := directory.path_join("occupied")
	DirAccess.make_dir_recursive_absolute(occupied)
	_write(occupied.path_join("shap_contributions.csv"), "USER_EXISTING_CSV")
	_write(occupied.path_join(model_path.get_file()), "USER_MODEL_FILE")
	_write(occupied.path_join(predict_input.get_file()), "USER_BACKGROUND_FILE")
	page.export_explanation(occupied)
	_expect(page.explain_error.is_empty(), page.explain_error)
	_expect(FileAccess.get_file_as_string(occupied.path_join("shap_contributions.csv")) == "USER_EXISTING_CSV", "existing CSV was overwritten")
	_expect(FileAccess.get_file_as_string(occupied.path_join(model_path.get_file())) == "USER_MODEL_FILE", "existing model file changed")
	_expect(FileAccess.get_file_as_string(occupied.path_join(predict_input.get_file())) == "USER_BACKGROUND_FILE", "existing background file changed")
	var subdirectories := DirAccess.open(occupied).get_directories()
	_expect(subdirectories.size() == 1, "expected a single unique export subdirectory")
	for key in ["json", "csv", "png", "notes"]:
		var name := str(page.explain_artifacts[key]).get_file()
		_expect(FileAccess.file_exists(occupied.path_join(subdirectories[0]).path_join(name)), "subdirectory export missing " + name)

	# Exporting into the current source directory is refused and changes nothing.
	var source_csv := str(page.explain_artifacts["csv"])
	var source_before := FileAccess.get_file_as_string(source_csv)
	page.export_explanation(source_csv.get_base_dir())
	_expect(not page.explain_error.is_empty(), "same-source export must be reported")
	_expect(FileAccess.get_file_as_string(source_csv) == source_before, "source artifact changed")
	_expect(page.explain_note.is_empty(), "same-source export must not claim success")
	for key in ["json", "csv", "png", "notes"]:
		_expect(FileAccess.file_exists(str(page.explain_artifacts[key])), "source artifact removed")

	# A missing source artifact is refused before anything is written.
	var notes_path := str(page.explain_artifacts["notes"])
	page.explain_artifacts.erase("notes")
	var blocked := directory.path_join("blocked")
	page.export_explanation(blocked)
	_expect(not page.explain_error.is_empty(), "missing source must be reported")
	_expect(not DirAccess.dir_exists_absolute(blocked), "missing source must not create the destination")
	page.explain_artifacts["notes"] = notes_path

	# A destination that is an existing file (copy failure) preserves that file
	# and reports an error instead of success.
	var file_target := directory.path_join("not_a_directory")
	_write(file_target, "OCCUPYING_FILE")
	page.export_explanation(file_target)
	_expect(not page.explain_error.is_empty(), "copy failure must be reported")
	_expect(FileAccess.get_file_as_string(file_target) == "OCCUPYING_FILE", "existing file was changed")
	_expect(page.explain_note.is_empty(), "copy failure must not claim success")

	# Changing row/class/settings clears the on-screen result but preserves files.
	var kept_png := str(page.explain_artifacts["png"])
	page.explain_cycles.value = 3
	_expect(page.explanation.is_empty() and page.explain_artifacts.is_empty())
	_expect(FileAccess.file_exists(kept_png), "completed artifacts must not be deleted")
	_expect(page.explain_view.texture == null)

	# Context changes are blocked while an explanation is running.
	page.explain_background_size.value = 10
	page.run_explanation()
	_expect(page.explain_busy)
	var original_input: String = page.input_path
	var original_model: String = page.model_path
	page.load_data(input)
	page.load_model(model_path)
	page.confirm_mapping()
	page.run_prediction()
	_expect(page.input_path == original_input and page.model_path == original_model)
	_expect(page.background_button.disabled, "background change must be blocked while running")
	await _wait_explain(page)
	_expect(page.explain_error.is_empty(), page.explain_error)
	_expect(not page.explanation.is_empty())

	# Cancel terminates only this subprocess and clears the result; immediate restart works.
	var earlier_png := str(page.explain_artifacts["png"])
	var earlier_dir: String = page.explain_output_dir
	page.run_explanation()
	_expect(page.explain_busy)
	await create_timer(.15).timeout
	page.cancel_explanation()
	await create_timer(.2).timeout
	_expect(not page.explain_busy)
	_expect(page.explanation.is_empty())
	_expect(FileAccess.file_exists(earlier_png), "cancelling must not delete earlier artifacts")
	var later_root := TestPaths.temp_dir().path_join("psyml 换目录 解释 %d" % Time.get_ticks_usec())
	page.set_output_root(later_root)
	page.run_explanation()
	await _wait_explain(page)
	_expect(page.explain_error.is_empty(), page.explain_error)
	_expect(not page.explanation.is_empty())
	_expect(page.explain_output_dir.begins_with(later_root + "/"), page.explain_output_dir)
	_expect(page.explain_output_dir != earlier_dir, "a later run must use its own new folder")
	_expect(FileAccess.file_exists(earlier_png), "a later run must not remove earlier artifacts")

	# Incompatible background fails cleanly without leaving results.
	var bad := directory.path_join("bad.csv")
	_write(bad, "unrelated\n1\n2\n")
	page.load_background(bad)
	_expect(page.explanation.is_empty() and page.explain_error.is_empty())
	page.run_explanation()
	await _wait_explain(page)
	_expect(not page.explain_error.is_empty())
	_expect(page.explanation.is_empty())
	_expect(page.explain_artifacts.is_empty())

	# Switching language must not raise and keeps the section readable.
	for locale in range(3):
		main._on_language_selected(locale)
		_expect(page.explain_status.text.length() > 0)

	await _test_bridge_framing(main)
	print("PSYML_EXPLANATION_UI_OK")
	quit(0)


func _test_bridge_framing(main) -> void:
	var bridge = main.bridge
	var ready := {"payload": {}}
	var failure := {"error": {}}
	bridge.explanation_ready.connect(func(payload: Dictionary, _generation: int):
		ready["payload"] = payload)
	bridge.explanation_failed.connect(func(error: Dictionary, _generation: int):
		failure["error"] = error)

	# Chunked stdout plus a large stderr must still yield the complete payload.
	var script := "import sys, time\n"
	script += "sys.stderr.write('E' * 200000)\n"
	script += "sys.stderr.flush()\n"
	script += "payload = '{\"schema_version\": \"1.0\", \"ok\": true, \"chunked\": true}'\n"
	script += "for i in range(0, len(payload), 7):\n"
	script += "    sys.stdout.write(payload[i:i+7])\n"
	script += "    sys.stdout.flush()\n"
	script += "    time.sleep(0.02)\n"
	script += "sys.stdout.write('\\n')\n"
	script += "sys.stdout.flush()\n"
	_expect(bridge.start_explanation(PackedStringArray(), PackedStringArray(["-c", script])))
	var deadline := Time.get_ticks_msec() + 30000
	while ready["payload"].is_empty() and failure["error"].is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	_expect(not ready["payload"].is_empty(), str(failure["error"]))
	_expect(ready["payload"].get("ok", false) and ready["payload"].get("chunked", false))

	# A pure failure with huge stderr is reported as a bounded diagnostic.
	var failing := "import sys\nsys.stderr.write('X' * 200000)\nsys.exit(3)\n"
	_expect(bridge.start_explanation(PackedStringArray(), PackedStringArray(["-c", failing])))
	deadline = Time.get_ticks_msec() + 30000
	while failure["error"].is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	_expect(not failure["error"].is_empty())
	_expect(str(failure["error"]["message"]).length() <= 66000)

	# A Unicode payload written in fragments that cut through multi-byte
	# characters, with no trailing newline, must still arrive exactly. The
	# bytes are produced from escapes so the Windows command line stays ASCII.
	ready["payload"] = {}
	failure["error"] = {}
	var unicode_script := "import sys, time\n"
	unicode_script += "payload = b'{\"schema_version\": \"1.0\", \"ok\": true, \"note\": \"'"
	unicode_script += " + b'\\xe4\\xb8\\xad\\xe6\\x96\\x87' + b'\"}'\n"
	unicode_script += "for i in range(0, len(payload), 4):\n"
	unicode_script += "    sys.stdout.buffer.write(payload[i:i+4])\n"
	unicode_script += "    sys.stdout.buffer.flush()\n"
	unicode_script += "    time.sleep(0.01)\n"
	_expect(bridge.start_explanation(PackedStringArray(), PackedStringArray(["-c", unicode_script])))
	deadline = Time.get_ticks_msec() + 30000
	while (
		ready["payload"].is_empty()
		and failure["error"].is_empty()
		and Time.get_ticks_msec() < deadline
	):
		await create_timer(0.05).timeout
	_expect(not ready["payload"].is_empty(), str(failure["error"]))
	_expect(ready["payload"].get("note", "") == "中文", str(ready["payload"]))
