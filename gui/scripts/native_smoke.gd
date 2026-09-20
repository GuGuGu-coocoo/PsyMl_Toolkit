extends RefCounted

static func run(main: Control) -> void:
	if main.capabilities.has("error"):
		push_error(str(main.capabilities))
		main.get_tree().quit(1)
		return
	for task in ["classification", "regression"]:
		var example: String = CoreBridge.quickstart_directory().path_join(task + "_config.json")
		if not main.configuration_io.import_file(example):
			push_error(main.status_detail)
			main.get_tree().quit(1)
			return
		main.output_edit.text = smoke_root().path_join("psyml_native_smoke_" + str(Time.get_ticks_usec()))
		main._on_run_pressed()
		var deadline := Time.get_ticks_msec() + 180000
		while main.is_analysis_running and Time.get_ticks_msec() < deadline:
			await main.get_tree().create_timer(0.1).timeout
		if main.is_analysis_running or main.last_result_path.is_empty():
			push_error("Bundled analysis failed: " + main.status_detail)
			main.get_tree().quit(1)
			return
		var model_name := "decision_tree" if task == "classification" else "ridge"
		var page = main.prediction_page
		page.trust.button_pressed = true
		page.load_model(main.last_result_path.get_base_dir().path_join("model/best_" + model_name + ".joblib"))
		if not await _wait_prediction(main, page):
			return
		page.load_data(CoreBridge.quickstart_directory().path_join(task + "_predict.csv"))
		if not await _wait_prediction(main, page):
			return
		page.run_prediction()
		if not await _wait_prediction(main, page):
			return
		if page.predictions.get("row_count", 0) != 10:
			push_error("Bundled prediction must return 10 rows")
			main.get_tree().quit(1)
			return
		var delivery := verify_prediction_delivery(page)
		if not delivery.is_empty():
			push_error("Bundled prediction delivery check failed: " + delivery)
			main.get_tree().quit(1)
			return

	var report := FileAccess.open(OS.get_environment("PSYML_SMOKE_REPORT"), FileAccess.WRITE)
	report.store_string("PSYML_NATIVE_BUNDLE_OK")
	report.close()
	print("PSYML_NATIVE_BUNDLE_OK")
	main.get_tree().quit(0)

static func _wait_prediction(main: Control, page) -> bool:
	var deadline := Time.get_ticks_msec() + 60000
	while page.busy and Time.get_ticks_msec() < deadline:
		await main.get_tree().create_timer(0.1).timeout
	if page.busy or not page.error_message.is_empty():
		push_error("Bundled prediction failed: " + page.error_message)
		main.get_tree().quit(1)
		return false
	return true


static func verify_prediction_delivery(page) -> String:
	# The bundled smoke verifies the completed prediction of this run against the
	# real artifact: this run's predictions.csv must exist on disk and the open
	# action must target exactly that run folder. No copy/save-as detour and no
	# file manager is launched; the target is captured like the GUI tests do.
	if page.predictions.is_empty():
		return "prediction payload is empty"
	var csv: String = str(page.result_path)
	if csv.is_empty() or csv.get_file() != "predictions.csv" or not FileAccess.file_exists(csv):
		return "this run's predictions.csv is missing: " + csv
	var opened: Array[String] = []
	var previous: Callable = page.open_target_handler
	page.open_target_handler = func(path: String): opened.append(path)
	page.open_prediction_folder()
	page.open_target_handler = previous
	if opened.size() != 1 or opened[0] != csv.get_base_dir():
		return "the open action must target this run's folder: " + str(opened)
	return ""


static func smoke_root() -> String:
	# Source runs can point the smoke at a project-local temp root
	# (PSYML_TEST_TMP, already used by the GUI tests); the exported bundle
	# without that variable keeps using the system temp folder.
	var configured := OS.get_environment("PSYML_TEST_TMP").strip_edges()
	if configured.is_empty():
		return OS.get_temp_dir()
	DirAccess.make_dir_recursive_absolute(configured)
	return configured
