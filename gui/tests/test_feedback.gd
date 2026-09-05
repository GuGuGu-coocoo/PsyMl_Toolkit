extends SceneTree


func _initialize() -> void:
	call_deferred("_run_test")


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
	assert(main.tabs.is_tab_hidden(1))
	var fixture := ProjectSettings.globalize_path("res://../examples/synthetic/classification.csv")
	main._on_file_selected(fixture)
	var deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)
	assert(main.tabs.current_tab == 0)
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
		if main.model_list.get_item_metadata(index) == "decision_tree":
			main.model_list.select(index, false)
	main.tuning_option.select(2)
	main._populate_parameter_editor()
	var grid: Dictionary = main._parameter_grid_payload().grids.decision_tree
	assert(typeof(grid.max_depth[1]) == TYPE_INT)
	assert(typeof(grid.min_samples_leaf[0]) == TYPE_INT)
	for index in range(main.validation_list.item_count):
		if main.validation_list.get_item_metadata(index) == "holdout":
			main.validation_list.select(index, false)
	main._refresh_review()
	assert(main._build_config().validation_strategy == "stratified_k_fold")
	for index in range(main.primary_validation_option.item_count):
		if main.primary_validation_option.get_item_metadata(index) == "holdout":
			main.primary_validation_option.select(index)
	main._refresh_review()
	assert(main._build_config().validation_strategy == "holdout")
	assert(main._build_config().validation_strategies[0] == "holdout")
	assert(main.feature_list.select_mode == ItemList.SELECT_TOGGLE)
	assert(main.feature_list.get_item_icon(0) != null)
	assert(main.variable_tree.get_theme_color("font_selected_color") == main.TEXT)
	main.variable_tree.get_root().get_first_child().select(0)
	var outer = main.tabs.get_tab_control(0)
	var right = main.get_node("AppMargin/Page/Tabs/Data/Padding/DataContent/DataWorkspace/PredictorsPanel")
	assert(not right is ScrollContainer)
	assert(right.get_node("Margin/Content/DesignPanel").is_ancestor_of(main.feature_list))
	assert(not main.variable_tree.mouse_force_pass_scroll_events)
	assert(not main.sample_tree.mouse_force_pass_scroll_events)
	outer.scroll_vertical = 0
	await process_frame
	await process_frame
	# Research-design labels and panel margins scroll with the page.
	await _wheel(main.get_node("%DesignSectionLabel").global_position + Vector2(10, 10))
	assert(outer.scroll_vertical > 0)
	var pan_before: int = outer.scroll_vertical
	await _pan(main.get_node("%DesignSectionLabel").global_position + Vector2(10, 10))
	assert(outer.scroll_vertical > pan_before)
	var before: int = outer.scroll_vertical
	await _wheel(right.global_position + Vector2(5, 100))
	assert(outer.scroll_vertical > before)
	before = outer.scroll_vertical
	await _wheel(main.variable_tree.global_position + Vector2(30, 30))
	assert(outer.scroll_vertical == before)
	outer.scroll_vertical = 0
	await process_frame
	await process_frame
	var capture_dir := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if not capture_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(capture_dir)
		root.get_texture().get_image().save_png(capture_dir.path_join("combined-setup.png"))
		outer.scroll_vertical = 820
		await process_frame
		await process_frame
		root.get_texture().get_image().save_png(capture_dir.path_join("analysis-options.png"))
		outer.scroll_vertical = 100000
		await process_frame
		await process_frame
		root.get_texture().get_image().save_png(capture_dir.path_join("figure-options.png"))
	main.task_option.select(1)
	main._on_task_changed()
	for index in range(main.model_list.item_count):
		assert(main.model_list.get_item_metadata(index) != "logistic_regression")
		assert(main.model_list.get_item_metadata(index) != "svm")
	assert(main._selected_figures() == ["observed_vs_predicted", "residuals", "residual_distribution"])
	for child in main.figure_choices.get_children():
		if child is CheckBox:
			child.button_pressed = false
	assert(main._selected_figures().is_empty())
	for locale in [1, 2, 0]:
		main._on_language_selected(locale)
		assert(main._selected_figures().is_empty(), "Language change reset figure choices")
	main._show_core_error({"code": "invalid_input", "message": "All parameter candidates failed: max_depth must be positive"})
	assert(main.error_details.visible)
	assert("max_depth" in main.error_details.text)
	assert("参数候选" in main.error_details.text)
	main.copy_error_button.pressed.emit()
	if DisplayServer.get_name() != "headless":
		assert(DisplayServer.clipboard_get() == main.status_detail)
	print("PSYML_FEEDBACK_OK")
	quit(0)
