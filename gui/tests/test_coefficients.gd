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
	_expect(not page.coefficients_open_button.disabled)
	_expect(not page.coefficients_export_button.disabled)

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

	# Export into a new directory delivers all three artifacts and reports success.
	var export_dir := directory.path_join("exported")
	page.export_coefficients(export_dir)
	_expect(page.coefficients_error.is_empty(), page.coefficients_error)
	_expect(not page.coefficients_note.is_empty(), "export must report success")
	for key in ["json", "csv", "notes"]:
		var name := str(page.coefficients_artifacts[key]).get_file()
		_expect(FileAccess.file_exists(export_dir.path_join(name)), "export missing " + name)

	# A destination holding a same-named CSV must not be overwritten; export falls
	# back to a unique new subdirectory.
	var occupied := directory.path_join("occupied")
	DirAccess.make_dir_recursive_absolute(occupied)
	_write(occupied.path_join("coefficients.csv"), "USER_EXISTING_CSV")
	page.export_coefficients(occupied)
	_expect(page.coefficients_error.is_empty(), page.coefficients_error)
	_expect(FileAccess.get_file_as_string(occupied.path_join("coefficients.csv")) == "USER_EXISTING_CSV", "existing CSV was overwritten")
	var subdirectories := DirAccess.open(occupied).get_directories()
	_expect(subdirectories.size() == 1, "expected a single unique export subdirectory")

	# Exporting into the current source directory is refused and changes nothing.
	var source_csv := str(page.coefficients_artifacts["csv"])
	var source_before := FileAccess.get_file_as_string(source_csv)
	page.export_coefficients(source_csv.get_base_dir())
	_expect(not page.coefficients_error.is_empty(), "same-source export must be reported")
	_expect(FileAccess.get_file_as_string(source_csv) == source_before, "source artifact changed")
	_expect(page.coefficients_note.is_empty(), "same-source export must not claim success")

	# A missing source artifact is refused before anything is written.
	var notes_path := str(page.coefficients_artifacts["notes"])
	page.coefficients_artifacts.erase("notes")
	var blocked := directory.path_join("blocked")
	page.export_coefficients(blocked)
	_expect(not page.coefficients_error.is_empty(), "missing source must be reported")
	_expect(not DirAccess.dir_exists_absolute(blocked), "missing source must not create the destination")
	page.coefficients_artifacts["notes"] = notes_path

	# Clearing the UI keeps completed artifacts on disk.
	var kept_json := str(page.coefficients_artifacts["json"])
	page._clear_coefficients()
	_expect(page.coefficient_report.is_empty() and page.coefficients_artifacts.is_empty())
	_expect(FileAccess.file_exists(kept_json), "completed artifacts must not be deleted")

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

	# Switching language must not raise and keeps the section readable.
	for locale in range(3):
		main._on_language_selected(locale)
		_expect(page.coefficients_status.text.length() > 0)

	print("PSYML_COEFFICIENTS_UI_OK")
	quit(0)
