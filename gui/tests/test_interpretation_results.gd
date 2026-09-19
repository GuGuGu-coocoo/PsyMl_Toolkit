extends SceneTree
## GUI regression for FR-009 result interpretation: baseline difference,
## fold variability, failure/uncertainty states and no stale results.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_run_test")


func _wait_run(main) -> void:
	var deadline := Time.get_ticks_msec() + 180000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.is_analysis_running, main.status_detail)


func _wait_preview(main) -> void:
	var deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)


func _select_option(option: OptionButton, value) -> void:
	for index in range(option.item_count):
		if option.get_item_metadata(index) == value:
			option.select(index)
			return
	assert(false, "option value not found: " + str(value))


func _select_values(list: ItemList, values: Array) -> void:
	for index in range(list.item_count):
		list.deselect(index)
		if list.get_item_metadata(index) in values:
			list.select(index, false)


func _select_models(main, names: Array) -> void:
	_select_values(main.model_list, names)
	main._refresh_review()


func _choose_result(main, validation: String) -> void:
	for index in range(main.validation_result_option.item_count):
		if main.validation_result_option.get_item_metadata(index) == validation:
			main.validation_result_option.select(index)
			main._on_validation_result_selected(index)
			return
	assert(false, "Missing validation result: " + validation)


func _prepare(main) -> void:
	var fixture := ProjectSettings.globalize_path("res://../examples/synthetic/classification.csv")
	main._on_file_selected(fixture)
	await _wait_preview(main)
	_select_option(main.target_option, "target")
	main._on_column_role_changed()
	for index in range(main.feature_list.item_count):
		main.feature_list.deselect(index)
		if main.feature_list.get_item_metadata(index) == "score":
			main.feature_list.select(index, false)
	main.folds_spin.value = 3
	main.inner_folds_spin.value = 2
	main._refresh_review()


func _crafted(status: String, per_fold: Array) -> Dictionary:
	var folds_count: int = per_fold.size()
	var comparable: bool = not per_fold.is_empty()
	return {
		"selection_metric": "balanced_accuracy",
		"primary_validation": "holdout",
		"validations": {
			"holdout": {
				"status": status,
				"metric_summaries": {
					"balanced_accuracy": {"mean": 0.8, "std": null, "n_folds": folds_count}
				},
				"baseline_comparison": {
					"status": "comparable" if comparable else "not_comparable",
					"reason": "" if comparable else "baseline_not_selected",
					"mean_difference": 0.25 if comparable else null,
					"n_paired_folds": folds_count,
					"n_folds_procedure": folds_count,
					"per_fold": per_fold,
				},
				"failures": {
					"inner_candidate": {"count": 1},
					"outer_model_validation": {"count": 0},
					"validation_procedure": {"count": 0},
				},
			}
		},
	}


func _run_test() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	assert(main.interpretation_ui != null, "interpretation helper must be built")
	await _prepare(main)

	# Comparable baseline: dummy and decision_tree on the same validation.
	_select_values(main.validation_list, ["stratified_k_fold"])
	_select_models(main, ["decision_tree", "dummy"])
	main._update_primary_validation()
	main.primary_validation_option.select(1)
	main._refresh_review()
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-interp-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	var result = JSON.parse_string(FileAccess.get_file_as_string(main.last_result_path))
	assert(result.artifacts.get("result_interpretation", "") == "result_interpretation.json")
	assert(FileAccess.file_exists(main.last_result_dir.path_join("result_interpretation.json")))
	assert(FileAccess.file_exists(main.last_result_dir.path_join("interpretation_baseline_differences.csv")))
	assert(main.interpretation_ui.heading.visible)
	assert(main.interpretation_ui.current_validation == "stratified_k_fold")
	assert(not main.interpretation_ui.status_label.text.is_empty())
	assert(main.interpretation_ui.status_label.text.contains("ddof=0"))
	assert(main.interpretation_ui.baseline_label.visible)
	assert(main.interpretation_ui.baseline_label.text.contains("dummy"))
	assert(main.interpretation_ui.diff_tree.visible)
	assert(main.interpretation_ui.diff_tree.get_root().get_child_count() == 3)
	assert(main.interpretation_ui.failures_label.visible)

	# Language switch must keep the interpreted validation and content.
	main._on_language_selected(1)
	assert(main.interpretation_ui.current_validation == "stratified_k_fold")
	assert(not main.interpretation_ui.baseline_label.text.is_empty())
	main._on_language_selected(0)

	# No dummy selected: the baseline must be explicitly unavailable, not invented.
	_select_models(main, ["decision_tree"])
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-interp-nb-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	assert(main.interpretation_ui.current_validation == "stratified_k_fold")
	assert(main.interpretation_ui.baseline_label.visible)
	assert(main.interpretation_ui.diff_tree.visible == false, "no fabricated fold differences")
	assert(main.interpretation_ui.baseline_label.text.length() > 0)

	# Independent validations: each child keeps its own interpretation.
	_select_values(main.validation_list, ["holdout", "stratified_k_fold"])
	_select_models(main, ["decision_tree", "dummy"])
	main._update_primary_validation()
	main.primary_validation_option.select(0)
	main.folds_spin.value = 3
	main._refresh_review()
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml-interp-ind-%d" % Time.get_ticks_usec())
	main._on_run_pressed()
	await _wait_run(main)
	assert(main.status_key == "COMPLETED", main.status_detail)
	assert(main.validation_result_option.visible)
	_choose_result(main, "holdout")
	assert(main.interpretation_ui.current_validation == "holdout")
	assert(FileAccess.file_exists(main.last_result_dir.path_join("result_interpretation.json")))
	_choose_result(main, "stratified_k_fold")
	assert(main.interpretation_ui.current_validation == "stratified_k_fold")

	# A fresh run clears the previous interpretation before writing new results.
	main._clear_results()
	assert(main.interpretation_ui.current_validation == "")
	assert(main.interpretation_ui.heading.visible == false)

	# Rendering must be idempotent across locale cycles: repeated language
	# switches must not accumulate duplicate fold rows.
	var folds := [
		{"fold": 1, "procedure_value": 0.9, "baseline_value": 0.5, "difference": 0.4, "procedure_model": "decision_tree"},
		{"fold": 2, "procedure_value": 0.7, "baseline_value": 0.5, "difference": 0.2, "procedure_model": "decision_tree"},
	]
	main.interpretation_ui.current_interpretation = _crafted("completed", folds)
	main.interpretation_ui._render({"best_validation": "holdout"})
	assert(main.interpretation_ui.diff_tree.get_root().get_child_count() == 2)
	for locale in [1, 2, 0, 1, 0]:
		main._on_language_selected(locale)
		assert(
			main.interpretation_ui.diff_tree.get_root().get_child_count() == 2,
			"locale cycle %d duplicated fold rows" % locale,
		)
		assert(not main.interpretation_ui.baseline_label.text.is_empty())
		assert(main.interpretation_ui.failures_label.visible)
		assert(main.interpretation_ui.baseline_label.text.contains("dummy"))

	# No-baseline transition clears the stale fold rows and labels.
	main._on_language_selected(0)
	main.interpretation_ui.current_interpretation = _crafted("completed", [])
	main.interpretation_ui._render({"best_validation": "holdout"})
	assert(main.interpretation_ui.diff_tree.visible == false, "stale fold rows must be gone")
	assert(main.interpretation_ui.diff_tree.get_root() == null)
	assert(main.interpretation_ui.baseline_label.visible)
	assert(main.interpretation_ui.baseline_label.text.contains(main.tr("INTERPRETATION_REASON_NOT_SELECTED")))

	# Failed transition resets the completed summary but reports the failure.
	var failed_interpretation := _crafted("failed", [])
	failed_interpretation["validations"]["holdout"]["baseline_comparison"] = {
		"status": "not_comparable",
		"reason": "procedure_failed",
		"mean_difference": null,
		"n_paired_folds": 0,
	}
	main.interpretation_ui.current_interpretation = failed_interpretation
	main.interpretation_ui._render({"best_validation": "holdout"})
	assert(main.interpretation_ui.status_label.visible == false, "no stale completed status")
	assert(main.interpretation_ui.baseline_label.visible)
	assert(
		main.interpretation_ui.baseline_label.text.contains(
			main.tr("INTERPRETATION_REASON_PROCEDURE_FAILED")
		)
	)
	assert(main.interpretation_ui.failures_label.visible)
	main._clear_results()

	print("PSYML_INTERPRETATION_OK")
	quit(0)
