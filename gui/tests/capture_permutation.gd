extends SceneTree
## Capture the permutation-importance settings/results UI for visual QA.
##
## Writes synthetic long-Chinese-name data and runs one classification analysis
## with permutation importance enabled, then saves the results page in zh/en/fr.
## These screenshots only use synthetic data.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_capture")


func _wait_analysis(main) -> void:
	var deadline := Time.get_ticks_msec() + 90000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(0.1).timeout
	assert(not main.is_analysis_running, main.status_detail)


func _select_metadata(list: OptionButton, value: String) -> void:
	for index in range(list.item_count):
		if list.get_item_metadata(index) == value:
			list.select(index)
			return


func _scroll_container(control: Control) -> ScrollContainer:
	var node: Node = control.get_parent()
	while node != null:
		if node is ScrollContainer:
			return node
		node = node.get_parent()
	return null


func _scroll_to(control: Control) -> void:
	# Bring the new permutation block into view; the pages are ScrollContainers.
	var container := _scroll_container(control)
	if container != null:
		container.ensure_control_visible(control)


func _scroll_top(control: Control) -> void:
	var container := _scroll_container(control)
	if container != null:
		container.scroll_vertical = 0


func _show_permutation_figure(main) -> void:
	for index in range(main.figure_option.item_count):
		if str(main.figure_option.get_item_metadata(index)).ends_with("permutation_importance.png"):
			main.figure_option.select(index)
			main._show_selected_figure(index)
			return


func _grab(path: String) -> void:
	# A windowed run must wait for a presented frame before the viewport
	# texture holds the current UI, otherwise every capture repeats frame one.
	await RenderingServer.frame_post_draw
	await process_frame
	await process_frame
	root.get_viewport().get_texture().get_image().save_png(path)


func _capture() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	root.size = Vector2i(1180, 820)
	var output := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if output.is_empty():
		output = TestPaths.temp_dir().path_join("screenshots")
	DirAccess.make_dir_recursive_absolute(output)

	var data_dir := TestPaths.temp_dir().path_join("permutation-capture")
	DirAccess.make_dir_recursive_absolute(data_dir)
	var csv_path := data_dir.path_join("long_permutation.csv")
	var file := FileAccess.open(csv_path, FileAccess.WRITE)
	var first := "变量_基线得分_测量值_研究版_甲"
	var second := "变量_基线得分_测量值_研究版_乙"
	file.store_string("%s,%s,participant,target\n" % [first, second])
	for i in range(36):
		file.store_string("%f,%f,g%d,%d\n" % [sin(float(i)), cos(float(i)), i % 6, i % 2])
	file.close()

	main._on_file_selected(csv_path)
	var preview_deadline := Time.get_ticks_msec() + 20000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < preview_deadline:
		await create_timer(0.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)
	_select_metadata(main.target_option, "target")
	_select_metadata(main.group_option, "participant")
	main._on_column_role_changed()
	for index in range(main.feature_list.item_count):
		main.feature_list.deselect(index)
		if main.feature_list.get_item_metadata(index) in [first, second]:
			main.feature_list.select(index, false)
	main._refresh_review()
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) == "decision_tree":
			main.model_list.select(index, false)
	for index in range(main.validation_list.item_count):
		main.validation_list.deselect(index)
		if main.validation_list.get_item_metadata(index) == "group_k_fold":
			main.validation_list.select(index, false)
	main.folds_spin.value = 3
	main.permutation_ui.enable_check.button_pressed = true
	main.permutation_ui.repeats_spin.value = 2
	main.output_edit.text = data_dir.path_join("run")
	main._refresh_review()
	main._on_run_pressed()
	await _wait_analysis(main)
	assert(main.status_key == "COMPLETED", main.status_detail)

	main.tabs.current_tab = 0
	await create_timer(0.3).timeout
	_scroll_to(main.permutation_ui.help_label)
	await create_timer(0.3).timeout
	await _grab(output.path_join("permutation-settings-zh.png"))
	for locale in [0, 1, 2]:
		main._on_language_selected(locale)
		main.tabs.current_tab = 3
		await create_timer(0.2).timeout
		_show_permutation_figure(main)
		# Top of the results page: the selected signed ranking figure.
		_scroll_top(main.permutation_ui.export_button)
		await create_timer(0.2).timeout
		await _grab(output.path_join("permutation-figure-%d.png" % locale))
		# Scrolled to the permutation summary block.
		_scroll_to(main.permutation_ui.export_button)
		await create_timer(0.3).timeout
		await _grab(output.path_join("permutation-results-%d.png" % locale))
	print("PSYML_PERMUTATION_CAPTURE_OK")
	quit(0)
