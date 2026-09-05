extends RefCounted

static func run(main: Control) -> void:
	if main.capabilities.has("error"):
		push_error(str(main.capabilities))
		main.get_tree().quit(1)
		return
	for task in ["classification", "regression"]:
		var example: String = CoreBridge.examples_directory().path_join(task + "_config.json")
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
	var report := FileAccess.open(OS.get_environment("PSYML_SMOKE_REPORT"), FileAccess.WRITE)
	report.store_string("PSYML_NATIVE_BUNDLE_OK")
	report.close()
	print("PSYML_NATIVE_BUNDLE_OK")
	main.get_tree().quit(0)
