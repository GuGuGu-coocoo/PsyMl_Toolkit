extends SceneTree


func _initialize() -> void:
	call_deferred("_capture_walkthrough")


func _capture_walkthrough() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	var width := OS.get_environment("PSYML_CAPTURE_WIDTH").to_int()
	var height := OS.get_environment("PSYML_CAPTURE_HEIGHT").to_int()
	if width > 0 and height > 0:
		root.size = Vector2i(width, height)
	var requested_locale := OS.get_environment("PSYML_SCREENSHOT_LOCALE")
	var locale_index := PsyMLI18n.LOCALES.find(requested_locale)
	if locale_index < 0:
		push_error("Unsupported screenshot locale: " + requested_locale)
		quit(1)
		return
	main._on_language_selected(locale_index)
	var guide_root := "/tmp/PsyML Guide"
	DirAccess.make_dir_recursive_absolute(guide_root)
	var fixture := guide_root.path_join("sample.tsv")
	var fixture_file := FileAccess.open(fixture, FileAccess.WRITE)
	fixture_file.store_string(
		FileAccess.get_file_as_string("res://tests/fixtures/sample.tsv")
	)
	fixture_file.close()
	var input_override := OS.get_environment("PSYML_CAPTURE_INPUT")
	if not input_override.is_empty():
		fixture = input_override
	main._on_file_selected(fixture)
	var preview_deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < preview_deadline:
		await create_timer(0.05).timeout
	if main.preview_payload.is_empty():
		push_error(main.status_label.text)
		quit(1)
		return
	if OS.get_environment("PSYML_CAPTURE_TASK") == "regression":
		main.task_option.select(1)
		main._on_task_changed()
	for index in range(main.target_option.item_count):
		if main.target_option.get_item_metadata(index) == "target":
			main.target_option.select(index)
			break
	for index in range(main.group_option.item_count):
		if main.group_option.get_item_metadata(index) == "participant":
			main.group_option.select(index)
			break
	main._on_column_role_changed()
	for index in range(main.validation_list.item_count):
		main.validation_list.deselect(index)
	for index in range(main.validation_list.item_count):
		if main.validation_list.get_item_metadata(index) in [
			"group_k_fold", "stratified_group_k_fold"
		]:
			main.validation_list.select(index, false)
	main.validation_list.ensure_current_is_visible()
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) in ["decision_tree", "dummy"]:
			main.model_list.select(index, false)
	main.model_list.ensure_current_is_visible()
	for index in range(main.tuning_option.item_count):
		if main.tuning_option.get_item_metadata(index) == "tuning_quick":
			main.tuning_option.select(index)
			break
	main.inner_folds_spin.value = 2
	main.max_candidates_spin.value = 2
	main._populate_parameter_editor()
	for index in range(main.feature_list.item_count):
		main.feature_list.deselect(index)
		if main.feature_list.get_item_metadata(index) in ["score", "category"]:
			main.feature_list.select(index, false)
	if OS.get_environment("PSYML_CAPTURE_GUIDE") == "1":
		main.folds_spin.value = 3
		for index in range(main.validation_list.item_count):
			main.validation_list.deselect(index)
			if main.validation_list.get_item_metadata(index) == "group_k_fold":
				main.validation_list.select(index, false)
		if OS.get_environment("PSYML_CAPTURE_TASK") == "regression":
			for index in range(main.model_list.item_count):
				main.model_list.deselect(index)
				if main.model_list.get_item_metadata(index) == "linear_regression":
					main.model_list.select(index, false)
			main.tuning_option.select(0)
			main._populate_parameter_editor()
	var output_root := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if output_root.is_empty():
		output_root = OS.get_temp_dir().path_join("psyml-walkthrough")
	DirAccess.make_dir_recursive_absolute(output_root)
	main.output_edit.text = "/tmp/PsyML Results/" + requested_locale + "-" + str(Time.get_unix_time_from_system()).replace(".", "-")
	main._refresh_review()
	await _capture_tab(main, 0, output_root.path_join("01-data.png"))
	await _capture_tab(main, 1, output_root.path_join("02-configure.png"))
	await _capture_tab(main, 2, output_root.path_join("03-review.png"))
	main._on_run_pressed()
	var run_deadline := Time.get_ticks_msec() + 45000
	while main.last_result_dir.is_empty() and Time.get_ticks_msec() < run_deadline:
		await create_timer(0.05).timeout
	if main.last_result_dir.is_empty():
		push_error(main.status_label.text)
		quit(1)
		return
	await _capture_tab(main, 3, output_root.path_join("04-results.png"))
	main.tabs.current_tab = 1
	main.tabs.get_child(1).scroll_vertical = 900
	await _capture_tab(main, 1, output_root.path_join("05-parameters.png"))
	main.tabs.get_child(3).scroll_vertical = 650
	await _capture_tab(main, 3, output_root.path_join("06-predictions.png"))
	print("PSYML_WALKTHROUGH_SCREENSHOTS=" + output_root)
	quit(0)


func _capture_tab(main: Control, index: int, path: String) -> void:
	main.tabs.current_tab = index
	await process_frame
	await process_frame
	var image := root.get_viewport().get_texture().get_image()
	var error := image.save_png(path)
	if error != OK:
		push_error("Could not save screenshot: %s" % error_string(error))
