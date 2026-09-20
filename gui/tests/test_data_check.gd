extends SceneTree
## GUI regression for the data check: category counts, identifier hints,
## role/task/group switching, language and stale-state clearing.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_run_test")


func _wait_preview(main) -> void:
	var deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not main.preview_payload.is_empty(), main.status_detail)


func _select_option(option: OptionButton, value) -> int:
	for index in range(option.item_count):
		if option.get_item_metadata(index) == value:
			option.select(index)
			return index
	return -1


func _run_test() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	assert(main.data_check_ui != null, "data check helper must be built")

	var fixture := ProjectSettings.globalize_path("res://../examples/synthetic/classification.csv")
	main._on_file_selected(fixture)
	await _wait_preview(main)

	# Classification target shows observed category counts (not estimated from the sample).
	_select_option(main.target_option, "target")
	main._on_column_role_changed()
	assert(main.data_check_ui.summary_label.visible, "target summary expected")
	assert(main.data_check_ui.category_tree.visible, "category tree expected")
	assert(main.data_check_ui.category_tree.size.y > 0, "category tree must have layout height")
	assert(
		main.data_check_ui.category_tree.is_visible_in_tree(),
		"category table must actually be shown in the scene, not only flagged visible",
	)
	var root_item = main.data_check_ui.category_tree.get_root()
	assert(root_item != null and root_item.get_child_count() >= 2, "two observed target classes")
	assert(
		main.data_check_ui.category_tree.get_column_title(1) == main.tr("DATA_CHECK_TABLE_COUNT"),
		"per-class count column must not be labelled as missing",
	)
	assert(
		main.data_check_ui.category_tree.get_column_title(2) == main.tr("DATA_CHECK_TABLE_SHARE"),
		"proportion column must be labelled as share of non-missing",
	)
	var summary_text: String = main.data_check_ui.summary_label.text
	assert(summary_text.contains("target"), "target name must be stated")
	assert(summary_text.contains("48"), "total row count must be stated")

	# The participant column is flagged as a suspected identifier with a reason.
	assert(main.data_check_ui.id_label.visible, "identifier hint expected")
	assert(main.data_check_ui.id_label.text.contains("participant"))

	# Switching target refreshes the listed categories without stale values.
	_select_option(main.target_option, "category")
	main._on_column_role_changed()
	var category_root = main.data_check_ui.category_tree.get_root()
	assert(category_root.get_child_count() == 2, "category column has two observed values")

	# Regression tasks do not show classification category proportions.
	main.task_option.select(1)
	main._on_task_changed()
	assert(main.data_check_ui.category_tree.visible == false, "regression hides categories")
	main.task_option.select(0)
	main._on_task_changed()
	main._on_column_role_changed()
	assert(main.data_check_ui.category_tree.visible, "classification restores categories")

	# Language switching keeps content and does not leak the previous language.
	main._on_language_selected(1)
	assert(main.data_check_ui.category_tree.visible)
	assert(not main.data_check_ui.summary_label.text.is_empty())
	main._on_language_selected(0)

	# An invalid data path clears stale statistics.
	main.data_path_edit.text = "/nonexistent/psyml.csv"
	main._on_data_path_changed("/nonexistent/psyml.csv")
	assert(main.data_check_ui.category_tree.visible == false, "stale stats must clear")

	# All-missing target: exact totals are still shown with 0 categories, and the
	# state is clearly distinguished from privacy suppression.
	main.preview_payload = {
		"row_count": 5,
		"column_count": 1,
		"columns": [{
			"name": "target",
			"identifier_suspected": false,
			"identifier_signals": [],
			"nonmissing_count": 0,
			"missing_count": 5,
			"category_count": 0,
			"value_counts": [],
		}],
	}
	main.task_option.select(0)
	main.target_option.clear()
	main.target_option.add_item("target")
	main.target_option.set_item_metadata(0, "target")
	main.target_option.select(0)
	main.data_check_ui.refresh()
	assert(main.data_check_ui.summary_label.visible, "totals must survive an all-missing target")
	assert(main.data_check_ui.summary_label.text.contains(main.tr("DATA_CHECK_NO_CATEGORIES")))
	assert(main.data_check_ui.category_tree.visible == false, "no fabricated classes")
	assert(not main.data_check_ui.summary_label.text.contains("0.0%"), "no invented proportions")

	# Privacy suppression (no sampled values key): totals stay exact, no classes.
	main.preview_payload = {
		"row_count": 4,
		"column_count": 1,
		"columns": [{
			"name": "target",
			"identifier_suspected": false,
			"identifier_signals": [],
			"nonmissing_count": 3,
			"missing_count": 1,
			"category_count": 2,
		}],
	}
	main.data_check_ui.refresh()
	assert(main.data_check_ui.summary_label.visible)
	assert(main.data_check_ui.summary_label.text.contains(main.tr("DATA_CHECK_SAMPLE_ONLY")))
	assert(not main.data_check_ui.summary_label.text.contains(main.tr("DATA_CHECK_NO_CATEGORIES")))
	assert(main.data_check_ui.category_tree.visible == false, "private values must not be shown")

	# Zero rows: zero totals, still explicit and distinct from privacy suppression.
	main.preview_payload = {
		"row_count": 0,
		"column_count": 1,
		"columns": [{
			"name": "target",
			"identifier_suspected": false,
			"identifier_signals": [],
			"nonmissing_count": 0,
			"missing_count": 0,
			"category_count": 0,
			"value_counts": [],
		}],
	}
	main.data_check_ui.refresh()
	assert(main.data_check_ui.summary_label.visible)
	assert(main.data_check_ui.summary_label.text.contains(main.tr("DATA_CHECK_NO_CATEGORIES")))

	# Identifier reasons are localized from structured signals, not English prose.
	main.preview_payload = {
		"row_count": 30,
		"column_count": 2,
		"columns": [
			{"name": "target", "identifier_suspected": false, "identifier_signals": [],
				"nonmissing_count": 30, "missing_count": 0, "category_count": 2, "value_counts": []},
			{
				"name": "participant_id",
				"identifier_suspected": true,
				"identifier_signals": ["name_token", "near_unique_values"],
				"unique_count": 30,
				"nonmissing_count": 30,
				"unique_ratio": 1.0,
			},
		],
	}
	main._on_language_selected(0)
	main.data_check_ui.refresh()
	assert(main.data_check_ui.id_label.visible)
	assert(main.data_check_ui.id_label.text.contains(main.tr("DATA_CHECK_ID_REASON_NAME")))
	assert(main.data_check_ui.id_label.text.contains("30/30"))
	assert(main.data_check_ui.id_label.text.contains("1.00"))
	assert(not main.data_check_ui.id_label.text.contains("column name contains"))
	main._on_language_selected(1)
	assert(main.data_check_ui.id_label.text.contains(main.tr("DATA_CHECK_ID_REASON_NAME")))
	assert(not main.data_check_ui.id_label.text.contains("列名含"))
	main._on_language_selected(2)
	assert(main.data_check_ui.id_label.text.contains(main.tr("DATA_CHECK_ID_REASON_NAME")))
	main._on_language_selected(0)

	print("PSYML_DATA_CHECK_OK")
	quit(0)
