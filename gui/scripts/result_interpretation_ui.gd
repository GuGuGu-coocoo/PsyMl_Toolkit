extends RefCounted
## Result interpretation: compact trilingual summary of the baseline
## difference, between-fold variability and failure hierarchy for one result.
##
## Reads `result_interpretation.json` written by the runner; never recomputes
## science and never lets a comparison change selection.

const REASON_KEYS := {
	"baseline_not_selected": "INTERPRETATION_REASON_NOT_SELECTED",
	"baseline_not_run_or_failed": "INTERPRETATION_REASON_NOT_RUN",
	"procedure_failed": "INTERPRETATION_REASON_PROCEDURE_FAILED",
	"fold_sets_differ": "INTERPRETATION_REASON_FOLDS",
	"non_finite_matched_scores": "INTERPRETATION_REASON_NONFINITE",
	"metric_missing_from_procedure": "INTERPRETATION_REASON_METRIC",
	"metric_missing_from_baseline": "INTERPRETATION_REASON_METRIC",
	"unknown_metric_direction": "INTERPRETATION_REASON_UNKNOWN",
}

var main: Control
var heading: Label
var status_label: Label
var baseline_label: Label
var failures_label: Label
var note_label: Label
var diff_tree: Tree
var current_interpretation: Dictionary = {}
var current_validation := ""


func _init(owner: Control) -> void:
	main = owner


func build() -> void:
	var parent: Node = main.predictions_tree.get_parent()
	heading = Label.new()
	heading.add_theme_font_size_override("font_size", 18)
	parent.add_child(heading)
	main.translated_controls.append({"node": heading, "key": "INTERPRETATION_RESULT_SECTION"})

	status_label = Label.new()
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(status_label)

	baseline_label = Label.new()
	baseline_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(baseline_label)

	failures_label = Label.new()
	failures_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(failures_label)

	diff_tree = Tree.new()
	diff_tree.custom_minimum_size = Vector2(0, 150)
	diff_tree.columns = 3
	diff_tree.column_titles_visible = true
	diff_tree.hide_root = true
	parent.add_child(diff_tree)

	note_label = Label.new()
	note_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note_label.add_theme_color_override("font_color", Color("626977"))
	parent.add_child(note_label)
	main.translated_controls.append({"node": note_label, "key": "INTERPRETATION_DESCRIPTIVE"})
	clear()


func clear() -> void:
	current_interpretation = {}
	current_validation = ""
	if heading == null:
		return
	heading.hide()
	status_label.text = ""
	status_label.hide()
	baseline_label.text = ""
	baseline_label.hide()
	failures_label.text = ""
	failures_label.hide()
	diff_tree.clear()
	diff_tree.hide()
	note_label.hide()


func load_result(parsed: Dictionary, result_dir: String) -> void:
	clear()
	var artifacts: Dictionary = parsed.get("artifacts", {})
	var relative := str(artifacts.get("result_interpretation", ""))
	if relative.is_empty():
		heading.show()
		status_label.text = main.tr("INTERPRETATION_NO_FILE")
		status_label.show()
		return
	var file := FileAccess.open(result_dir.path_join(relative), FileAccess.READ)
	if file == null:
		heading.show()
		status_label.text = main.tr("INTERPRETATION_NO_FILE")
		status_label.show()
		return
	var parsed_interpretation = JSON.parse_string(file.get_as_text())
	if not parsed_interpretation is Dictionary:
		heading.show()
		status_label.text = main.tr("INTERPRETATION_NO_FILE")
		status_label.show()
		return
	current_interpretation = parsed_interpretation
	heading.show()
	note_label.show()
	_render(parsed)


func _render(parsed: Dictionary) -> void:
	# Every render starts from a clean block so language switches and result
	# transitions never accumulate duplicate rows or stale labels.
	status_label.text = ""
	status_label.hide()
	baseline_label.text = ""
	baseline_label.hide()
	failures_label.text = ""
	failures_label.hide()
	diff_tree.clear()
	diff_tree.hide()
	var validation := str(parsed.get("best_validation", ""))
	if validation.is_empty():
		validation = str(current_interpretation.get("primary_validation", ""))
	var validations: Dictionary = current_interpretation.get("validations", {})
	if not validations.has(validation):
		for key in validations.keys():
			validation = str(key)
			break
	current_validation = validation
	var entry: Dictionary = validations.get(validation, {})
	if entry.is_empty():
		status_label.text = main.tr("INTERPRETATION_NO_FILE")
		status_label.show()
		return
	var metric := str(current_interpretation.get("selection_metric", ""))
	var summaries: Dictionary = entry.get("metric_summaries", {})
	var selection: Dictionary = summaries.get(metric, {})
	var status_line := ""
	if entry.get("status") == "completed" and not selection.is_empty():
		var mean_text := _number(selection.get("mean"))
		var std_text := _number(selection.get("std"))
		status_line = main.tr("INTERPRETATION_SELECTION") % [
			main._validation_display(validation),
			main._metric_display(metric),
			mean_text,
			std_text,
			str(int(selection.get("n_folds", 0))),
		]
		if selection.get("std") == null:
			status_line += " · " + main.tr("INTERPRETATION_NO_STD")
	status_label.text = status_line
	if status_line.is_empty():
		status_label.hide()
	else:
		status_label.show()

	var comparison: Dictionary = entry.get("baseline_comparison", {})
	if comparison.get("status") == "comparable":
		baseline_label.text = main.tr("INTERPRETATION_BASELINE_OK") % [
			_number(comparison.get("mean_difference")),
			str(int(comparison.get("n_paired_folds", 0))),
			str(int(comparison.get("n_folds_procedure", 0))),
		]
		_render_differences(comparison.get("per_fold", []))
	else:
		baseline_label.text = main.tr("INTERPRETATION_BASELINE_NONE") % _reason_text(
			str(comparison.get("reason", ""))
		)
	baseline_label.show()

	var failures: Dictionary = entry.get("failures", {})
	if not failures.is_empty():
		failures_label.text = main.tr("INTERPRETATION_FAILURES") % [
			_failure_field(failures, "inner_candidate"),
			_failure_field(failures, "outer_model_validation"),
			_failure_field(failures, "validation_procedure"),
		]
		failures_label.show()


## Failure counts accept both the primary nested shape and the independent flat
## shape; an unknown (null) count is shown as unavailable, never as zero.
func _failure_field(failures: Dictionary, level: String) -> String:
	var value = failures.get(level)
	if value is Dictionary:
		value = value.get("count")
	if value == null:
		return "—"
	return str(int(value))


func _render_differences(per_fold: Array) -> void:
	if per_fold.is_empty():
		diff_tree.hide()
		return
	diff_tree.columns = 3
	diff_tree.set_column_title(0, main.tr("FOLDS"))
	diff_tree.set_column_title(1, main._metric_display(str(current_interpretation.get("selection_metric", ""))))
	diff_tree.set_column_title(2, main.tr("COLUMN_DIFFERENCE"))
	for index in range(3):
		diff_tree.set_column_custom_minimum_width(index, 120 if index == 1 else 90)
		diff_tree.set_column_expand(index, index == 1)
	var root := diff_tree.create_item()
	for fold in per_fold:
		var item := diff_tree.create_item(root)
		item.set_text(0, str(int(fold.get("fold", 0))))
		item.set_text(1, _number(fold.get("procedure_value")))
		item.set_text(2, _number(fold.get("difference")))
		item.set_tooltip_text(2, main.tr("COLUMN_BASELINE") + ": " + _number(fold.get("baseline_value")))
	diff_tree.show()


func _reason_text(reason: String) -> String:
	var key: String = REASON_KEYS.get(reason, "INTERPRETATION_REASON_UNKNOWN")
	return main.tr(key)


func _number(value) -> String:
	if value == null:
		return "—"
	# Godot's % formatting has no %g; trim a fixed-precision representation instead.
	var text := "%.6f" % float(value)
	while text.contains(".") and (text.ends_with("0") or text.ends_with(".")):
		text = text.substr(0, text.length() - 1)
	return text


func refresh_language() -> void:
	if heading == null:
		return
	heading.text = main.tr("INTERPRETATION_RESULT_SECTION")
	note_label.text = main.tr("INTERPRETATION_DESCRIPTIVE")
	if not current_interpretation.is_empty():
		# Re-render with the active locale after a language switch.
		_render({"best_validation": current_validation})
