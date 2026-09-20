extends SceneTree
## Capture the data check and result interpretation UI for QA.
##
## Uses synthetic data only. These are rendered offscreen/window captures for
## visual review; headless success alone is not visual acceptance. Run windowed
## (not --headless) so the viewport is presented before each grab.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_capture")


func _wait_analysis(main) -> void:
	var deadline := Time.get_ticks_msec() + 120000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(0.1).timeout
	assert(not main.is_analysis_running, main.status_detail)


func _wait_preview(main) -> void:
	var deadline := Time.get_ticks_msec() + 20000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)


func _select_metadata(option: OptionButton, value: String) -> void:
	for index in range(option.item_count):
		if option.get_item_metadata(index) == value:
			option.select(index)
			return


func _grab(path: String) -> void:
	await RenderingServer.frame_post_draw
	await process_frame
	await process_frame
	root.get_viewport().get_texture().get_image().save_png(path)


func _scroll_to(control: Control) -> void:
	var node: Node = control.get_parent()
	while node != null:
		if node is ScrollContainer:
			node.ensure_control_visible(control)
			return
		node = node.get_parent()


func _capture() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	root.size = Vector2i(1180, 820)
	var output := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if output.is_empty():
		output = TestPaths.temp_dir().path_join("screenshots")
	DirAccess.make_dir_recursive_absolute(output)

	var data_dir := TestPaths.temp_dir().path_join("researcher-flow-capture")
	DirAccess.make_dir_recursive_absolute(data_dir)
	var csv_path := data_dir.path_join("synthetic_flow.csv")
	var file := FileAccess.open(csv_path, FileAccess.WRITE)
	file.store_string("participant,score,category,target\n")
	for i in range(48):
		var label := "case_%02d" % i
		var category := "A" if i % 2 == 0 else "B"
		var target := 0 if (i % 4) < 2 else 1
		file.store_string("%s,%f,%s,%d\n" % [label, sin(float(i)) + float(i % 5), category, target])
	file.close()

	main._on_file_selected(csv_path)
	await _wait_preview(main)
	_select_metadata(main.target_option, "target")
	main._on_column_role_changed()
	for index in range(main.feature_list.item_count):
		main.feature_list.deselect(index)
		if main.feature_list.get_item_metadata(index) in ["score", "category"]:
			main.feature_list.select(index, false)
	main._refresh_review()

	# Data check on the opened preview.
	main.tabs.current_tab = 0
	await create_timer(0.3).timeout
	_scroll_to(main.data_check_ui.category_tree)
	await create_timer(0.3).timeout
	await _grab(output.path_join("data-check-zh.png"))
	_scroll_to(main.data_check_ui.id_label)
	await create_timer(0.3).timeout
	await _grab(output.path_join("data-check-id-zh.png"))
	main._on_language_selected(1)
	await create_timer(0.3).timeout
	_scroll_to(main.data_check_ui.category_tree)
	await create_timer(0.3).timeout
	await _grab(output.path_join("data-check-en.png"))
	_scroll_to(main.data_check_ui.id_label)
	await create_timer(0.3).timeout
	await _grab(output.path_join("data-check-id-en.png"))
	main._on_language_selected(0)

	# Result interpretation with a successful dummy baseline.
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) in ["decision_tree", "dummy"]:
			main.model_list.select(index, false)
	for index in range(main.validation_list.item_count):
		main.validation_list.deselect(index)
		if main.validation_list.get_item_metadata(index) == "stratified_k_fold":
			main.validation_list.select(index, false)
	main.folds_spin.value = 3
	main.inner_folds_spin.value = 2
	main.output_edit.text = data_dir.path_join("run")
	main._refresh_review()
	main._on_run_pressed()
	await _wait_analysis(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	main.tabs.current_tab = 3
	await create_timer(0.4).timeout
	_scroll_to(main.interpretation_ui.diff_tree)
	await create_timer(0.3).timeout
	await _grab(output.path_join("result-interpretation-zh.png"))
	for locale in [1, 2]:
		main._on_language_selected(locale)
		main.tabs.current_tab = 3
		await create_timer(0.3).timeout
		_scroll_to(main.interpretation_ui.diff_tree)
		await create_timer(0.3).timeout
		await _grab(output.path_join("result-interpretation-%s.png" % ["en", "fr"][locale - 1]))
	main._on_language_selected(0)

	print("PSYML_CAPTURE_OK")
	quit(0)
