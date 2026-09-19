extends SceneTree
## GUI regression for permutation-importance settings, results and cleanup.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_run_test")


func _wait_run(main) -> void:
	var deadline := Time.get_ticks_msec() + 60000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.is_analysis_running, main.status_detail)


func _select_values(list: ItemList, values: Array) -> void:
	for index in range(list.item_count):
		list.deselect(index)
		if list.get_item_metadata(index) in values:
			list.select(index, false)


func _choose_result(main, validation: String) -> void:
	for index in range(main.validation_result_option.item_count):
		if main.validation_result_option.get_item_metadata(index) == validation:
			main.validation_result_option.select(index)
			main._on_validation_result_selected(index)
			return
	assert(false, "Missing validation result: " + validation)


func _select_roles(main, fixture: String) -> void:
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
	main._refresh_review()


func _enable(main, repeats: int) -> void:
	main.permutation_ui.enable_check.button_pressed = true
	main.permutation_ui.repeats_spin.value = repeats
	main._refresh_review()


func _disable(main) -> void:
	main.permutation_ui.enable_check.button_pressed = false
	main._refresh_review()


func _run_test() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	assert(main.permutation_ui != null)
	var fixture := ProjectSettings.globalize_path("res://../examples/synthetic/classification.csv")
	await _select_roles(main, fixture)
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) == "decision_tree":
			main.model_list.select(index, false)
	_select_values(main.validation_list, ["group_k_fold"])
	main.folds_spin.value = 3
	main.primary_validation_option.select(1)
	main._refresh_review()

	# New config fields round-trip through the GUI and survive a language switch.
	_enable(main, 2)
	var config: Dictionary = main._build_config()
	assert(config.permutation_importance == true)
	assert(config.permutation_repeats == 2)
	main._on_language_selected(1)
	config = main._build_config()
	assert(config.permutation_importance == true, "language switch reset the switch")
	assert(config.permutation_repeats == 2, "language switch reset the repeats")
	main._on_language_selected(2)
	config = main._build_config()
	assert(config.permutation_repeats == 2)
	main._on_language_selected(0)
	# A legacy configuration without the new keys loads as OFF.
	main.permutation_ui.apply_configuration({"permutation_importance": false, "permutation_repeats": 10})
	assert(main.permutation_ui.enable_check.button_pressed == false)
	assert(int(main.permutation_ui.repeats_spin.value) == 10)

	# Enabled run writes and displays interpretation artefacts.
	_enable(main, 2)
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-perm-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	assert(main.permutation_ui.enable_check.disabled, "switch must be disabled while running")
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	var result = JSON.parse_string(FileAccess.get_file_as_string(main.last_result_path))
	assert(result.permutation.enabled == true)
	assert(result.permutation.validations.has("group_k_fold"))
	var interpretation_dir: String = main.last_result_dir.path_join("interpretations/group_k_fold")
	for name in ["permutation_raw.csv", "permutation_folds.csv", "permutation_summary.csv", "permutation.json", "permutation_importance.png"]:
		assert(FileAccess.file_exists(interpretation_dir.path_join(name)), name)
	assert(main.permutation_ui.summary_tree.visible)
	assert(main.permutation_ui.summary_tree.get_root() != null)
	var first_summary_row = main.permutation_ui.summary_tree.get_root().get_first_child()
	assert(first_summary_row != null, "summary rows expected")
	# Long variable names are ellipsized; the full name must stay inspectable.
	var variable_text: String = first_summary_row.get_text(0)
	assert(not variable_text.is_empty(), "variable name expected")
	assert(first_summary_row.get_tooltip_text(0) == variable_text,
		"summary variable cell must expose the full name as a tooltip")
	assert(not main.permutation_ui.status_label.text.is_empty())
	var permutation_figure := false
	for index in range(main.figure_option.item_count):
		if str(main.figure_option.get_item_metadata(index)).ends_with("permutation_importance.png"):
			permutation_figure = true
	assert(permutation_figure, "permutation figure must be selectable")

	# OFF run must clear old interpretation state and write no interpretation files.
	_disable(main)
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-perm-off-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	var off_result = JSON.parse_string(FileAccess.get_file_as_string(main.last_result_path))
	assert(not off_result.has("permutation"))
	assert(not DirAccess.dir_exists_absolute(main.last_result_dir.path_join("interpretations")))
	assert(main.permutation_ui.summary_tree.visible == false)
	assert(main.permutation_ui.current_validation == "")

	# Independent validations: each child keeps its own interpretation; a failed
	# validation clears the previous child's summary.
	_enable(main, 2)
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) in ["decision_tree", "dummy"]:
			main.model_list.select(index, false)
	_select_values(main.validation_list, ["holdout", "group_k_fold"])
	main.folds_spin.value = 3
	main.primary_validation_option.select(0)
	main._refresh_review()
	assert(main._build_config().primary_validation == null)
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-perm-ind-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	assert(main.validation_result_option.visible)
	assert(main.permutation_ui.summary_tree.visible == false, "root independent view has no summary")
	_choose_result(main, "holdout")
	assert(main.permutation_ui.current_validation == "holdout")
	assert(main.permutation_ui.summary_tree.visible)
	assert(main.last_result_dir.ends_with("validations/holdout"))
	_choose_result(main, "group_k_fold")
	assert(main.permutation_ui.current_validation == "group_k_fold")
	assert(main.permutation_ui.summary_tree.visible)
	main._on_language_selected(1)
	assert(main.permutation_ui.current_validation == "group_k_fold")
	main._on_language_selected(0)

	# A failing validation must not show the previous successful interpretation.
	main.folds_spin.value = 20
	main._on_run_pressed()
	await _wait_run(main)
	var partial = JSON.parse_string(FileAccess.get_file_as_string(main.last_result_path))
	assert(partial.status == "completed_with_errors")
	_choose_result(main, "group_k_fold")
	assert(main.permutation_ui.summary_tree.visible == false, "failed validation must clear the summary")
	assert(main.permutation_ui.current_validation == "")

	# Cancelling mid-run clears the result area and re-enables the controls.
	_select_values(main.validation_list, ["k_fold"])
	main.folds_spin.value = 20
	_enable(main, 100)
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-perm-cancel-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await create_timer(0.3).timeout
	main._request_cancel()
	assert(main.status_key == "CANCELLED", main.status_detail)
	assert(main.permutation_ui.summary_tree.visible == false)
	assert(main.permutation_ui.current_validation == "")
	assert(main.permutation_ui.enable_check.disabled == false)
	print("PSYML_PERMUTATION_OK")
	quit(0)
