extends SceneTree

const TestPaths = preload("res://tests/test_paths.gd")

var failures := 0


func _initialize() -> void:
	call_deferred("run")


func check(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failures += 1


func _wait_for_run(main) -> void:
	var guard := 0
	while main.bridge.is_running() and guard < 2400:
		await create_timer(0.1).timeout
		guard += 1
	guard = 0
	while main.last_result_path.is_empty() and guard < 1200:
		await create_timer(0.1).timeout
		guard += 1


func run() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	# Test setup is independent of the host desktop Documents directory.
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml test output")
	var data := CoreBridge.quickstart_directory().path_join("classification_train.csv")
	var stamp := str(Time.get_ticks_msec())
	var output_dir := TestPaths.temp_dir().path_join("psyml_fit_warnings_" + stamp)
	var config := {
		"schema_version": "1.0",
		"task": "classification",
		"target_column": "target",
		"model_name": "logistic_regression",
		"input_path": data,
		"output_dir": output_dir,
		"feature_columns": ["score", "category"],
		"group_column": "participant",
		"validation_strategy": "holdout",
		"random_seed": 3,
		"missing_strategy": "median",
		"scaling": "standard",
		"model_params": {"max_iter": 1},
		"tuning_mode": "none",
		"figure_types": [],
	}
	var config_path := TestPaths.temp_dir().path_join("psyml_fit_warnings_" + stamp + ".json")
	var file := FileAccess.open(config_path, FileAccess.WRITE)
	file.store_string(JSON.stringify(config))
	file.close()
	check(main.bridge.start_analysis(config_path), "Could not start the max_iter=1 analysis")
	await _wait_for_run(main)
	# A warning must never turn a completed run into a failure event.
	check(not main.last_result_path.is_empty(), "max_iter=1 run did not complete")
	check(
		main.warnings_text.text.contains("ConvergenceWarning"),
		"GUI did not render the fit warning: " + main.warnings_text.text
	)
	var warnings_path := output_dir.path_join("warnings.json")
	check(FileAccess.file_exists(warnings_path), "warnings.json missing")
	var recorded = CoreBridge.parse_json_document(FileAccess.get_file_as_string(warnings_path))
	check(recorded is Array and not recorded.is_empty(), "warnings.json is empty")
	print("PSYML_FIT_WARNINGS_OK")
	quit(1 if failures else 0)
