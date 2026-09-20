extends SceneTree

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_run_test")


func _run_test() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	assert(main.has_node("AppMargin/Page/Header/TitleColumn/TitleLabel"))
	assert(main.has_node("AppMargin/Page/Header/TitleColumn/VersionLabel"))
	assert(main.has_node("AppMargin/Page/Tabs/Data/Padding/DataContent/DataSourcePanel"))
	assert(main.has_node("AppMargin/Page/Tabs/Data/Padding/DataContent/DataWorkspace/PredictorsPanel/Margin/Content/DesignPanel"))
	assert(main.has_node("AppMargin/Page/Tabs/Review/Padding/ReviewContent/ExecutionPanel"))
	assert(main.has_node("AppMargin/Page/Tabs/Results/Padding/ResultsContent/ResultsBody"))
	assert(main.get_node("AppMargin/Page/Header/TitleColumn/TitleLabel").text == "PsyML Toolkit")
	assert(main.version_label.visible)
	assert(main.version_label.text == TranslationServer.translate("VERSION") + " " + main._display_version(main._resolve_version()))
	assert(main.find_child("SubtitleLabel", true, false) == null)
	assert(main.bridge == main.get_node("CoreBridge"))
	assert(TranslationServer.get_locale() == "zh_CN")
	assert(TranslationServer.translate("COLUMN_RANK") == "排名")
	assert(TranslationServer.translate("METRIC_PRECISION_WEIGHTED") == "加权精确率（Weighted Precision）")
	assert(main.run_button.text == "运行分析")
	assert(main.run_button.disabled)
	assert(main.cancel_button.disabled)
	assert(main._localized_warning("Dropped 1 rows with missing target values.") == "目标变量缺失，排除了 1 行。")
	assert(main._localized_warning("Dropped 2 rows because missing_strategy='drop'.") == "所选字段的缺失删除策略排除了 2 行。")
	assert(main.preview_button.disabled)
	var fixture := ProjectSettings.globalize_path("res://tests/fixtures/sample.tsv")
	main._on_file_selected(fixture)
	var preview_deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < preview_deadline:
		await create_timer(0.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_label.text)
	assert(main.tabs.current_tab == 0)
	assert(not main.preview_button.disabled)
	var changed_path := fixture + ".changed"
	main.data_path_edit.text = changed_path
	main._on_data_path_changed(changed_path)
	assert(main.preview_payload.is_empty())
	assert(main.run_button.disabled)
	assert(main.data_summary_label.text == TranslationServer.translate("NO_DATA"))
	main.data_path_edit.text = fixture
	main._on_data_path_changed(fixture)
	main._request_preview()
	preview_deadline = Time.get_ticks_msec() + 15000
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
	assert(main.feature_list.multi_selected.get_connections().size() > 0)
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
	var result_dir := TestPaths.temp_dir().path_join("psyml godot 中文 %d" % Time.get_ticks_msec())
	# The selected result root; each run gets a family subfolder under it.
	var root_dir: String = result_dir
	main.output_edit.text = "relative/results"
	main._refresh_review()
	assert(main.run_button.disabled)
	assert(main.review_text.text == TranslationServer.translate("SELECT_OUTPUT"))
	main.output_edit.text = result_dir
	main._refresh_review()
	assert(not main.run_button.disabled)
	# FR-019: a new GUI training run is planned inside its own training/ family
	# folder under the shared root, matching prediction/, explanation/ and
	# coefficients/, while the run folder name still starts with run_.
	var planned_dir: String = main._build_config().output_dir
	assert(planned_dir.get_base_dir() == result_dir.path_join("training"), planned_dir)
	assert(planned_dir.get_file().begins_with("run_"), planned_dir)
	# Clearing the final model in no-search mode must immediately invalidate review.
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
	main.model_list.multi_selected.emit(0, false)
	assert(main.run_button.disabled)
	assert(main.review_text.text == TranslationServer.translate("SELECT_MODEL"))
	main.model_list.select(0, false)
	main.model_list.select(1, false)
	main.model_list.multi_selected.emit(1, true)
	assert(not main.run_button.disabled)
	assert(main._build_config().selection_protocol == "nested_family_v1")
	# FR-015: while the runner reports `finalizing`, the page must show the
	# writing state, stay below a full bar and keep the run cancellable; only
	# `completed` may mark it finished or navigate to the results page.
	var finalizing := {"seen": 0, "problem": ""}
	main.bridge.event_received.connect(func(event: Dictionary):
		if str(event.get("phase", "")) != "finalizing":
			return
		finalizing.seen += 1
		if main.progress_bar.value >= 1.0:
			finalizing.problem = "bar full during finalizing"
		if main.progress_detail_label.text != main.tr("PROGRESS_FINALIZING"):
			finalizing.problem = "message missing: " + main.progress_detail_label.text
		if main.status_key != "RUNNING" or not main.is_analysis_running:
			finalizing.problem = "run state left RUNNING during finalizing"
		if main.cancel_button.disabled:
			finalizing.problem = "cancel disabled during finalizing"
		if main.tabs.current_tab == 3:
			finalizing.problem = "results page shown before completion")
	main._on_run_pressed()
	assert(main.is_analysis_running)
	assert(main.run_button.disabled)
	assert(not main.cancel_button.disabled)
	assert(not main.data_path_edit.editable)
	assert(main.task_option.disabled)
	assert(main.feature_list.mouse_filter == Control.MOUSE_FILTER_IGNORE)
	await _capture_state(main, "07-running.png")
	result_dir = main._build_config().output_dir
	var result_path := result_dir.path_join("result.json")
	var finished := await _wait_for_result(main, result_dir, result_path, "classification")
	if not finished:
		return
	var result = JSON.parse_string(FileAccess.get_file_as_string(result_path))
	assert(result.status == "completed")
	assert(result.task == "classification")
	assert(result.evaluation_scope == "nested_selection_procedure")
	assert(result.evaluated_combinations == 4)
	assert(finalizing.seen > 0, "no finalizing event was reported")
	assert(finalizing.problem.is_empty(), finalizing.problem)
	assert(main.tabs.current_tab == 3)
	assert(main.metrics_tree.get_root().get_first_child() != null)
	assert(main.comparison_tree.get_root().get_first_child() != null)
	assert(main.comparison_tree.get_column_title(0) == "排名")
	assert(main.metrics_tree.get_root().get_first_child().get_text(0) == "准确率（Accuracy）")
	assert(main.figure_view.texture != null)
	assert(main.progress_bar.value == 1.0)
	assert(main.progress_detail_label.text == "全部任务已完成。")
	assert(not main.is_analysis_running)
	assert(main.data_path_edit.editable)
	assert(not main.task_option.disabled)
	assert(main.feature_list.mouse_filter == Control.MOUSE_FILTER_STOP)
	assert(not main.open_results_button.disabled)
	# Changing the root only affects later runs; the completed training run folder
	# stays the open target and its files are not moved.
	var finished_dir: String = main.last_result_dir
	assert(finished_dir == result_dir, finished_dir)
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml 换根 %d" % Time.get_ticks_msec())
	main._refresh_review()
	assert(main.last_result_dir == finished_dir)
	assert(main.open_results_button.tooltip_text == finished_dir)
	main.output_edit.text = root_dir
	main._refresh_review()
	assert(main.last_result_dir == finished_dir)
	assert(DirAccess.dir_exists_absolute(finished_dir))
	# FR-019: legacy `run_*` folders directly under the root keep loading exactly
	# where they are. Loading must not migrate them into training/ or rewrite the
	# existing files, and their CSV artifacts still preview.
	var legacy_dir := TestPaths.temp_dir().path_join("psyml legacy run %d" % Time.get_ticks_msec())
	DirAccess.make_dir_recursive_absolute(legacy_dir)
	var legacy_file := FileAccess.open(legacy_dir.path_join("model_comparison.csv"), FileAccess.WRITE)
	legacy_file.store_string("rank,model,validation,selection_metric,selection_score,status\n1,decision_tree,holdout,accuracy,0.9,completed\n")
	legacy_file.close()
	legacy_file = FileAccess.open(legacy_dir.path_join("predictions.csv"), FileAccess.WRITE)
	legacy_file.store_string("observed,predicted\n0,0\n1,1\n")
	legacy_file.close()
	legacy_file = FileAccess.open(legacy_dir.path_join("result.json"), FileAccess.WRITE)
	legacy_file.store_string(JSON.stringify({
		"status": "completed",
		"task": "classification",
		"metrics": {"accuracy": 0.9},
		"best_model": "decision_tree",
		"best_validation": "holdout",
		"selection_metric": "accuracy",
		"best_parameters": {},
		"artifacts": {"model_comparison": "model_comparison.csv", "predictions": "predictions.csv"},
	}, "  "))
	legacy_file.close()
	var legacy_result := legacy_dir.path_join("result.json")
	var legacy_before := FileAccess.get_file_as_string(legacy_result)
	main._load_results(legacy_result)
	await process_frame
	assert(main.last_result_dir == CoreBridge.canonical_path(legacy_dir), main.last_result_dir)
	assert(not main.open_results_button.disabled)
	assert(main.metrics_tree.get_root().get_first_child() != null)
	assert(main.predictions_tree.get_root().get_first_child() != null, "legacy predictions.csv must preview")
	assert(FileAccess.get_file_as_string(legacy_result) == legacy_before, "legacy result.json must not be rewritten")
	assert(not DirAccess.dir_exists_absolute(legacy_dir.path_join("training")), "legacy run must not be migrated")
	assert(DirAccess.open(legacy_dir).get_directories().is_empty(), "loading a legacy run must not create folders")
	for index in range(main.task_option.item_count):
		if main.task_option.get_item_metadata(index) == "regression":
			main.task_option.select(index)
			break
	main._on_task_changed()
	var regression_dir := TestPaths.temp_dir().path_join(
		"psyml godot regression %d" % Time.get_ticks_msec()
	)
	main.output_edit.text = regression_dir
	main._on_run_pressed()
	assert(main.last_result_dir.is_empty())
	assert(main.open_results_button.disabled)
	assert(main.figure_view.texture == null)
	regression_dir = main._build_config().output_dir
	var regression_result_path := regression_dir.path_join("result.json")
	var regression_finished := await _wait_for_result(
		main, regression_dir, regression_result_path, "regression"
	)
	if not regression_finished:
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
	main.output_edit.text = TestPaths.temp_dir().path_join(
		"psyml godot cancel %d" % Time.get_ticks_msec()
	)
	main._on_run_pressed()
	await create_timer(0.15).timeout
	assert(main.bridge.is_running())
	main._request_cancel()
	assert(main.status_key == "CANCELLED")
	await _capture_state(main, "08-stopped.png")
	assert(not main.is_analysis_running)
	assert(not main.bridge.is_running())
	assert(main.pending_config_path.is_empty())
	assert(not main.run_button.disabled)
	assert(main.last_result_dir.is_empty())
	assert(main.metrics_tree.get_root() == null)
	assert(main.open_results_button.disabled)
	# Force a real core failure after cancellation, then retry successfully.
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) == "dummy":
			main.model_list.select(index, false)
	main.tuning_option.select(0)
	main._populate_parameter_editor()
	for index in range(main.group_option.item_count):
		if main.group_option.get_item_metadata(index) == "participant":
			main.group_option.select(index)
	main._on_column_role_changed()
	for index in range(main.validation_list.item_count):
		main.validation_list.deselect(index)
		if main.validation_list.get_item_metadata(index) == "group_k_fold":
			main.validation_list.select(index, false)
	main.folds_spin.value = 20
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-invalid-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	var failure_deadline := Time.get_ticks_msec() + 20000
	while main.is_analysis_running and Time.get_ticks_msec() < failure_deadline:
		await create_timer(0.05).timeout
	assert(main.status_key == "ERROR", main.status_label.text)
	await _capture_state(main, "09-error.png")
	assert(main.last_result_dir.is_empty())
	assert(main.figure_view.texture == null)
	assert(main.open_results_button.disabled)
	main.folds_spin.value = 3
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-recovery-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	var recovery_deadline := Time.get_ticks_msec() + 20000
	while main.is_analysis_running and Time.get_ticks_msec() < recovery_deadline:
		await create_timer(0.05).timeout
	assert(main.status_key == "COMPLETED", main.status_label.text)
	assert(not main.last_result_dir.is_empty())
	main._on_language_selected(1)
	assert(main.comparison_tree.get_column_title(0) == "Rank")
	assert(main.best_result_label.text.begins_with("Final fit"))
	main._on_language_selected(2)
	assert(main.run_button.text == "Exécuter l’analyse")
	assert(main.tabs.get_tab_title(3) == "3  Résultats")
	assert(main.comparison_tree.get_column_title(0) == "Rang")
	print("PSYML_GODOT_UI_FLOW_OK")
	quit(0)


func _wait_for_result(main, result_dir: String, result_path: String, label: String) -> bool:
	var expected := CoreBridge.canonical_path(result_dir)
	var deadline := TestPaths.run_deadline_msec()
	while Time.get_ticks_msec() < deadline:
		if FileAccess.file_exists(result_path) and main.last_result_dir == expected:
			break
		if main.status_key in ["ERROR", "CANCELLED"]:
			break
		await create_timer(0.05).timeout
	if FileAccess.file_exists(result_path) and main.last_result_dir == expected:
		return true
	var diagnostic := _diagnostic_text(main, label, result_dir, result_path)
	var diagnostic_path := TestPaths.log_directory().path_join("ui_flow_failure.txt")
	var file := FileAccess.open(diagnostic_path, FileAccess.WRITE)
	if file != null:
		file.store_string(diagnostic)
		file.close()
	for line in diagnostic.split("\n"):
		if not line.is_empty():
			printerr("PSYML_UI_FLOW_DIAGNOSTIC " + line)
	push_error("PSYML_UI_FLOW_TIMEOUT " + label + " expected=" + expected)
	quit(1)
	return false


func _diagnostic_text(main, label: String, result_dir: String, result_path: String) -> String:
	var stderr_tail: String = main.bridge.last_stderr_tail(2000)
	var lines := [
		"label=" + label,
		"status_key=" + str(main.status_key),
		"status_label=" + str(main.status_label.text),
		"status_detail=" + str(main.status_detail),
		"expected_dir=" + CoreBridge.canonical_path(result_dir),
		"actual_dir=" + CoreBridge.canonical_path(str(main.last_result_dir)),
		"expected_dir_raw=" + result_dir,
		"actual_dir_raw=" + str(main.last_result_dir),
		"result_file_exists=" + ("yes" if FileAccess.file_exists(result_path) else "no"),
		"result_path=" + CoreBridge.canonical_path(result_path),
		"last_result_path=" + str(main.last_result_path),
		"bridge_running=" + ("yes" if main.bridge.is_running() else "no"),
		"bridge_last_exit_code=" + str(main.bridge.last_process_exit_code()),
		"pending_config=" + str(main.pending_config_path),
		"language=" + TranslationServer.get_locale(),
		"stderr_tail_begin",
		stderr_tail,
		"stderr_tail_end",
	]
	return "\n".join(lines)


func _capture_state(main: Control, filename: String) -> void:
	var directory := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if directory.is_empty():
		return
	DirAccess.make_dir_recursive_absolute(directory)
	main.tabs.current_tab = 2
	await process_frame
	await process_frame
	root.get_viewport().get_texture().get_image().save_png(directory.path_join(filename))
