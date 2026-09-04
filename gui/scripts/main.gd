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
var subtitle_label: Label
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
var validation_option: OptionButton
var folds_spin: SpinBox
var model_option: OptionButton
var output_edit: LineEdit
var review_text: TextEdit
var status_label: Label
var progress_bar: ProgressBar
var run_button: Button
var cancel_button: Button
var warnings_text: RichTextLabel
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
	app_theme.set_stylebox("panel", "TabContainer", _style_box(Color.WHITE, 8))
	app_theme.set_stylebox("panel", "Tree", _style_box(Color("fbfcff"), 5, Color("d9deea")))
	app_theme.set_stylebox("panel", "ItemList", _style_box(Color("fbfcff"), 5, Color("d9deea")))
	app_theme.set_stylebox("normal", "LineEdit", _style_box(Color.WHITE, 5, Color("cbd2e1")))
	app_theme.set_stylebox("normal", "TextEdit", _style_box(Color.WHITE, 5, Color("cbd2e1")))
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
	title.add_theme_font_size_override("font_size", 30)
	title.add_theme_color_override("font_color", ACCENT)
	brand.add_child(title)
	subtitle_label = _translated_label("APP_SUBTITLE")
	subtitle_label.add_theme_color_override("font_color", Color("59657a"))
	brand.add_child(subtitle_label)
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
	validation_option = _value_option(
		["holdout", "k_fold", "stratified_k_fold", "group_k_fold", "leave_one_group_out"]
	)
	_add_field(grid, "VALIDATION", validation_option)
	folds_spin = SpinBox.new()
	folds_spin.min_value = 2
	folds_spin.max_value = 20
	folds_spin.value = 5
	_add_field(grid, "FOLDS", folds_spin)
	model_option = OptionButton.new()
	_add_field(grid, "MODEL", model_option)
	_populate_task_options()
	task_option.item_selected.connect(func(_index): _on_task_changed())
	target_option.item_selected.connect(func(_index): _on_column_role_changed())
	group_option.item_selected.connect(func(_index): _on_column_role_changed())
	for control in [missing_option, scaling_option, validation_option, model_option]:
		control.item_selected.connect(func(_index): _refresh_review())
	folds_spin.value_changed.connect(func(_value): _refresh_review())


func _add_field(grid: GridContainer, key: String, control: Control) -> void:
	grid.add_child(_translated_label(key))
	control.custom_minimum_size = Vector2(420, 42)
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
	cancel_button.pressed.connect(func(): bridge.cancel_analysis())
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
	_refresh_review()


func _populate_models() -> void:
	if capabilities.is_empty() or capabilities.has("error") or model_option == null:
		return
	model_option.clear()
	var task: String = task_option.get_item_metadata(task_option.selected)
	for model in capabilities.models[task]:
		model_option.add_item(str(model).replace("_", " ").capitalize())
		model_option.set_item_metadata(model_option.item_count - 1, model)


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
	_refresh_review()


func _selected_features() -> Array[String]:
	var result: Array[String] = []
	for index in feature_list.get_selected_items():
		result.append(feature_list.get_item_metadata(index))
	return result


func _build_config() -> Dictionary:
	if preview_payload.is_empty():
		return {"error": tr("SELECT_DATA")}
	if target_option.item_count == 0:
		return {"error": tr("SELECT_TARGET")}
	var features := _selected_features()
	if features.is_empty():
		return {"error": tr("SELECT_FEATURE")}
	return {
		"schema_version": "1.0",
		"task": task_option.get_item_metadata(task_option.selected),
		"target_column": target_option.get_item_metadata(target_option.selected),
		"model_name": model_option.get_item_metadata(model_option.selected),
		"input_path": data_path_edit.text,
		"output_dir": output_edit.text,
		"group_column": group_option.get_item_metadata(group_option.selected),
		"feature_columns": features,
		"test_size": 0.2,
		"random_seed": 42,
		"validation_strategy": validation_option.get_item_metadata(validation_option.selected),
		"n_splits": int(folds_spin.value),
		"missing_strategy": missing_option.get_item_metadata(missing_option.selected),
		"scaling": scaling_option.get_item_metadata(scaling_option.selected),
		"include_data_hash": true,
		"model_params": {},
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
	progress_bar.value = 0.0
	run_button.disabled = true
	cancel_button.disabled = false
	if not bridge.start_analysis(pending_config_path):
		run_button.disabled = false
		cancel_button.disabled = true
		_cleanup_pending_config()
		_show_error("PsyML Core is already running")


func _on_core_event(event: Dictionary) -> void:
	progress_bar.value = float(event.get("progress", 0.0))
	match event.get("event", ""):
		"started":
			_set_status("RUNNING")
		"completed":
			_cleanup_pending_config()
			_set_status("COMPLETED")
			run_button.disabled = false
			cancel_button.disabled = true
			_load_results(event.result_path)
		"cancelled":
			_cleanup_pending_config()
			_set_status("CANCELLED")
			run_button.disabled = false
			cancel_button.disabled = true
		"failed":
			_cleanup_pending_config()
			run_button.disabled = false
			cancel_button.disabled = true
			_show_core_error(event.get("error", {}))


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
	_render_warnings()
	metrics_tree.clear()
	var root := metrics_tree.create_item()
	for metric in parsed.metrics:
		var item := metrics_tree.create_item(root)
		item.set_text(0, metric)
		item.set_text(1, "%.6f" % parsed.metrics[metric])
	var artifacts: Dictionary = parsed.artifacts
	_load_predictions(last_result_dir.path_join(artifacts.predictions))
	var image := Image.load_from_file(last_result_dir.path_join(artifacts.figure))
	if image != null and not image.is_empty():
		figure_view.texture = ImageTexture.create_from_image(image)
	tabs.current_tab = 3


func _load_predictions(path: String) -> void:
	predictions_tree.clear()
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return
	var headers := file.get_csv_line()
	predictions_tree.columns = headers.size()
	predictions_tree.column_titles_visible = true
	for index in range(headers.size()):
		predictions_tree.set_column_title(index, headers[index])
	var root := predictions_tree.create_item()
	var shown := 0
	while not file.eof_reached() and shown < 20:
		var values := file.get_csv_line()
		if values.size() == 1 and values[0].is_empty():
			continue
		var item := predictions_tree.create_item(root)
		for index in range(min(headers.size(), values.size())):
			item.set_text(index, values[index])
		shown += 1


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
