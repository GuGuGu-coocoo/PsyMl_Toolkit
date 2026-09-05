extends SceneTree


func _initialize() -> void:
	call_deferred("_run_test")


func _choose_result(main, validation: String) -> void:
	for index in range(main.validation_result_option.item_count):
		if main.validation_result_option.get_item_metadata(index) == validation:
			main.validation_result_option.select(index)
			main._on_validation_result_selected(index)
			return
	assert(false, "Missing validation result: " + validation)


func _wait_run(main) -> void:
	var deadline := Time.get_ticks_msec() + 30000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.is_analysis_running, main.status_detail)


func _wheel(position: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = position
	motion.global_position = position
	root.push_input(motion, true)
	await process_frame
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_WHEEL_DOWN
	event.pressed = true
	event.position = position
	event.global_position = position
	root.push_input(event, true)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame


func _pan(position: Vector2) -> void:
	var event := InputEventPanGesture.new()
	event.position = position
	event.delta = Vector2(0, 3)
	root.push_input(event, true)
	await process_frame
	await process_frame


func _run_test() -> void:
	Input.use_accumulated_input = false
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var fixture := ProjectSettings.globalize_path("res://../examples/synthetic/classification.csv")
	main._on_file_selected(fixture)
	var deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)
	for index in range(main.target_option.item_count):
		if main.target_option.get_item_metadata(index) == "target":
			main.target_option.select(index)
	for index in range(main.group_option.item_count):
		if main.group_option.get_item_metadata(index) == "participant":
			main.group_option.select(index)
	main._on_column_role_changed()
	for index in range(main.feature_list.item_count):
		main.feature_list.deselect(index)
		if main.feature_list.get_item_metadata(index) in ["score", "category"]:
			main.feature_list.select(index, false)
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) in ["dummy", "decision_tree"]:
			main.model_list.select(index, false)
	for index in range(main.validation_list.item_count):
		main.validation_list.deselect(index)
		if main.validation_list.get_item_metadata(index) in ["holdout", "group_k_fold"]:
			main.validation_list.select(index, false)
	main.folds_spin.value = 3
	main._refresh_review()
	main.primary_validation_option.select(0)
	main._refresh_review()
	assert(main._build_config().primary_validation == null)
	main._on_language_selected(1)
	assert(main._build_config().primary_validation == null)
	main._on_language_selected(0)
	main.output_edit.text = OS.get_temp_dir().path_join("psyml-independent-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	var bundle_path: String = main.last_result_path
	assert(main.validation_result_option.visible)
	assert(main.validation_result_option.selected == 0)
	assert(main.metrics_tree.get_root() == null)
	assert(main.figure_view.texture == null)
	assert("未指定主要验证" in main.best_result_label.text)
	assert("Primary metrics evaluate" not in main.warnings_text.text)
	assert("[留出集]" in main.warnings_text.text)
	var screenshot_dir := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if not screenshot_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(screenshot_dir)
		await process_frame
		await process_frame
		root.get_texture().get_image().save_png(screenshot_dir.path_join("independent-overview.png"))
	_choose_result(main, "holdout")
	assert(main.last_result_path == bundle_path)
	assert(main.last_result_dir.ends_with("validations/holdout"))
	assert("主要验证" not in main.best_result_label.text)
	assert(main.metrics_tree.get_root().get_first_child() != null)
	assert(main.figure_view.texture != null)
	assert(main.figure_option.item_count == 2)
	_choose_result(main, "group_k_fold")
	assert(main.last_result_dir.ends_with("validations/group_k_fold"))
	assert(main.metrics_tree.get_root().get_first_child() != null)
	main._on_language_selected(2)
	assert(main.last_result_dir.ends_with("validations/group_k_fold"))
	assert(main.validation_result_option.get_item_metadata(main.validation_result_option.selected) == "group_k_fold")
	main._on_language_selected(0)
	if not screenshot_dir.is_empty():
		await process_frame
		await process_frame
		root.get_texture().get_image().save_png(screenshot_dir.path_join("independent-selected.png"))
	var page = main.tabs.get_tab_control(3)
	# Summary text, headings and margins must all scroll the results page.
	for control in [main.get_node("%ResultSummarySectionLabel"), main.best_result_label, main.warnings_text]:
		page.scroll_vertical = 0
		await process_frame
		page.ensure_control_visible(control)
		await process_frame
		await process_frame
		var before: int = page.scroll_vertical
		await _wheel(control.global_position + Vector2(10, 10))
		assert(page.scroll_vertical > before, "Summary text swallowed page scrolling: " + control.name)
		page.scroll_vertical = 0
		await process_frame
		page.ensure_control_visible(control)
		await process_frame
		await process_frame
		before = page.scroll_vertical
		await _pan(control.global_position + Vector2(10, 10))
		assert(page.scroll_vertical > before, "Summary text swallowed trackpad scrolling: " + control.name)
	page.scroll_vertical = 0
	await process_frame
	await process_frame
	var panel = main.best_result_label.get_parent().get_parent().get_parent()
	await _wheel(panel.global_position + Vector2(5, 80))
	assert(page.scroll_vertical > 0, "Summary panel margin swallowed scrolling")
	page.ensure_control_visible(main.comparison_tree)
	await process_frame
	await process_frame
	var before: int = page.scroll_vertical
	await _wheel(main.comparison_tree.global_position + Vector2(30, 30))
	assert(page.scroll_vertical == before, "Nested table scroll leaked to page")
	main.validation_result_option.select(0)
	main._on_validation_result_selected(0)
	assert(main.metrics_tree.get_root() == null)
	assert(main.figure_view.texture == null)
	# Failure of one validation must not show the previous successful figures.
	main.folds_spin.value = 20
	main._on_run_pressed()
	await _wait_run(main)
	var partial = JSON.parse_string(FileAccess.get_file_as_string(main.last_result_path))
	assert(partial.status == "completed_with_errors")
	assert("部分验证失败" in main.best_result_label.text)
	_choose_result(main, "holdout")
	assert(main.figure_view.texture != null)
	_choose_result(main, "group_k_fold")
	assert(main.figure_view.texture == null)
	assert(main.metrics_tree.get_root() == null)
	assert("验证失败" in main.best_result_label.text)
	assert(not main.warnings_text.text.is_empty())
	print("PSYML_INDEPENDENT_RESULTS_OK")
	quit(0)
