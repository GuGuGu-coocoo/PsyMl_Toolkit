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
		main.output_edit.text = OS.get_temp_dir().path_join("psyml_native_smoke_" + str(Time.get_ticks_usec()))
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
		var export_path: String = main.last_result_path.get_base_dir().path_join("smoke_predictions.xlsx")
		page.export_predictions(export_path)
		if not await _wait_prediction(main, page):
			return
		if not FileAccess.file_exists(export_path):
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
