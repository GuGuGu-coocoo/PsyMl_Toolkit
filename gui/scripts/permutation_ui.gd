extends RefCounted
## Permutation-importance configuration and result display.
##
## Kept out of main.gd so the main script does not keep growing. Builds a small
## settings block in the analysis-setup page and a summary block in the results
## page, then binds them to the existing config/result lifecycle.

const STATUS_KEYS := {
	"completed": "PERMUTATION_STATUS_COMPLETED",
	"partial": "PERMUTATION_STATUS_PARTIAL",
	"failed": "PERMUTATION_STATUS_FAILED",
	"not_run": "PERMUTATION_STATUS_NOT_RUN",
}

var main: Control
var section_label: Label
var enable_check: CheckBox
var repeats_label: Label
var repeats_spin: SpinBox
var help_label: Label
var result_heading: Label
var status_label: Label
var summary_tree: Tree
var export_button: Button
var current_validation := ""
var current_result_dir := ""
var current_entry: Dictionary = {}
var current_parsed: Dictionary = {}


func _init(owner: Control) -> void:
	main = owner


func build() -> void:
	_build_settings()
	_build_result_section()


func _build_settings() -> void:
	var parent: Node = main.parameter_editor.get_parent()
	section_label = Label.new()
	section_label.add_theme_font_size_override("font_size", 18)
	parent.add_child(section_label)
	main.translated_controls.append({"node": section_label, "key": "PERMUTATION_SECTION"})

	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 14)
	grid.add_theme_constant_override("v_separation", 8)
	parent.add_child(grid)

	enable_check = CheckBox.new()
	enable_check.button_pressed = false
	enable_check.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_child(enable_check)
	main.translated_controls.append({"node": enable_check, "key": "PERMUTATION_ENABLE"})
	var spacer := Control.new()
	grid.add_child(spacer)

	repeats_label = Label.new()
	repeats_label.custom_minimum_size.x = 120
	repeats_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	repeats_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	grid.add_child(repeats_label)
	main.translated_controls.append({"node": repeats_label, "key": "PERMUTATION_REPEATS"})
	repeats_spin = SpinBox.new()
	repeats_spin.min_value = 1
	repeats_spin.max_value = 100
	repeats_spin.step = 1
	repeats_spin.value = 10
	repeats_spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_child(repeats_spin)

	help_label = Label.new()
	help_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help_label.add_theme_color_override("font_color", Color("626977"))
	parent.add_child(help_label)
	main.translated_controls.append({"node": help_label, "key": "PERMUTATION_HELP"})

	enable_check.toggled.connect(_on_enable_toggled)
	repeats_spin.value_changed.connect(func(_value): main._refresh_review())
	_on_enable_toggled(false)


func _on_enable_toggled(pressed: bool) -> void:
	main._set_control_interactive(repeats_spin, pressed and not main.is_analysis_running)
	enable_check.tooltip_text = main.tr("PERMUTATION_ENABLE")
	main._refresh_review()


func _build_result_section() -> void:
	var parent: Node = main.predictions_tree.get_parent()
	result_heading = Label.new()
	result_heading.add_theme_font_size_override("font_size", 18)
	parent.add_child(result_heading)
	main.translated_controls.append({"node": result_heading, "key": "PERMUTATION_RESULT_SECTION"})

	status_label = Label.new()
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(status_label)
	status_label.hide()

	summary_tree = Tree.new()
	summary_tree.custom_minimum_size = Vector2(0, 170)
	summary_tree.columns = 5
	summary_tree.column_titles_visible = true
	summary_tree.hide_root = true
	parent.add_child(summary_tree)
	summary_tree.hide()

	export_button = Button.new()
	export_button.custom_minimum_size = Vector2(0, 40)
	export_button.disabled = true
	parent.add_child(export_button)
	main.translated_controls.append({"node": export_button, "key": "PERMUTATION_OPEN_FOLDER"})
	export_button.pressed.connect(_open_folder)
	_clear_result_content()


func controls() -> Array[Control]:
	return [enable_check, repeats_spin]


func enrich(config: Dictionary) -> Dictionary:
	config["permutation_importance"] = enable_check.button_pressed
	config["permutation_repeats"] = int(repeats_spin.value)
	return config


func apply_configuration(config: Dictionary) -> void:
	enable_check.button_pressed = bool(config.get("permutation_importance", false))
	repeats_spin.value = float(config.get("permutation_repeats", 10))
	clear()


func set_enabled(enabled: bool) -> void:
	main._set_control_interactive(enable_check, enabled)
	main._set_control_interactive(repeats_spin, enabled and enable_check.button_pressed)
	export_button.disabled = not enabled or current_entry.is_empty()


func clear() -> void:
	current_validation = ""
	current_result_dir = ""
	current_entry = {}
	current_parsed = {}
	_clear_result_content()


func _clear_result_content() -> void:
	if summary_tree == null:
		return
	summary_tree.clear()
	summary_tree.hide()
	if status_label != null:
		status_label.text = ""
		status_label.hide()
	if export_button != null:
		export_button.disabled = true
	if result_heading != null:
		result_heading.hide()


func load_result(parsed: Dictionary, result_dir: String) -> void:
	clear()
	var payload: Dictionary = parsed.get("permutation", {})
	if payload.is_empty() or not payload.get("enabled", false):
		return
	current_result_dir = result_dir
	var validations: Dictionary = payload.get("validations", {})
	if validations.is_empty():
		return
	var primary = parsed.get("primary_validation", null)
	if primary == null or not validations.has(primary):
		for key in validations.keys():
			primary = key
			break
	current_validation = str(primary)
	current_entry = validations.get(current_validation, {})
	current_parsed = parsed

	result_heading.show()
	status_label.show()
	export_button.disabled = current_entry.is_empty()
	_add_figure_entry(current_entry)
	_render_status(payload)
	_populate_summary()


func _add_figure_entry(entry: Dictionary) -> void:
	var artifacts: Dictionary = entry.get("artifacts", {})
	for key in artifacts:
		if not str(key).ends_with("_figure"):
			continue
		main.figure_option.add_item(main.tr("PERMUTATION_FIGURE"))
		main.figure_option.set_item_metadata(main.figure_option.item_count - 1, artifacts[key])
		main.figure_option.visible = true
		if main.figure_option.item_count == 1:
			main._show_selected_figure(0)
		return


func _render_status(_payload: Dictionary) -> void:
	var status_key: String = STATUS_KEYS.get(str(current_entry.get("status", "")), "PERMUTATION_STATUS_NOT_RUN")
	var metric: String = main._metric_display(str(current_parsed.get("selection_metric", "")))
	var scope: String = main.tr("PERMUTATION_SCOPE")
	status_label.text = main.tr("PERMUTATION_STATUS") % [
		main._validation_display(current_validation),
		main.tr(status_key),
		main.tr("PERMUTATION_AGGREGATE") % [
			int(current_entry.get("n_folds_successful", 0)),
			int(current_entry.get("n_folds_planned", 0)),
		],
		metric,
		scope,
	]


func _populate_summary() -> void:
	var artifacts: Dictionary = current_entry.get("artifacts", {})
	var summary_rel := ""
	for key in artifacts:
		if str(key).ends_with("_summary"):
			summary_rel = artifacts[key]
			break
	if summary_rel.is_empty():
		summary_tree.hide()
		return
	var file := FileAccess.open(current_result_dir.path_join(summary_rel), FileAccess.READ)
	if file == null:
		summary_tree.hide()
		return
	var headers := file.get_csv_line()
	var wanted := ["variable", "fold_mean_equal_weight", "between_fold_std", "n_folds_successful", "status"]
	var indices: Array[int] = []
	for name in wanted:
		indices.append(headers.find(name))
	summary_tree.clear()
	summary_tree.columns = wanted.size()
	summary_tree.column_titles_visible = true
	for index in range(wanted.size()):
		summary_tree.set_column_title(index, main._column_display(wanted[index]))
		summary_tree.set_column_custom_minimum_width(index, 150 if index == 0 else 130)
		summary_tree.set_column_expand(index, index == 0)
	var root := summary_tree.create_item()
	while not file.eof_reached():
		var values := file.get_csv_line()
		if values.size() == 1 and values[0].is_empty():
			continue
		if values.size() < headers.size():
			continue
		var item := summary_tree.create_item(root)
		for column in range(indices.size()):
			var source: int = indices[column]
			var value := str(values[source]) if source >= 0 else ""
			if wanted[column] == "status":
				value = _status_display(value)
			elif wanted[column] == "fold_mean_equal_weight" or wanted[column] == "between_fold_std":
				value = _number_display(value)
			item.set_text(column, value)
			# Long variable names are ellipsized in the column; expose the full
			# text as a tooltip so two similar names stay distinguishable.
			if wanted[column] == "variable":
				item.set_tooltip_text(column, value)
	summary_tree.show()


func _number_display(value: String) -> String:
	if value.strip_edges().is_empty() or value == "nan":
		return "—"
	if value.is_valid_float():
		return "%.4f" % value.to_float()
	return value


func _status_display(value: String) -> String:
	var key: String = STATUS_KEYS.get(value, "")
	return main.tr(key) if not key.is_empty() else value


func _open_folder() -> void:
	var target := current_result_dir
	var artifacts: Dictionary = current_entry.get("artifacts", {})
	for key in artifacts:
		if str(key).ends_with("_metadata"):
			target = current_result_dir.path_join(str(artifacts[key]).get_base_dir())
			break
	if not target.is_empty() and DirAccess.dir_exists_absolute(target):
		OS.shell_open(target)


func refresh_language() -> void:
	if result_heading == null:
		return
	result_heading.text = main.tr("PERMUTATION_RESULT_SECTION")
	export_button.text = main.tr("PERMUTATION_OPEN_FOLDER")
	section_label.text = main.tr("PERMUTATION_SECTION")
	enable_check.text = main.tr("PERMUTATION_ENABLE")
	repeats_label.text = main.tr("PERMUTATION_REPEATS")
	help_label.text = main.tr("PERMUTATION_HELP")
	if not current_validation.is_empty():
		_render_status(current_parsed.get("permutation", {}))
		_populate_summary()
