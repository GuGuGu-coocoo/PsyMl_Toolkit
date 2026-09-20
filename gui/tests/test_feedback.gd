extends SceneTree

const TestPaths = preload("res://tests/test_paths.gd")


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


func _wheel_up(position: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = position
	motion.global_position = position
	root.push_input(motion, true)
	await process_frame
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_WHEEL_UP
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


func _click(position: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = position
	motion.global_position = position
	root.push_input(motion, true)
	await process_frame
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = true
	event.position = position
	event.global_position = position
	root.push_input(event, true)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame


func _drag(from: Vector2, delta: Vector2) -> void:
	await _click(from)
	var motion := InputEventMouseMotion.new()
	motion.position = from + delta
	motion.global_position = from + delta
	motion.button_mask = MOUSE_BUTTON_MASK_LEFT
	root.push_input(motion, true)
	await process_frame
	var release := InputEventMouseButton.new()
	release.button_index = MOUSE_BUTTON_LEFT
	release.pressed = false
	release.position = from + delta
	release.global_position = from + delta
	root.push_input(release, true)
	await process_frame
	await process_frame


func _write_build_file(path: String, label: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string('{"label": "%s", "version": "%s"}' % [label, label])
	file.close()


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
	# One gesture keeps one owner: crossing the nested tree while the page owns
	# the gesture must not hand control to the tree (FR-013).
	before = outer.scroll_vertical
	await _wheel(main.variable_tree.global_position + Vector2(30, 30))
	assert(outer.scroll_vertical > before)
	# After the release delay the nested tree is picked as the new owner and the
	# page stays put even though the tree itself has nothing to scroll.
	await create_timer(0.4).timeout
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
	await _check_version_label(main)
	await _check_page4_output_row(main)
	await _check_scroll_owner(main)
	print("PSYML_FEEDBACK_OK")
	quit(0)


func _check_version_label(main) -> void:
	# FR-012: the app name carries a small version label from a single source.
	var header: Control = main.get_node("AppMargin/Page/Header")
	var title: Label = main.get_node("AppMargin/Page/Header/TitleColumn/TitleLabel")
	var label: Label = main.version_label
	assert(label != null)
	assert(title.text == "PsyML Toolkit")
	assert(main.find_child("SubtitleLabel", true, false) == null)
	var source_version: String = main._version_from_pyproject(
		main._read_text_file(main._project_file("pyproject.toml"))
	)
	assert(not source_version.is_empty(), "source checkout must expose a version")
	assert(label.visible)
	assert(label.text == TranslationServer.translate("VERSION") + " " + source_version)
	# A simulated standalone package (same layout as tools/build_native.py) is
	# resolved through the real candidate function, not a hand-picked path.
	var layout_root := TestPaths.temp_dir().path_join("package-layout")
	DirAccess.make_dir_recursive_absolute(layout_root)
	var legacy_build := TestPaths.temp_dir().path_join("BUILD.json")
	if FileAccess.file_exists(legacy_build):
		DirAccess.remove_absolute(legacy_build)
	var mac_destination := layout_root.path_join("PsyML-Toolkit-9.9.9-macOS-arm64")
	var mac_resources := mac_destination.path_join("PsyML Toolkit.app/Contents/Resources")
	DirAccess.make_dir_recursive_absolute(mac_resources)
	_write_build_file(mac_destination.path_join("BUILD.json"), "9.9.9-mac")
	var mac_candidates: Array = main._build_file_candidates_for(mac_resources)
	assert(mac_candidates.size() == 4, "the candidate lookup must stay bounded")
	assert(mac_candidates[3] == mac_destination.path_join("BUILD.json"))
	assert(main._resolve_version_from(mac_candidates) == "9.9.9-mac")
	var windows_destination := layout_root.path_join("PsyML-Toolkit-9.9.9-Windows-x64")
	DirAccess.make_dir_recursive_absolute(windows_destination)
	_write_build_file(windows_destination.path_join("BUILD.json"), "9.9.9-win")
	var windows_candidates: Array = main._build_file_candidates_for(windows_destination)
	assert(windows_candidates[0] == windows_destination.path_join("BUILD.json"))
	assert(main._resolve_version_from(windows_candidates) == "9.9.9-win")
	# A source checkout matches no bounded candidate and falls back cleanly.
	var source_bundle := layout_root.path_join("source-checkout/gui/resources")
	DirAccess.make_dir_recursive_absolute(source_bundle)
	assert(main._resolve_version_from(main._build_file_candidates_for(source_bundle)).is_empty())
	assert(main._version_from_build_file(TestPaths.temp_dir().path_join("absent-BUILD.json")) == "")
	# Narrow window and all three languages keep the small text visible.
	main.get_window().size = Vector2i(1000, 700)
	await process_frame
	await process_frame
	for locale in [0, 1, 2]:
		main._on_language_selected(locale)
		await process_frame
		await process_frame
		assert(label.visible)
		assert(label.text == TranslationServer.translate("VERSION") + " " + source_version)
		var label_rect := label.get_global_rect()
		assert(label_rect.size.x > 0.0 and label_rect.size.y > 0.0)
		assert(header.get_global_rect().has_point(label_rect.position))
		assert(header.get_global_rect().end.x >= label_rect.end.x)
	main._on_language_selected(0)
	main.get_window().size = Vector2i(1180, 800)
	await process_frame
	await process_frame


func _check_page4_output_row(main) -> void:
	# FR-014 layout regression in the narrow window: the shared result-root row
	# must keep its label on one line and stay inside the prediction page.
	main.get_window().size = Vector2i(1000, 700)
	main.tabs.current_tab = 4
	await process_frame
	await process_frame
	var page: ScrollContainer = main.tabs.get_tab_control(4)
	var edit: LineEdit = main.prediction_page.output_edit
	var row: Control = edit.get_parent()
	var folder_label: Label = row.get_child(0)
	var help: Label = main.prediction_page.output_help
	assert(folder_label.autowrap_mode == TextServer.AUTOWRAP_OFF)
	assert(not folder_label.text.is_empty())
	assert(folder_label.get_global_rect().size.y < 30.0, "the result-root label must stay on one line")
	assert(row.get_global_rect().size.y < 60.0, "the result-root row must stay one line tall")
	assert(row.get_global_rect().end.x <= page.get_global_rect().end.x)
	assert(edit.get_global_rect().size.x > 200.0, "the result-root field must keep a usable width")
	assert(help.visible and help.get_line_count() >= 1)
	main.tabs.current_tab = 0
	main.get_window().size = Vector2i(1180, 800)
	await process_frame
	await process_frame


func _check_scroll_owner(main) -> void:
	# FR-013: one scroll layer per gesture, verified with injected wheel and pan
	# events on the real page plus a nested list that reports its own scroll.
	main.tabs.current_tab = 0
	await process_frame
	var page: ScrollContainer = main.tabs.get_tab_control(0)
	var content: Control = main.get_node("AppMargin/Page/Tabs/Data/Padding/DataContent")
	var nested := ItemList.new()
	nested.name = "LockProbeList"
	nested.custom_minimum_size = Vector2(220, 300)
	nested.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	content.add_child(nested)
	content.move_child(nested, 0)
	for index in range(60):
		nested.add_item("lock row %d" % index)
	await process_frame
	await process_frame
	assert(main.scroll_router != null)
	var bar := nested.get_v_scroll_bar()
	assert(bar.max_value - bar.page > 0.0, "probe list must scroll")

	# outside -> inside with the wheel keeps scrolling the page
	await _reset_gesture(page, bar)
	assert(page.get_global_rect().has_point(_page_top_point(main)))
	assert(page.get_global_rect().has_point(_list_center_point(nested)))
	var page_before: int = page.scroll_vertical
	await _wheel(_page_top_point(main))
	assert(page.scroll_vertical > page_before, "page must scroll from the heading")
	var list_before: float = bar.value
	await _wheel(_list_center_point(nested))
	assert(page.scroll_vertical > page_before, "page keeps the gesture after crossing the list")
	assert(bar.value == list_before, "nested list must not steal the page gesture")

	# inside -> outside with the wheel keeps scrolling the nested list
	await _reset_gesture(page, bar)
	await _wheel(_list_center_point(nested))
	assert(bar.value > 0.0, "nested list must scroll from its own area")
	var list_after: float = bar.value
	var page_held: int = page.scroll_vertical
	await _wheel(_page_top_point(main))
	assert(bar.value > list_after, "nested list keeps the gesture over the page")
	assert(page.scroll_vertical == page_held, "page must not move while the list owns the gesture")

	# direction change does not transfer the owner
	await _reset_gesture(page, bar)
	await _wheel(_list_center_point(nested))
	var list_down: float = bar.value
	await _wheel_up(_page_top_point(main))
	assert(bar.value < list_down, "wheel up keeps the nested list owner")
	assert(page.scroll_vertical == 0)

	# inside -> outside with a pan gesture keeps scrolling the nested list
	await _reset_gesture(page, bar)
	await _pan(_list_center_point(nested))
	var pan_list: float = bar.value
	var pan_page: int = page.scroll_vertical
	assert(pan_list > 0.0, "pan must scroll the nested list")
	await _pan(_page_top_point(main))
	assert(bar.value > pan_list, "pan keeps the nested list owner over the page")
	assert(page.scroll_vertical == pan_page)

	# outside -> inside with a pan gesture keeps scrolling the page
	await _reset_gesture(page, bar)
	await _pan(_page_top_point(main))
	var pan_page_before: int = page.scroll_vertical
	var pan_list_before: float = bar.value
	assert(pan_page_before > 0)
	await _pan(_list_center_point(nested))
	assert(page.scroll_vertical > pan_page_before, "pan keeps the page owner across the list")
	assert(bar.value == pan_list_before)

	# a pause longer than the release delay starts a new gesture
	await _reset_gesture(page, bar)
	await _wheel(_page_top_point(main))
	var pause_page: int = page.scroll_vertical
	var pause_list: float = bar.value
	await create_timer(0.4).timeout
	await _wheel(_list_center_point(nested))
	assert(bar.value > pause_list, "after the release delay a new owner is picked")
	assert(page.scroll_vertical == pause_page)

	# The lock must not swallow or leak clicks: while the page owns a fresh
	# gesture, an immediate click on the non-owner nested list still selects a
	# row, and no mouse filter stays changed after the scroll events.
	await _reset_gesture(page, bar)
	var nested_filter: int = nested.mouse_filter
	var bar_filter: int = bar.mouse_filter
	await _wheel(_page_top_point(main))
	assert(main.scroll_router.gesture_owner == page)
	assert(nested.mouse_filter == nested_filter, "the lock must not leave a filter on a non-owner list")
	assert(bar.mouse_filter == bar_filter, "the lock must not leave a filter on a non-owner scrollbar")
	nested.deselect_all()
	var click_page: int = page.scroll_vertical
	var visible_list := nested.get_global_rect().intersection(page.get_global_rect())
	assert(visible_list.size.y > 30.0, "the probe list must stay partly visible for the click")
	await _click(visible_list.get_center())
	assert(nested.get_selected_items().size() == 1, "an immediate list click must select the row")
	assert(page.scroll_vertical == click_page, "the list click must not pass through to the page")

	# A scrollbar drag is a non-scroll event too: right after a list gesture,
	# pressing and dragging the page scrollbar must move the page.
	await _reset_gesture(page, bar)
	await _wheel(_list_center_point(nested))
	assert(main.scroll_router.gesture_owner == nested)
	var page_bar: ScrollBar = page.get_v_scroll_bar()
	await _drag(page_bar.get_global_rect().get_center(), Vector2(0, 60))
	assert(page.scroll_vertical > 0, "a scrollbar drag during the list gesture must move the page")
	bar.value = bar.min_value
	await process_frame
	await process_frame

	# boundary of the owner never chains to the page
	await _reset_gesture(page, bar)
	bar.value = bar.max_value
	await process_frame
	await process_frame
	var boundary_value: float = bar.value
	await _wheel(_list_center_point(nested))
	await _wheel(_page_top_point(main))
	assert(page.scroll_vertical == 0, "a list at its boundary must not scroll the page")
	assert(bar.value == boundary_value)

	# hiding the owner clears the lock and the next event picks a new owner
	await _reset_gesture(page, bar)
	await _wheel(_list_center_point(nested))
	nested.visible = false
	await process_frame
	await process_frame
	await _wheel(_page_top_point(main))
	assert(page.scroll_vertical > 0, "a hidden owner must release the lock")
	nested.visible = true
	await process_frame
	await process_frame

	# changing the page clears the lock
	await _reset_gesture(page, bar)
	await _wheel(_list_center_point(nested))
	assert(main.scroll_router.gesture_owner != null)
	main.tabs.current_tab = 3
	await process_frame
	assert(main.scroll_router.gesture_owner == null, "changing the page must release the lock")
	main.tabs.current_tab = 0
	await process_frame
	nested.queue_free()
	await process_frame


func _reset_gesture(page: ScrollContainer, bar: ScrollBar) -> void:
	# Wait out the release delay so each scenario starts a fresh gesture, then
	# restore both scroll positions.
	await create_timer(0.4).timeout
	page.scroll_vertical = 0
	bar.value = bar.min_value
	await process_frame
	await process_frame


func _page_top_point(main) -> Vector2:
	return main.get_node("%DataHeading").global_position + Vector2(10, 10)


func _list_center_point(nested: ItemList) -> Vector2:
	return nested.get_global_rect().get_center()
