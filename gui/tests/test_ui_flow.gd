extends SceneTree


func _initialize() -> void:
	call_deferred("_run_test")


func _run_test() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	assert(TranslationServer.get_locale() == "zh_CN")
	assert(main.run_button.text == "运行分析")
	var fixture := ProjectSettings.globalize_path("res://tests/fixtures/sample.tsv")
	main._on_file_selected(fixture)
	var preview_deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < preview_deadline:
		await create_timer(0.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_label.text)
	for index in range(main.target_option.item_count):
		if main.target_option.get_item_metadata(index) == "target":
			main.target_option.select(index)
			break
	main._on_column_role_changed()
	assert(main.model_list.item_count > 1)
	main.model_list.select(1, false)
	assert(main.validation_list.item_count > 1)
	for index in range(main.validation_list.item_count):
		if main.validation_list.get_item_metadata(index) == "holdout":
			main.validation_list.select(index, false)
			break
	for index in range(main.tuning_option.item_count):
		if main.tuning_option.get_item_metadata(index) == "tuning_custom":
			main.tuning_option.select(index)
			break
	main._populate_parameter_editor()
	var comparative_config = main._build_config()
	assert(comparative_config.model_names.size() == 2)
	assert(comparative_config.validation_strategies.size() == 2)
	assert(comparative_config.tuning_mode == "custom")
	assert(not comparative_config.parameter_grids.is_empty())
	for index in range(main.tuning_option.item_count):
		if main.tuning_option.get_item_metadata(index) == "tuning_none":
			main.tuning_option.select(index)
			break
	main._populate_parameter_editor()
	var result_dir := OS.get_temp_dir().path_join("psyml godot 中文 %d" % Time.get_ticks_msec())
	main.output_edit.text = result_dir
	main._on_run_pressed()
	var result_path := result_dir.path_join("result.json")
	var run_deadline := Time.get_ticks_msec() + 30000
	while (
		(not FileAccess.file_exists(result_path) or main.last_result_dir != result_dir)
		and Time.get_ticks_msec() < run_deadline
	):
		await create_timer(0.05).timeout
	if not FileAccess.file_exists(result_path) or main.last_result_dir != result_dir:
		push_error(main.status_label.text)
		quit(1)
		return
	var result = JSON.parse_string(FileAccess.get_file_as_string(result_path))
	assert(result.status == "completed")
	assert(result.task == "classification")
	assert(result.evaluated_combinations == 4)
	assert(main.metrics_tree.get_root().get_first_child() != null)
	assert(main.comparison_tree.get_root().get_first_child() != null)
	assert(main.figure_view.texture != null)
	assert(main.progress_bar.value == 1.0)
	assert(main.progress_detail_label.text == "全部任务已完成。")
	for index in range(main.task_option.item_count):
		if main.task_option.get_item_metadata(index) == "regression":
			main.task_option.select(index)
			break
	main._on_task_changed()
	var regression_dir := OS.get_temp_dir().path_join(
		"psyml godot regression %d" % Time.get_ticks_msec()
	)
	main.output_edit.text = regression_dir
	main._on_run_pressed()
	var regression_result_path := regression_dir.path_join("result.json")
	var regression_deadline := Time.get_ticks_msec() + 30000
	while (
		(
			not FileAccess.file_exists(regression_result_path)
			or main.last_result_dir != regression_dir
		)
		and Time.get_ticks_msec() < regression_deadline
	):
		await create_timer(0.05).timeout
	if (
		not FileAccess.file_exists(regression_result_path)
		or main.last_result_dir != regression_dir
	):
		push_error(main.status_label.text)
		quit(1)
		return
	var regression_result = JSON.parse_string(
		FileAccess.get_file_as_string(regression_result_path)
	)
	assert(regression_result.task == "regression")
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) == "mlp":
			main.model_list.select(index, false)
	for index in range(main.tuning_option.item_count):
		if main.tuning_option.get_item_metadata(index) == "tuning_quick":
			main.tuning_option.select(index)
			break
	main._populate_parameter_editor()
	main.output_edit.text = OS.get_temp_dir().path_join(
		"psyml godot cancel %d" % Time.get_ticks_msec()
	)
	main._on_run_pressed()
	await create_timer(0.15).timeout
	assert(main.bridge.is_running())
	main._request_cancel()
	assert(main.status_key == "CANCELLED")
	assert(not main.bridge.is_running())
	assert(main.pending_config_path.is_empty())
	assert(not main.run_button.disabled)
	main._on_language_selected(2)
	assert(main.run_button.text == "Exécuter l’analyse")
	assert(main.tabs.get_tab_title(3) == "4  Résultats")
	print("PSYML_GODOT_UI_FLOW_OK")
	quit(0)
