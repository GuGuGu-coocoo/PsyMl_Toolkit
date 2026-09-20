extends RefCounted
## Data check: observed category counts/proportions and identifier hints.
##
## Reads only the profiling metadata already returned by `protocol.dataframe_preview`
## (never estimates from the first five sample rows). Values are shown only when
## the interactive sample mode supplied them; the default preview leaks nothing.

var main: Control
var section_label: Label
var summary_label: Label
var category_tree: Tree
var id_title_label: Label
var id_label: Label
var note_label: Label


func _init(owner: Control) -> void:
	main = owner


func build() -> void:
	var parent: Node = main.sample_tree.get_parent() if main.sample_tree != null else main.variable_tree.get_parent()
	section_label = Label.new()
	section_label.add_theme_font_size_override("font_size", 18)
	parent.add_child(section_label)
	main.translated_controls.append({"node": section_label, "key": "DATA_CHECK_SECTION"})

	summary_label = Label.new()
	summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(summary_label)
	summary_label.hide()

	category_tree = Tree.new()
	category_tree.custom_minimum_size = Vector2(0, 150)
	category_tree.columns = 3
	category_tree.column_titles_visible = true
	category_tree.hide_root = true
	category_tree.hide()
	parent.add_child(category_tree)

	id_title_label = Label.new()
	id_title_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	id_title_label.add_theme_font_size_override("font_size", 16)
	parent.add_child(id_title_label)
	id_title_label.hide()

	id_label = Label.new()
	id_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(id_label)
	id_label.hide()

	note_label = Label.new()
	note_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note_label.add_theme_color_override("font_color", Color("626977"))
	parent.add_child(note_label)
	note_label.hide()

	refresh()


## Recompute the whole block from current preview metadata and role selections.
func refresh() -> void:
	if category_tree == null:
		return
	_clear()
	var columns: Array = main.preview_payload.get("columns", []) if not main.preview_payload.is_empty() else []
	if columns.is_empty():
		return
	_render_identifier_hints(columns)
	var task := ""
	if main.task_option != null and main.task_option.item_count > 0:
		task = str(main.task_option.get_item_metadata(main.task_option.selected))
	if task != "classification":
		return
	if main.target_option == null or main.target_option.item_count == 0:
		return
	var target = main.target_option.get_item_metadata(main.target_option.selected)
	if target == null:
		return
	var profile := _column_by_name(columns, str(target))
	if profile.is_empty():
		return
	var value_counts: Array = profile.get("value_counts", [])
	# Exact totals are always stated when target metadata is present, including
	# all-missing and zero-row targets; only the per-class listing is optional.
	summary_label.text = main.tr("DATA_CHECK_TARGET") % [
		str(target),
		int(profile.get("category_count", 0)),
		int(main.preview_payload.get("row_count", 0)),
		int(profile.get("nonmissing_count", 0)),
		int(profile.get("missing_count", 0)),
	]
	summary_label.show()
	if not profile.has("value_counts"):
		# Privacy suppression: the payload came from the non-sampled preview,
		# so we state exact totals but never invent per-class values.
		summary_label.text += "\n" + main.tr("DATA_CHECK_SAMPLE_ONLY")
		return
	if value_counts.is_empty():
		# Sampled mode with nothing observed: distinguish "all missing / empty"
		# from privacy suppression; no proportions are fabricated.
		summary_label.text += "\n" + main.tr("DATA_CHECK_NO_CATEGORIES")
		return
	category_tree.columns = 3
	category_tree.set_column_title(0, main.tr("DATA_CHECK_TABLE_CATEGORY"))
	category_tree.set_column_title(1, main.tr("DATA_CHECK_TABLE_COUNT"))
	category_tree.set_column_title(2, main.tr("DATA_CHECK_TABLE_SHARE"))
	var root := category_tree.create_item()
	for entry in value_counts:
		var item := category_tree.create_item(root)
		item.set_text(0, _value_text(entry.get("value")))
		item.set_text(1, str(int(entry.get("count", 0))))
		item.set_text(2, _fraction_text(entry.get("fraction_of_nonmissing")))
	category_tree.show()
	if bool(profile.get("value_counts_truncated", false)):
		summary_label.text += "\n" + main.tr("DATA_CHECK_CATEGORY_TRUNCATED") % [
			value_counts.size(),
			int(profile.get("value_counts_omitted", 0)),
		]
		summary_label.show()


func _render_identifier_hints(columns: Array) -> void:
	var hints: Array = []
	for column in columns:
		if bool(column.get("identifier_suspected", false)):
			hints.append(column)
	if hints.is_empty():
		return
	id_title_label.text = main.tr("DATA_CHECK_ID_TITLE")
	id_title_label.show()
	var lines: Array = []
	for column in hints:
		lines.append(main.tr("DATA_CHECK_ID_ROW") % [
			str(column.get("name", "")),
			_identifier_reason(column),
		])
	id_label.text = "\n".join(lines)
	id_label.show()
	note_label.text = main.tr("DATA_CHECK_ID_NOTE")
	note_label.show()


## Build a localized reason from the structured signals and numeric counts, never
## from the English backend prose, so zh/en/fr stay consistent.
func _identifier_reason(column: Dictionary) -> String:
	var signals: Array = column.get("identifier_signals", [])
	var parts: Array = []
	if "name_token" in signals:
		parts.append(main.tr("DATA_CHECK_ID_REASON_NAME"))
	if "near_unique_values" in signals:
		parts.append(main.tr("DATA_CHECK_ID_REASON_UNIQUE") % [
			int(column.get("unique_count", 0)),
			int(column.get("nonmissing_count", 0)),
			_ratio_text(column.get("unique_ratio")),
		])
	return "; ".join(parts)


func _ratio_text(value) -> String:
	if value == null:
		return "—"
	return "%.2f" % float(value)


func _column_by_name(columns: Array, name: String) -> Dictionary:
	for column in columns:
		if str(column.get("name", "")) == name:
			return column
	return {}


func _value_text(value) -> String:
	if value == null:
		return "—"
	# JSON parses every number as a float; show whole-number class labels as integers.
	if (value is float or value is int) and float(value) == round(float(value)):
		return str(int(value))
	return str(value)


func _fraction_text(value) -> String:
	if value == null:
		return "—"
	return "%.1f%%" % (float(value) * 100.0)


func refresh_language() -> void:
	if section_label == null:
		return
	section_label.text = main.tr("DATA_CHECK_SECTION")
	category_tree.set_column_title(0, main.tr("DATA_CHECK_TABLE_CATEGORY"))
	category_tree.set_column_title(1, main.tr("DATA_CHECK_TABLE_COUNT"))
	category_tree.set_column_title(2, main.tr("DATA_CHECK_TABLE_SHARE"))
	refresh()


func _clear() -> void:
	summary_label.text = ""
	summary_label.hide()
	category_tree.clear()
	category_tree.hide()
	id_title_label.text = ""
	id_title_label.hide()
	id_label.text = ""
	id_label.hide()
	note_label.text = ""
	note_label.hide()
