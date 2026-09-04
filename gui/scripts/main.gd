extends Control

const ACCENT := Color("5f7cf7")
const SURFACE := Color("f6f7fb")
const TEXT := Color("172033")

var bridge: CoreBridge
var capabilities: Dictionary = {}
var preview_payload: Dictionary = {}
var translated_controls: Array[Dictionary] = []
var localized_value_options: Array[OptionButton] = []
var tabs: TabContainer
var language_label: Label
var language_option: OptionButton
var data_path_edit: LineEdit
var data_summary_label: Label
var variable_tree: Tree
var sample_tree: Tree
var feature_list: ItemList
var task_option: OptionButton
var target_option: OptionButton
var group_option: OptionButton
var missing_option: OptionButton
var scaling_option: OptionButton
var validation_list: ItemList
var folds_spin: SpinBox
var model_list: ItemList
var tuning_option: OptionButton
var selection_metric_option: OptionButton
var inner_folds_spin: SpinBox
var max_candidates_spin: SpinBox
var parameter_editor: VBoxContainer
var parameter_controls: Dictionary = {}
var saved_parameter_values: Dictionary = {}
var output_edit: LineEdit
var review_text: TextEdit
var status_label: Label
var progress_detail_label: Label
var progress_bar: ProgressBar
var run_button: Button
var cancel_button: Button
var warnings_text: RichTextLabel
var best_result_label: Label
var comparison_tree: Tree
var metrics_tree: Tree
var predictions_tree: Tree
var figure_view: TextureRect
var no_results_label: Label
var file_dialog: FileDialog
var folder_dialog: FileDialog
var last_result_dir := ""
var status_key := "READY"
var status_detail := ""
var last_warnings: Array = []
var pending_config_path := ""


func _ready() -> void:
	PsyMLI18n.install()
	TranslationServer.set_locale("zh_CN")
	_build_theme()
	_build_interface()
	bridge = CoreBridge.new()
	add_child(bridge)
	bridge.preview_ready.connect(_on_preview_ready)
	bridge.preview_failed.connect(_on_preview_failed)
	bridge.event_received.connect(_on_core_event)
	capabilities = bridge.execute_json_sync(PackedStringArray(["capabilities"]))
	if capabilities.has("error"):
		_show_error(capabilities["error"].get("message", "PsyML Core unavailable"))
	else:
		_populate_models()
	_apply_language()


func _build_theme() -> void:
	var app_theme := Theme.new()
	app_theme.default_font_size = 17
	for control_type in ["Label", "Button", "OptionButton", "LineEdit", "TextEdit", "Tree", "ItemList"]:
		app_theme.set_color("font_color", control_type, TEXT)
	app_theme.set_color("font_hover_color", "Button", TEXT)
	app_theme.set_color("font_pressed_color", "Button", TEXT)
	app_theme.set_color("font_selected_color", "TabBar", TEXT)
	app_theme.set_color("font_unselected_color", "TabBar", Color("59657a"))
	app_theme.set_color("font_selected_color", "ItemList", Color.WHITE)
	app_theme.set_color("font_readonly_color", "TextEdit", TEXT)
	app_theme.set_stylebox("panel", "TabContainer", _style_box(Color.WHITE, 8))
	app_theme.set_stylebox("panel", "Tree", _style_box(Color("fbfcff"), 5, Color("d9deea")))
	app_theme.set_stylebox("panel", "ItemList", _style_box(Color("fbfcff"), 5, Color("d9deea")))
	app_theme.set_stylebox("selected", "ItemList", _style_box(ACCENT, 4))
	app_theme.set_stylebox("selected_focus", "ItemList", _style_box(ACCENT, 4))
	app_theme.set_stylebox("normal", "LineEdit", _style_box(Color.WHITE, 5, Color("cbd2e1")))
	app_theme.set_stylebox("normal", "TextEdit", _style_box(Color.WHITE, 5, Color("cbd2e1")))
	app_theme.set_stylebox("read_only", "TextEdit", _style_box(Color("fbfcff"), 5, Color("cbd2e1")))
	app_theme.set_stylebox("normal", "Button", _style_box(Color("eef1f8"), 5))
	app_theme.set_stylebox("hover", "Button", _style_box(Color("e1e7fb"), 5))
	app_theme.set_stylebox("pressed", "Button", _style_box(Color("d2dcfb"), 5))
	app_theme.set_stylebox("tab_selected", "TabBar", _style_box(Color.WHITE, 5))
	app_theme.set_stylebox("tab_unselected", "TabBar", _style_box(Color("e3e7ef"), 5))
	app_theme.set_type_variation("AccentButton", "Button")
	app_theme.set_stylebox("normal", "AccentButton", _style_box(ACCENT, 5))
	app_theme.set_stylebox("hover", "AccentButton", _style_box(Color("4d6bea"), 5))
	app_theme.set_color("font_color", "AccentButton", Color.WHITE)
	app_theme.set_color("font_hover_color", "AccentButton", Color.WHITE)
	theme = app_theme


func _style_box(color: Color, radius: int, border := Color.TRANSPARENT) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	style.border_color = border
	if border != Color.TRANSPARENT:
		style.set_border_width_all(1)
	style.content_margin_left = 10
	style.content_margin_right = 10
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	return style


func _build_interface() -> void:
	var background := ColorRect.new()
	background.color = SURFACE
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 30)
	margin.add_theme_constant_override("margin_right", 30)
	margin.add_theme_constant_override("margin_top", 22)
	margin.add_theme_constant_override("margin_bottom", 24)
	add_child(margin)
	var page := VBoxContainer.new()
	page.add_theme_constant_override("separation", 16)
	margin.add_child(page)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 18)
	page.add_child(header)
	var brand := VBoxContainer.new()
	brand.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(brand)
	var title := Label.new()
	title.name = "TitleLabel"
	title.text = "PsyML Toolkit"
	title.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	title.add_theme_font_size_override("font_size", 30)
	title.add_theme_color_override("font_color", ACCENT)
	brand.add_child(title)
	language_label = _translated_label("LANGUAGE")
	header.add_child(language_label)
	language_option = OptionButton.new()
	language_option.name = "LanguageOption"
	for item in ["中文", "English", "Français"]:
		language_option.add_item(item)
	language_option.selected = 0
	language_option.item_selected.connect(_on_language_selected)
	header.add_child(language_option)

	tabs = TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	page.add_child(tabs)
	_build_data_tab()
	_build_config_tab()
	_build_review_tab()
	_build_results_tab()
	_build_dialogs()


func _tab_page(name_value: String) -> VBoxContainer:
	var scroll := ScrollContainer.new()
	scroll.name = name_value
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(scroll)
	var padding := MarginContainer.new()
	padding.add_theme_constant_override("margin_left", 16)
	padding.add_theme_constant_override("margin_right", 16)
	padding.add_theme_constant_override("margin_top", 18)
	padding.add_theme_constant_override("margin_bottom", 18)
	padding.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(padding)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	padding.add_child(content)
	return content


func _heading(key: String) -> Label:
	var label := _translated_label(key)
	label.add_theme_font_size_override("font_size", 23)
	label.add_theme_color_override("font_color", TEXT)
	return label


func _translated_label(key: String) -> Label:
	var label := Label.new()
	translated_controls.append({"node": label, "key": key})
	return label


func _translated_button(key: String) -> Button:
	var button := Button.new()
	button.custom_minimum_size.y = 42
	translated_controls.append({"node": button, "key": key})
	return button


func _build_data_tab() -> void:
	var content := _tab_page("Data")
	content.add_child(_heading("DATA_HEADING"))
	var path_row := HBoxContainer.new()
	path_row.add_theme_constant_override("separation", 10)
	content.add_child(path_row)
	path_row.add_child(_translated_label("DATA_PATH"))
	data_path_edit = LineEdit.new()
	data_path_edit.name = "DataPathEdit"
	data_path_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	data_path_edit.placeholder_text = "CSV · TSV · XLSX · XLS · SAV · DTA · SAS7BDAT · XPT · Parquet"
	path_row.add_child(data_path_edit)
	var browse := _translated_button("BROWSE")
	browse.pressed.connect(func(): file_dialog.popup_centered_ratio(0.8))
	path_row.add_child(browse)
	var preview := _translated_button("PREVIEW")
	preview.pressed.connect(_request_preview)
	path_row.add_child(preview)
	data_summary_label = _translated_label("NO_DATA")
	data_summary_label.name = "DataSummaryLabel"
	content.add_child(data_summary_label)

	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 18)
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(columns)
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(left)
	left.add_child(_translated_label("VARIABLES"))
	variable_tree = Tree.new()
	variable_tree.custom_minimum_size = Vector2(500, 210)
	variable_tree.columns = 3
	variable_tree.column_titles_visible = true
	left.add_child(variable_tree)
	left.add_child(_translated_label("SAMPLE"))
	sample_tree = Tree.new()
	sample_tree.custom_minimum_size = Vector2(500, 180)
	left.add_child(sample_tree)
	var right := VBoxContainer.new()
	right.custom_minimum_size.x = 330
	columns.add_child(right)
	right.add_child(_translated_label("FEATURES"))
	feature_list = ItemList.new()
	feature_list.name = "FeatureList"
	feature_list.select_mode = ItemList.SELECT_MULTI
	feature_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	feature_list.custom_minimum_size.y = 400
	feature_list.item_selected.connect(func(_index): _refresh_review())
	right.add_child(feature_list)


func _build_config_tab() -> void:
	var content := _tab_page("Configure")
	content.add_child(_heading("CONFIG_HEADING"))
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 24)
	grid.add_theme_constant_override("v_separation", 14)
	content.add_child(grid)
	task_option = OptionButton.new()
	_add_field(grid, "TASK", task_option)
	target_option = OptionButton.new()
	_add_field(grid, "TARGET", target_option)
	group_option = OptionButton.new()
	_add_field(grid, "GROUP", group_option)
	missing_option = _value_option(["drop", "mean", "median", "mode"])
	missing_option.select(2)
	_add_field(grid, "MISSING", missing_option)
	scaling_option = _value_option(["none", "standard", "minmax"])
	scaling_option.select(1)
	_add_field(grid, "SCALING", scaling_option)
	validation_list = ItemList.new()
	validation_list.select_mode = ItemList.SELECT_MULTI
	validation_list.custom_minimum_size.y = 125
	_add_field(grid, "VALIDATION", validation_list)
	folds_spin = SpinBox.new()
	folds_spin.min_value = 2
	folds_spin.max_value = 20
	folds_spin.value = 5
	_add_field(grid, "FOLDS", folds_spin)
	model_list = ItemList.new()
	model_list.select_mode = ItemList.SELECT_MULTI
	model_list.custom_minimum_size.y = 145
	_add_field(grid, "MODEL", model_list)
	tuning_option = _value_option(["tuning_none", "tuning_quick", "tuning_custom"])
	_add_field(grid, "TUNING", tuning_option)
	selection_metric_option = OptionButton.new()
	_add_field(grid, "SELECTION_METRIC", selection_metric_option)
	inner_folds_spin = SpinBox.new()
	inner_folds_spin.min_value = 2
	inner_folds_spin.max_value = 10
	inner_folds_spin.value = 3
	_add_field(grid, "INNER_FOLDS", inner_folds_spin)
	max_candidates_spin = SpinBox.new()
	max_candidates_spin.min_value = 1
	max_candidates_spin.max_value = 200
	max_candidates_spin.value = 20
	_add_field(grid, "MAX_CANDIDATES", max_candidates_spin)
	content.add_child(_translated_label("PARAMETER_HELP"))
	parameter_editor = VBoxContainer.new()
	parameter_editor.add_theme_constant_override("separation", 10)
	content.add_child(parameter_editor)
	_populate_task_options()
	task_option.item_selected.connect(func(_index): _on_task_changed())
	target_option.item_selected.connect(func(_index): _on_column_role_changed())
	group_option.item_selected.connect(func(_index): _on_column_role_changed())
	for control in [missing_option, scaling_option, tuning_option, selection_metric_option]:
		control.item_selected.connect(func(_index): _refresh_review())
	tuning_option.item_selected.connect(func(_index): _populate_parameter_editor())
	model_list.multi_selected.connect(func(_index, _selected): _populate_parameter_editor())
	validation_list.multi_selected.connect(func(_index, _selected): _refresh_review())
	folds_spin.value_changed.connect(func(_value): _refresh_review())
	inner_folds_spin.value_changed.connect(func(_value): _refresh_review())
	max_candidates_spin.value_changed.connect(func(_value): _refresh_review())


func _add_field(grid: GridContainer, key: String, control: Control) -> void:
	grid.add_child(_translated_label(key))
	control.custom_minimum_size = Vector2(
		maxf(control.custom_minimum_size.x, 420.0),
		maxf(control.custom_minimum_size.y, 42.0)
	)
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_child(control)


func _value_option(values: Array) -> OptionButton:
	var option := OptionButton.new()
	for value in values:
		option.add_item(tr("OPTION_" + str(value).to_upper()))
		option.set_item_metadata(option.item_count - 1, value)
	localized_value_options.append(option)
	return option


func _populate_task_options() -> void:
	var previous = task_option.get_item_metadata(task_option.selected) if task_option.item_count else null
	task_option.clear()
	for task in ["classification", "regression"]:
		task_option.add_item(tr(task.to_upper()))
		task_option.set_item_metadata(task_option.item_count - 1, task)
		if task == previous:
			task_option.select(task_option.item_count - 1)


func _build_review_tab() -> void:
	var content := _tab_page("Review")
	content.add_child(_heading("REVIEW_HEADING"))
	var output_row := HBoxContainer.new()
	content.add_child(output_row)
	output_row.add_child(_translated_label("OUTPUT_FOLDER"))
	output_edit = LineEdit.new()
	output_edit.name = "OutputEdit"
	output_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	output_edit.text = OS.get_system_dir(OS.SYSTEM_DIR_DOCUMENTS).path_join("PsyML Results")
	output_row.add_child(output_edit)
	var choose := _translated_button("CHOOSE_FOLDER")
	choose.pressed.connect(func(): folder_dialog.popup_centered_ratio(0.75))
	output_row.add_child(choose)
	var refresh := _translated_button("REFRESH_REVIEW")
	refresh.pressed.connect(_refresh_review)
	output_row.add_child(refresh)
	review_text = TextEdit.new()
	review_text.name = "ReviewText"
	review_text.editable = false
	review_text.custom_minimum_size.y = 390
	review_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(review_text)
	progress_detail_label = Label.new()
	progress_detail_label.text = tr("PROGRESS_WAITING")
	progress_detail_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	content.add_child(progress_detail_label)
	var run_row := HBoxContainer.new()
	run_row.alignment = BoxContainer.ALIGNMENT_END
	content.add_child(run_row)
	status_label = _translated_label("READY")
	status_label.name = "StatusLabel"
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	run_row.add_child(status_label)
	progress_bar = ProgressBar.new()
	progress_bar.custom_minimum_size.x = 180
	progress_bar.max_value = 1.0
	progress_bar.show_percentage = false
	run_row.add_child(progress_bar)
	cancel_button = _translated_button("CANCEL")
	cancel_button.disabled = true
	cancel_button.pressed.connect(_request_cancel)
	run_row.add_child(cancel_button)
	run_button = _translated_button("RUN")
	run_button.name = "RunButton"
	run_button.theme_type_variation = "AccentButton"
	run_button.pressed.connect(_on_run_pressed)
	run_row.add_child(run_button)


func _build_results_tab() -> void:
	var content := _tab_page("Results")
	content.add_child(_heading("RESULTS_HEADING"))
	no_results_label = _translated_label("NO_RESULTS")
	content.add_child(no_results_label)
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 18)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(body)
	var details := VBoxContainer.new()
	details.custom_minimum_size.x = 520
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(details)
	best_result_label = Label.new()
	best_result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.add_child(best_result_label)
	details.add_child(_translated_label("COMPARISONS"))
	comparison_tree = Tree.new()
	comparison_tree.custom_minimum_size.y = 170
	details.add_child(comparison_tree)
	details.add_child(_translated_label("WARNINGS"))
	warnings_text = RichTextLabel.new()
	warnings_text.fit_content = true
	warnings_text.custom_minimum_size.y = 70
	details.add_child(warnings_text)
	details.add_child(_translated_label("METRICS"))
	metrics_tree = Tree.new()
	metrics_tree.columns = 2
	metrics_tree.column_titles_visible = true
	metrics_tree.custom_minimum_size.y = 180
	details.add_child(metrics_tree)
	details.add_child(_translated_label("PREDICTIONS"))
	predictions_tree = Tree.new()
	predictions_tree.custom_minimum_size.y = 190
	details.add_child(predictions_tree)
	var visual := VBoxContainer.new()
	visual.custom_minimum_size.x = 500
	visual.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(visual)
	figure_view = TextureRect.new()
	figure_view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	figure_view.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	figure_view.custom_minimum_size = Vector2(480, 430)
	figure_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	visual.add_child(figure_view)
	var open_button := _translated_button("OPEN_RESULTS")
	open_button.pressed.connect(_open_results)
	visual.add_child(open_button)


func _build_dialogs() -> void:
	file_dialog = FileDialog.new()
	file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	file_dialog.access = FileDialog.ACCESS_FILESYSTEM
	file_dialog.use_native_dialog = true
	file_dialog.filters = PackedStringArray(
		["*.csv,*.tsv,*.xlsx,*.xls,*.sav,*.dta,*.sas7bdat,*.xpt,*.parquet ; Research data"]
	)
	file_dialog.file_selected.connect(_on_file_selected)
	add_child(file_dialog)
	folder_dialog = FileDialog.new()
	folder_dialog.file_mode = FileDialog.FILE_MODE_OPEN_DIR
	folder_dialog.access = FileDialog.ACCESS_FILESYSTEM
	folder_dialog.use_native_dialog = true
	folder_dialog.dir_selected.connect(func(path): output_edit.text = path; _refresh_review())
	add_child(folder_dialog)


func _on_language_selected(index: int) -> void:
	language_option.select(index)
	TranslationServer.set_locale(PsyMLI18n.LOCALES[index])
	_apply_language()


func _apply_language() -> void:
	for item in translated_controls:
		var node: Control = item["node"]
		var text_value := tr(item["key"])
		if node is Label:
			node.text = text_value
		elif node is Button:
			node.text = text_value
	_populate_task_options()
	for option in localized_value_options:
		for index in range(option.item_count):
			option.set_item_text(
				index, tr("OPTION_" + str(option.get_item_metadata(index)).to_upper())
			)
	for index in range(validation_list.item_count):
		validation_list.set_item_text(
			index, tr("OPTION_" + str(validation_list.get_item_metadata(index)).to_upper())
		)
	for index in range(selection_metric_option.item_count):
		selection_metric_option.set_item_text(
			index, tr("METRIC_" + str(selection_metric_option.get_item_metadata(index)).to_upper())
		)
	tabs.set_tab_title(0, tr("TAB_DATA"))
	tabs.set_tab_title(1, tr("TAB_CONFIGURE"))
	tabs.set_tab_title(2, tr("TAB_REVIEW"))
	tabs.set_tab_title(3, tr("TAB_RESULTS"))
	_update_tree_titles()
	if preview_payload.is_empty():
		data_summary_label.text = tr("NO_DATA")
	else:
		data_summary_label.text = tr("DATA_SUMMARY") % [preview_payload.row_count, preview_payload.column_count]
	if group_option != null and group_option.item_count > 0:
		group_option.set_item_text(0, tr("NONE"))
	if status_label != null:
		if status_key == "ERROR":
			status_label.text = tr("ERROR") % status_detail
		else:
			status_label.text = tr(status_key)
	_populate_parameter_editor()
	_render_warnings()
	_refresh_review()


func _update_tree_titles() -> void:
	variable_tree.set_column_title(0, tr("COLUMN"))
	variable_tree.set_column_title(1, tr("TYPE"))
	variable_tree.set_column_title(2, tr("MISSING_COUNT"))
	metrics_tree.set_column_title(0, tr("METRICS"))
	metrics_tree.set_column_title(1, tr("VALUE"))


func _on_file_selected(path: String) -> void:
	data_path_edit.text = path
	_request_preview()


func _request_preview() -> void:
	if data_path_edit.text.strip_edges().is_empty():
		_show_error(tr("SELECT_DATA"))
		return
	data_summary_label.text = tr("PREVIEW_LOADING")
	bridge.request_preview(data_path_edit.text, true)


func _on_preview_ready(payload: Dictionary) -> void:
	preview_payload = payload
	data_summary_label.text = tr("DATA_SUMMARY") % [payload.row_count, payload.column_count]
	_set_status("PREVIEW_READY")
	variable_tree.clear()
	var root := variable_tree.create_item()
	feature_list.clear()
	target_option.clear()
	group_option.clear()
	group_option.add_item(tr("NONE"))
	group_option.set_item_metadata(0, null)
	for column in payload.columns:
		var row := variable_tree.create_item(root)
		row.set_text(0, column.name)
		row.set_text(1, column.dtype)
		row.set_text(2, str(column.missing_count))
		feature_list.add_item(column.name)
		feature_list.set_item_metadata(feature_list.item_count - 1, column.name)
		feature_list.select(feature_list.item_count - 1, false)
		target_option.add_item(column.name)
		target_option.set_item_metadata(target_option.item_count - 1, column.name)
		group_option.add_item(column.name)
		group_option.set_item_metadata(group_option.item_count - 1, column.name)
	_populate_sample(payload.get("sample", []))
	_on_column_role_changed()
	tabs.current_tab = 1


func _populate_sample(rows: Array) -> void:
	sample_tree.clear()
	if rows.is_empty():
		return
	var headers: Array = rows[0].keys()
	sample_tree.columns = headers.size()
	sample_tree.column_titles_visible = true
	for index in range(headers.size()):
		sample_tree.set_column_title(index, str(headers[index]))
	var root := sample_tree.create_item()
	for values in rows:
		var item := sample_tree.create_item(root)
		for index in range(headers.size()):
			item.set_text(index, str(values.get(headers[index], "")))


func _on_preview_failed(error: Dictionary) -> void:
	_show_core_error(error)


func _on_task_changed() -> void:
	_populate_models()
	_populate_parameter_editor()
	_refresh_review()


func _populate_models() -> void:
	if capabilities.is_empty() or capabilities.has("error") or model_list == null:
		return
	model_list.clear()
	var task: String = task_option.get_item_metadata(task_option.selected)
	for model in capabilities.models[task]:
		model_list.add_item(str(model).replace("_", " ").capitalize())
		model_list.set_item_metadata(model_list.item_count - 1, model)
	if model_list.item_count > 0:
		model_list.select(0, false)
	validation_list.clear()
	var validations: Array = ["holdout", "k_fold"]
	if task == "classification":
		validations.append("stratified_k_fold")
	validations.append("group_k_fold")
	if task == "classification":
		validations.append("stratified_group_k_fold")
	validations.append("leave_one_group_out")
	for validation in validations:
		validation_list.add_item(tr("OPTION_" + str(validation).to_upper()))
		validation_list.set_item_metadata(validation_list.item_count - 1, validation)
	var preferred := "stratified_k_fold" if task == "classification" else "k_fold"
	for index in range(validation_list.item_count):
		if validation_list.get_item_metadata(index) == preferred:
			validation_list.select(index, false)
	selection_metric_option.clear()
	for metric in capabilities.selection_metrics[task]:
		selection_metric_option.add_item(tr("METRIC_" + str(metric).to_upper()))
		selection_metric_option.set_item_metadata(selection_metric_option.item_count - 1, metric)
	selection_metric_option.select(0)
	_update_validation_availability()


func _capture_parameter_values() -> void:
	for key in parameter_controls:
		var controls: Dictionary = parameter_controls[key]
		saved_parameter_values[key] = {
			"enabled": controls.enabled.button_pressed,
			"values": controls.values.text,
		}


func _populate_parameter_editor() -> void:
	if parameter_editor == null or capabilities.is_empty() or capabilities.has("error"):
		return
	_capture_parameter_values()
	for child in parameter_editor.get_children():
		parameter_editor.remove_child(child)
		child.queue_free()
	parameter_controls.clear()
	var tuning_mode: String = tuning_option.get_item_metadata(tuning_option.selected)
	if tuning_mode == "tuning_none":
		var no_search := Label.new()
		no_search.text = tr("NO_PARAMETER_SEARCH")
		parameter_editor.add_child(no_search)
		return
	var task: String = task_option.get_item_metadata(task_option.selected)
	for model_name in _selected_models():
		var heading := Label.new()
		heading.text = str(model_name).replace("_", " ").capitalize()
		heading.add_theme_font_size_override("font_size", 19)
		parameter_editor.add_child(heading)
		var parameter_grid := GridContainer.new()
		parameter_grid.columns = 2
		parameter_grid.add_theme_constant_override("h_separation", 14)
		parameter_grid.add_theme_constant_override("v_separation", 8)
		parameter_editor.add_child(parameter_grid)
		var model_grid: Dictionary = capabilities.parameter_grids[task].get(model_name, {})
		if model_grid.is_empty():
			var empty_label := Label.new()
			empty_label.text = tr("NO_TUNABLE_PARAMETERS")
			parameter_grid.add_child(empty_label)
			continue
		for parameter in model_grid:
			var enabled := CheckBox.new()
			enabled.text = str(parameter)
			enabled.button_pressed = true
			enabled.disabled = tuning_mode == "tuning_quick"
			parameter_grid.add_child(enabled)
			var values := LineEdit.new()
			values.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			values.text = JSON.stringify(model_grid[parameter])
			values.editable = tuning_mode == "tuning_custom"
			var key := "%s::%s" % [model_name, parameter]
			if tuning_mode == "tuning_custom" and saved_parameter_values.has(key):
				enabled.button_pressed = saved_parameter_values[key].enabled
				values.text = saved_parameter_values[key].values
			values.text_changed.connect(func(_text): _refresh_review())
			enabled.toggled.connect(func(_pressed): _refresh_review())
			parameter_grid.add_child(values)
			parameter_controls[key] = {"enabled": enabled, "values": values}
	_refresh_review()


func _selected_values(list_control: ItemList) -> Array[String]:
	var values: Array[String] = []
	for index in list_control.get_selected_items():
		values.append(list_control.get_item_metadata(index))
	return values


func _selected_models() -> Array[String]:
	return _selected_values(model_list)


func _selected_validations() -> Array[String]:
	return _selected_values(validation_list)


func _update_validation_availability() -> void:
	if validation_list == null:
		return
	var has_group := (
		group_option != null
		and group_option.item_count > 0
		and group_option.get_item_metadata(group_option.selected) != null
	)
	for index in range(validation_list.item_count):
		var strategy: String = validation_list.get_item_metadata(index)
		var unavailable := (
			strategy in ["group_k_fold", "stratified_group_k_fold", "leave_one_group_out"]
			and not has_group
		)
		validation_list.set_item_disabled(index, unavailable)
		if unavailable:
			validation_list.deselect(index)
	if validation_list.get_selected_items().is_empty():
		for index in range(validation_list.item_count):
			if not validation_list.is_item_disabled(index):
				validation_list.select(index, false)
				break


func _on_column_role_changed() -> void:
	if target_option.item_count == 0:
		return
	var target = target_option.get_item_metadata(target_option.selected)
	var group = group_option.get_item_metadata(group_option.selected)
	for index in range(feature_list.item_count):
		var column = feature_list.get_item_metadata(index)
		feature_list.set_item_disabled(index, column == target or column == group)
		if column == target or column == group:
			feature_list.deselect(index)
	_update_validation_availability()
	_refresh_review()


func _selected_features() -> Array[String]:
	var result: Array[String] = []
	for index in feature_list.get_selected_items():
		result.append(feature_list.get_item_metadata(index))
	return result


func _parameter_grid_payload() -> Dictionary:
	var tuning_mode: String = tuning_option.get_item_metadata(tuning_option.selected)
	if tuning_mode != "tuning_custom":
		return {"grids": {}}
	var grids: Dictionary = {}
	for key in parameter_controls:
		var controls: Dictionary = parameter_controls[key]
		if not controls.enabled.button_pressed:
			continue
		var parsed = JSON.parse_string(controls.values.text)
		if not parsed is Array or parsed.is_empty():
			return {"error": tr("INVALID_PARAMETER_VALUES") % key}
		var parts := str(key).split("::", false, 1)
		if not grids.has(parts[0]):
			grids[parts[0]] = {}
		grids[parts[0]][parts[1]] = parsed
	return {"grids": grids}


func _build_config() -> Dictionary:
	if preview_payload.is_empty():
		return {"error": tr("SELECT_DATA")}
	if target_option.item_count == 0:
		return {"error": tr("SELECT_TARGET")}
	var features := _selected_features()
	if features.is_empty():
		return {"error": tr("SELECT_FEATURE")}
	var models := _selected_models()
	if models.is_empty():
		return {"error": tr("SELECT_MODEL")}
	var validations := _selected_validations()
	if validations.is_empty():
		return {"error": tr("SELECT_VALIDATION")}
	var grid_payload := _parameter_grid_payload()
	if grid_payload.has("error"):
		return grid_payload
	var tuning_mode: String = tuning_option.get_item_metadata(tuning_option.selected)
	return {
		"schema_version": "1.0",
		"task": task_option.get_item_metadata(task_option.selected),
		"target_column": target_option.get_item_metadata(target_option.selected),
		"model_name": models[0],
		"model_names": models,
		"input_path": data_path_edit.text,
		"output_dir": output_edit.text,
		"group_column": group_option.get_item_metadata(group_option.selected),
		"feature_columns": features,
		"test_size": 0.2,
		"random_seed": 42,
		"validation_strategy": validations[0],
		"validation_strategies": validations,
		"n_splits": int(folds_spin.value),
		"missing_strategy": missing_option.get_item_metadata(missing_option.selected),
		"scaling": scaling_option.get_item_metadata(scaling_option.selected),
		"include_data_hash": true,
		"model_params": {},
		"tuning_mode": tuning_mode.trim_prefix("tuning_"),
		"parameter_grids": grid_payload.grids,
		"selection_metric": selection_metric_option.get_item_metadata(
			selection_metric_option.selected
		),
		"inner_splits": int(inner_folds_spin.value),
		"max_candidates": int(max_candidates_spin.value),
	}


func _refresh_review() -> void:
	if review_text == null:
		return
	var config := _build_config()
	if config.has("error"):
		review_text.text = config.error
	else:
		review_text.text = JSON.stringify(config, "  ")


func _on_run_pressed() -> void:
	var config := _build_config()
	if config.has("error"):
		_show_error(config.error)
		return
	pending_config_path = OS.get_temp_dir().path_join(
		"psyml_pending_%d.json" % Time.get_ticks_usec()
	)
	var config_file := FileAccess.open(pending_config_path, FileAccess.WRITE)
	if config_file == null:
		pending_config_path = ""
		_show_error("Could not write local analysis configuration")
		return
	config_file.store_string(JSON.stringify(config, "  "))
	config_file.close()
	_set_status("RUNNING")
	progress_detail_label.text = tr("PROGRESS_STARTING")
	progress_bar.value = 0.0
	run_button.disabled = true
	cancel_button.disabled = false
	if not bridge.start_analysis(pending_config_path):
		run_button.disabled = false
		cancel_button.disabled = true
		_cleanup_pending_config()
		_show_error("PsyML Core is already running")


func _request_cancel() -> void:
	if not bridge.is_running():
		return
	_set_status("CANCELLING")
	cancel_button.disabled = true
	progress_detail_label.text = tr("PROGRESS_CANCELLING")
	bridge.cancel_analysis()


func _on_core_event(event: Dictionary) -> void:
	progress_bar.value = float(event.get("progress", 0.0))
	match event.get("event", ""):
		"started":
			_set_status("RUNNING")
		"progress":
			_set_status("RUNNING")
			var completed := int(event.get("completed_tasks", 0))
			var total := int(event.get("total_tasks", 0))
			var remaining := int(event.get("remaining_tasks", 0))
			var eta_value = event.get("estimated_remaining_seconds", null)
			var eta := tr("ESTIMATING") if eta_value == null else _format_duration(float(eta_value))
			var model := str(event.get("current_model", ""))
			var validation := str(event.get("current_validation", ""))
			var current_fold := int(event.get("current_fold", 1))
			if completed == 0:
				progress_detail_label.text = tr("PROGRESS_PLANNED") % total
			else:
				progress_detail_label.text = tr("PROGRESS_DETAIL") % [
					completed,
					total,
					remaining,
					eta,
					_model_display(model),
					_validation_display(validation),
					current_fold,
				]
		"completed":
			_cleanup_pending_config()
			_set_status("COMPLETED")
			run_button.disabled = false
			cancel_button.disabled = true
			progress_detail_label.text = tr("PROGRESS_COMPLETED")
			_load_results(event.result_path)
		"cancelled":
			_cleanup_pending_config()
			_set_status("CANCELLED")
			run_button.disabled = false
			cancel_button.disabled = true
			progress_detail_label.text = tr("PROGRESS_CANCELLED")
		"failed":
			_cleanup_pending_config()
			run_button.disabled = false
			cancel_button.disabled = true
			_show_core_error(event.get("error", {}))


func _format_duration(seconds: float) -> String:
	var rounded := maxi(int(round(seconds)), 0)
	if rounded < 60:
		return tr("SECONDS") % rounded
	var minutes := rounded / 60
	if minutes < 60:
		return tr("MINUTES") % minutes
	var hours := minutes / 60
	var leftover := minutes % 60
	return tr("HOURS_MINUTES") % [hours, leftover]


func _cleanup_pending_config() -> void:
	if pending_config_path.is_empty():
		return
	if FileAccess.file_exists(pending_config_path):
		DirAccess.remove_absolute(pending_config_path)
	pending_config_path = ""


func _load_results(result_path: String) -> void:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(result_path))
	if not parsed is Dictionary:
		_show_error("Invalid result.json")
		return
	last_result_dir = result_path.get_base_dir()
	no_results_label.visible = false
	last_warnings = parsed.get("warnings", [])
	best_result_label.text = tr("BEST_RESULT") % [
		_model_display(str(parsed.get("best_model", ""))),
		_validation_display(str(parsed.get("best_validation", ""))),
		_metric_display(str(parsed.get("selection_metric", ""))),
	]
	_render_warnings()
	metrics_tree.clear()
	var root := metrics_tree.create_item()
	for metric in parsed.metrics:
		var item := metrics_tree.create_item(root)
		item.set_text(0, metric)
		item.set_text(1, "%.6f" % parsed.metrics[metric])
	var artifacts: Dictionary = parsed.artifacts
	_load_csv_preview(last_result_dir.path_join(artifacts.model_comparison), comparison_tree, 30)
	_load_predictions(last_result_dir.path_join(artifacts.predictions))
	var image := Image.load_from_file(last_result_dir.path_join(artifacts.figure))
	if image != null and not image.is_empty():
		figure_view.texture = ImageTexture.create_from_image(image)
	tabs.current_tab = 3


func _load_predictions(path: String) -> void:
	_load_csv_preview(path, predictions_tree, 20)


func _load_csv_preview(path: String, tree: Tree, maximum_rows: int) -> void:
	tree.clear()
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return
	var headers := file.get_csv_line()
	tree.columns = headers.size()
	tree.column_titles_visible = true
	for index in range(headers.size()):
		tree.set_column_title(index, headers[index])
	var root := tree.create_item()
	var shown := 0
	while not file.eof_reached() and shown < maximum_rows:
		var values := file.get_csv_line()
		if values.size() == 1 and values[0].is_empty():
			continue
		var item := tree.create_item(root)
		for index in range(min(headers.size(), values.size())):
			var value := str(values[index])
			if headers[index] == "model":
				value = _model_display(value)
			elif headers[index] == "validation":
				value = _validation_display(value)
			elif headers[index] == "selection_metric":
				value = _metric_display(value)
			item.set_text(index, value)
		shown += 1


func _model_display(value: String) -> String:
	return value.replace("_", " ").capitalize()


func _validation_display(value: String) -> String:
	if value.is_empty():
		return value
	var key := "OPTION_" + value.to_upper()
	var localized := tr(key)
	return value if localized == key else localized


func _metric_display(value: String) -> String:
	if value.is_empty():
		return value
	var key := "METRIC_" + value.to_upper()
	var localized := tr(key)
	return value if localized == key else localized


func _open_results() -> void:
	if not last_result_dir.is_empty():
		OS.shell_open(last_result_dir)


func _show_error(message: String) -> void:
	if status_label != null:
		status_key = "ERROR"
		status_detail = message
		status_label.text = tr("ERROR") % message


func _set_status(key: String) -> void:
	status_key = key
	status_detail = ""
	status_label.text = tr(key)


func _show_core_error(error: Dictionary) -> void:
	var code := str(error.get("code", "analysis_failed")).to_upper()
	var key := "ERROR_" + code
	var localized := tr(key)
	if localized == key:
		localized = tr("ERROR_ANALYSIS_FAILED")
	var detail := str(error.get("message", ""))
	_show_error(localized + ("\n" + detail if not detail.is_empty() else ""))


func _localized_warning(warning: String) -> String:
	if warning.begins_with("Dropped "):
		return tr("WARN_DROPPED")
	if warning.begins_with("A group column was supplied"):
		return tr("WARN_GROUP_NOT_ISOLATED")
	if warning.begins_with("The target classes are imbalanced"):
		return tr("WARN_IMBALANCED")
	return warning


func _render_warnings() -> void:
	if warnings_text == null:
		return
	var warning_lines: Array[String] = []
	for warning in last_warnings:
		warning_lines.append(_localized_warning(warning))
	warnings_text.text = "\n".join(warning_lines)
