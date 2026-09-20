extends SceneTree
## GUI end-to-end for the fitted-coefficients section: extraction, verification,
## unsupported reasons, artifact delivery and language switching.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_run")


func _expect(condition: bool, message: String = "assertion failed") -> void:
	if not condition:
		printerr("PSYML_COEFFICIENTS_UI_FAILURE: " + message)
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


func _wait_coefficients(page) -> void:
	var deadline := Time.get_ticks_msec() + 60000
	while page.coefficients_busy and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	_expect(not page.coefficients_busy, "Coefficient extraction timed out")


func _run() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var page = main.prediction_page
	# Open actions are verified against the exact target they hand to the
	# OS without launching a file manager during the test.
	var opened: Array[String] = []
	page.open_target_handler = func(path: String): opened.append(path)
	# Page 4 writes into the page-2 result root: a Chinese path with spaces.
	var output_root := TestPaths.temp_dir().path_join("psyml 输出 系数 %d" % Time.get_ticks_usec())
	page.set_output_root(output_root)
	_expect(main.output_edit.text == output_root)
	_expect(page.output_edit.text == output_root)
	var directory := TestPaths.temp_dir().path_join("psyml-coefficients-ui-%d" % Time.get_ticks_usec())
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

	# The results page must expose the analysis coefficient status and its artifacts.
	main._load_results(str(config.output_dir).path_join("result.json"))
	await process_frame
	var result_coefficients = main.result_coefficients_ui
	_expect(result_coefficients.current_entry.get("status", "") == "available", str(result_coefficients.current_entry))
	_expect(result_coefficients.status_label.visible)
	_expect(result_coefficients.status_label.text.contains("all_analyzed_rows"), result_coefficients.status_label.text)
	_expect(result_coefficients.open_button.visible and not result_coefficients.open_button.disabled)
	main._clear_results()
	await process_frame

	page.trust.button_pressed = true
	page.load_model(model_path)
	await _wait_busy(page)
	page.load_data(predict_input)
	await _wait_busy(page)
	_expect(page.compatibility.compatible and not page.metadata.is_empty())
	_expect(not page.coefficients_button.disabled, "coefficients should be enabled once ready")

	# A missing or unwritable root is a visible error; never a user:// fallback.
	var user_before := _user_output_state()
	page.set_output_root("")
	page.run_coefficients()
	_expect(page.coefficients_error == main.tr("PREDICTION_OUTPUT_REQUIRED"), page.coefficients_error)
	_expect(not page.coefficients_busy and page.coefficient_report.is_empty())
	page.coefficients_error = ""
	var blocked_root := directory.path_join("blocked-root")
	_write(blocked_root, "not a directory")
	page.set_output_root(blocked_root)
	page.run_coefficients()
	_expect(page.coefficients_error == main.tr("OUTPUT_NOT_WRITABLE"), page.coefficients_error)
	_expect(not page.coefficients_busy)
	_expect(_user_output_state() == user_before, "coefficients must not fall back to user://")
	page.set_output_root(output_root)
	page.coefficients_error = ""

	# Successful extraction verifies the reconstruction and lists coefficients.
	page.run_coefficients()
	_expect(page.coefficients_busy)
	await _wait_coefficients(page)
	_expect(page.coefficients_error.is_empty(), page.coefficients_error)
	_expect(page.coefficient_report.get("status", "") == "available", str(page.coefficient_report))
	_expect(page.coefficient_report.get("verification", {}).get("verified", false), "reconstruction must verify")
	_expect(page.coefficients_tree.get_root().get_first_child() != null)
	# Intercepts, units, fit scope and the verification state must be visible without
	# opening the JSON, and a binary logistic row must state the class/reference axis.
	_expect(page.coefficients_outputs.text.contains(main.tr("COL_INTERCEPT")), page.coefficients_outputs.text)
	_expect(page.coefficients_outputs.text.contains("log-odds"), page.coefficients_outputs.text)
	_expect(page.coefficients_summary.text.contains("all_analyzed_rows"), page.coefficients_summary.text)
	_expect(page.coefficients_summary.text.contains(main.tr("COEFFICIENTS_VERIFY_OK")), page.coefficients_summary.text)
	var first_item: TreeItem = page.coefficients_tree.get_root().get_first_child()
	_expect(first_item.get_tooltip_text(0).contains(main.tr("COL_INTERCEPT")), first_item.get_tooltip_text(0))
	var coefficient_report_backup: Dictionary = page.coefficient_report.duplicate(true)
	for key in ["json", "csv", "notes"]:
		_expect(page.coefficients_artifacts.has(key), "missing artifact " + key)
		_expect(FileAccess.file_exists(str(page.coefficients_artifacts[key])), str(page.coefficients_artifacts))
	# They really live under the selected root, inside a new
	# coefficients/run_* folder owned by this operation.
	_expect(page.coefficients_output_dir.begins_with(output_root + "/"), page.coefficients_output_dir)
	_expect(
		page.coefficients_output_dir.get_base_dir() == output_root.path_join("coefficients"),
		page.coefficients_output_dir)
	_expect(page.coefficients_output_dir.get_file().begins_with("run_"), page.coefficients_output_dir)
	for key in ["json", "csv", "notes"]:
		_expect(
			str(page.coefficients_artifacts[key]).begins_with(page.coefficients_output_dir + "/"),
			str(page.coefficients_artifacts[key]))
	_expect(not page.coefficients_open_button.disabled)
	# The coefficient actions keep only opening; the export entry, dialog
	# and texts are gone, and opening targets the completed run folder itself.
	_expect(page.coefficients_open_button.get_parent().get_child_count() == 1,
		"the coefficients row must contain only the open action")
	for dead_key in ["EXPORT_COEFFICIENTS", "COEFFICIENTS_EXPORTED", "COEFFICIENTS_EXPORT_FAILED"]:
		_expect(main.tr(dead_key) == dead_key, "dead i18n key still translated: " + dead_key)
	opened.clear()
	page.open_coefficients_folder()
	_expect(opened.size() == 1 and opened[0] == page.coefficients_output_dir, str(opened))
	_expect(page.coefficients_error.is_empty(), page.coefficients_error)
	# A run folder that is no longer there must be a visible error that opens
	# nothing, never a fallback to another folder.
	var kept_dir: String = page.coefficients_output_dir
	page.coefficients_output_dir = directory.path_join("gone").path_join("run_missing")
	opened.clear()
	page.open_coefficients_folder()
	_expect(page.coefficients_error == main.tr("COEFFICIENTS_NO_ARTIFACT"), page.coefficients_error)
	_expect(opened.is_empty())
	page.coefficients_error = ""
	page.coefficients_output_dir = kept_dir
	var first_output_dir: String = page.coefficients_output_dir

	# More than 300 rows must show a display-limit notice that points to the full CSV.
	var limit_prefix: String = main.tr("COEFFICIENTS_ROW_LIMIT").split("%")[0]
	_expect(not page.coefficients_summary.text.contains(limit_prefix),
		"the limit notice must not appear for a small table: " + page.coefficients_summary.text)
	var many_rows: Dictionary = page.coefficient_report.duplicate(true)
	many_rows["features"] = []
	for index in range(320):
		many_rows["features"].append({
			"index": index, "name": "feature_%d" % index, "source": "score",
			"kind": "numeric", "category": null, "category_type": null,
			"category_index": null, "dropped_reference": false, "imputed": true,
			"imputer_strategy": "median", "imputer_fill_value": 0.0, "scaling": "standard",
			"scaler": null, "training_dtype": "float64", "note": "",
		})
	many_rows["coefficients"] = []
	for index in range(len(many_rows["output"]["rows"])):
		var base_row: Array = []
		base_row.resize(320)
		base_row.fill(0.0)
		many_rows["coefficients"].append(base_row)
	page.coefficient_report = many_rows
	page._fill_coefficients_tree()
	_expect(page.coefficients_summary.text.contains(limit_prefix), page.coefficients_summary.text)
	_expect(page.coefficients_summary.text.contains("coefficients.csv"), page.coefficients_summary.text)
	_expect(page.coefficients_tree.get_root().get_child_count() == 300, "the table must stop at 300 rows")
	page.coefficient_report = {}
	page._fill_coefficients_tree()
	_expect(not page.coefficients_summary.text.contains(limit_prefix), "clearing must drop the limit notice")
	page.coefficient_report = coefficient_report_backup
	page._fill_coefficients_tree()

	# Clearing the UI keeps completed artifacts on disk and closes the open action.
	var kept_json := str(page.coefficients_artifacts["json"])
	page._clear_coefficients()
	_expect(page.coefficient_report.is_empty() and page.coefficients_artifacts.is_empty())
	_expect(FileAccess.file_exists(kept_json), "completed artifacts must not be deleted")
	page.refresh_language()
	_expect(page.coefficients_open_button.disabled)
	opened.clear()
	page.open_coefficients_folder()
	_expect(page.coefficients_error == main.tr("COEFFICIENTS_NO_ARTIFACT"), page.coefficients_error)
	_expect(opened.is_empty())
	page.coefficients_error = ""

	# An unsupported estimator reports a specific reason and writes nothing new.
	config.model_name = "random_forest"
	config.model_names = ["random_forest"]
	config.tuning_mode = "none"
	config.parameter_grids = {}
	config.model_params = {"n_estimators": 5}
	config.output_dir = directory.path_join("rf_run")
	var rf_config_path := directory.path_join("rf_config.json")
	_write(rf_config_path, JSON.stringify(config))
	var rf_response: Dictionary = main.bridge.execute_json_sync(PackedStringArray(["run", "--config", rf_config_path]))
	_expect(not rf_response.has("error"), str(rf_response))
	var rf_model: String = str(config.output_dir).path_join(rf_response.model_export.model_path)
	page.load_model(rf_model)
	await _wait_busy(page)
	page.load_data(predict_input)
	await _wait_busy(page)
	page.run_coefficients()
	await _wait_coefficients(page)
	_expect(page.coefficient_report.get("status", "") == "unsupported", str(page.coefficient_report))
	_expect(page.coefficients_summary.text.contains("RandomForestClassifier"), page.coefficients_summary.text)
	_expect(page.coefficients_artifacts.is_empty(), "unsupported model must not produce artifacts")
	_expect(FileAccess.file_exists(kept_json), "an unsupported later run must not delete earlier artifacts")

	# A later successful run under a changed root gets its own new folder and
	# leaves earlier artifacts intact.
	var later_root := TestPaths.temp_dir().path_join("psyml 换目录 系数 %d" % Time.get_ticks_usec())
	page.set_output_root(later_root)
	page.load_model(model_path)
	await _wait_busy(page)
	page.load_data(predict_input)
	await _wait_busy(page)
	page.run_coefficients()
	await _wait_coefficients(page)
	_expect(page.coefficients_error.is_empty(), page.coefficients_error)
	_expect(page.coefficient_report.get("status", "") == "available", str(page.coefficient_report))
	_expect(page.coefficients_output_dir.begins_with(later_root + "/"), page.coefficients_output_dir)
	_expect(page.coefficients_output_dir != first_output_dir, "a later run must use its own new folder")
	_expect(FileAccess.file_exists(kept_json), "a later run must not remove earlier artifacts")
	for key in ["json", "csv", "notes"]:
		_expect(
			FileAccess.file_exists(str(page.coefficients_artifacts[key])),
			str(page.coefficients_artifacts))

	# Switching language must not raise and keeps the section readable.
	for locale in range(3):
		main._on_language_selected(locale)
		_expect(page.coefficients_status.text.length() > 0)

	print("PSYML_COEFFICIENTS_UI_OK")
	quit(0)
