extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	if main.capabilities.has("error"):
		push_error(str(main.capabilities))
		quit(1)
		return
	for task in ["classification", "regression"]:
		var example: String = CoreBridge.examples_directory().path_join(task + "_config.json")
		if not main.configuration_io.import_file(example):
			push_error(main.status_detail)
			quit(1)
			return
		main.output_edit.text = OS.get_temp_dir().path_join("psyml_native_smoke_" + str(Time.get_ticks_usec()))
		main._on_run_pressed()
		var deadline := Time.get_ticks_msec() + 180000
		while main.is_analysis_running and Time.get_ticks_msec() < deadline:
			await create_timer(0.1).timeout
		if main.is_analysis_running or main.last_result_path.is_empty():
			push_error("Bundled analysis failed: " + main.status_detail)
			quit(1)
			return
	print("PSYML_NATIVE_BUNDLE_OK")
	quit(0)
