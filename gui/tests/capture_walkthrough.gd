extends SceneTree
## Capture the current release UI using synthetic data and real analysis output.
## Set PSYML_SCREENSHOT_LOCALE and PSYML_SCREENSHOT_DIR; requires a display.

func _initialize() -> void:
	call_deferred("_capture_walkthrough")

func _save(main, tab: int, path: String) -> void:
	main.tabs.current_tab = tab
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	assert(root.get_texture().get_image().save_png(path) == OK)

func _capture_walkthrough() -> void:
	root.size = Vector2i(1280, 1000)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var locale := PsyMLI18n.LOCALES.find(OS.get_environment("PSYML_SCREENSHOT_LOCALE"))
	assert(locale >= 0)
	main._on_language_selected(locale)
	var sample_dir := "/tmp/PsyML-demo"
	DirAccess.make_dir_recursive_absolute(sample_dir)
	var input_path := sample_dir.path_join("classification.csv")
	var file := FileAccess.open(input_path, FileAccess.WRITE)
	file.store_string(FileAccess.get_file_as_string("res://../examples/synthetic/classification.csv"))
	file.close()
	main._on_file_selected(input_path)
	var deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)
	for option in [main.target_option, main.group_option]:
		var value := "target" if option == main.target_option else "participant"
		for i in range(option.item_count):
			if option.get_item_metadata(i) == value:
				option.select(i)
	main._on_column_role_changed()
	for pair in [[main.feature_list, ["score", "category"]], [main.model_list, ["decision_tree", "dummy"]], [main.validation_list, ["group_k_fold", "holdout"]]]:
		var list = pair[0]
		for i in range(list.item_count):
			list.deselect(i)
			if list.get_item_metadata(i) in pair[1]:
				list.select(i, false)
	main.folds_spin.value = 3
	main.inner_folds_spin.value = 2
	main.max_candidates_spin.value = 2
	main.tuning_option.select(1)
	main._populate_parameter_editor()
	main._refresh_review()
	main.primary_validation_option.select(0)
	main.output_edit.text = sample_dir.path_join("outputs")
	main._refresh_review()
	var directory := OS.get_environment("PSYML_SCREENSHOT_DIR")
	assert(not directory.is_empty())
	DirAccess.make_dir_recursive_absolute(directory)
	await _save(main, 0, directory.path_join("01-data.png"))
	main.tabs.get_tab_control(0).ensure_control_visible(main.get_node("%ParameterSectionLabel"))
	await _save(main, 0, directory.path_join("02-settings.png"))
	await _save(main, 2, directory.path_join("03-review.png"))
	main._on_run_pressed()
	deadline = Time.get_ticks_msec() + 45000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(main.status_key == "COMPLETED", main.status_detail)
	await _save(main, 3, directory.path_join("04-results.png"))
	for i in range(main.validation_result_option.item_count):
		if main.validation_result_option.get_item_metadata(i) == "group_k_fold":
			main.validation_result_option.select(i)
			main._on_validation_result_selected(i)
	await _save(main, 3, directory.path_join("05-selected-result.png"))
	# Use a fresh window so the quick-start images contain no prior-run status.
	main.queue_free()
	await process_frame
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	main._on_language_selected(locale)
	main.output_edit.text = sample_dir.path_join("outputs")
	# A second sequence shows the exact bundled configuration used by the quick start.
	var example: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../examples/synthetic/classification_config.json"))
	example.input_path = input_path
	var config_path := sample_dir.path_join("classification_config.json")
	file = FileAccess.open(config_path, FileAccess.WRITE)
	file.store_string(JSON.stringify(example, "  "))
	file.close()
	assert(main.configuration_io.import_file(config_path), main.status_detail)
	main.tabs.get_tab_control(0).scroll_vertical = 0
	await _save(main, 0, directory.path_join("06-import-config.png"))
	await _save(main, 2, directory.path_join("07-reproduce-run.png"))
	main._on_run_pressed()
	deadline = Time.get_ticks_msec() + 45000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(main.status_key == "COMPLETED", main.status_detail)
	await _save(main, 3, directory.path_join("08-reproduced-result.png"))
	print("PSYML_RELEASE_CAPTURE_OK ", directory)
	quit(0)
