extends Control

const ACCENT := Color("5261c9")
const TEXT := Color("20232b")
const SURFACE := Color("f7f8fa")
const BORDER := Color("dce0e6")
const MUTED := Color("626977")
const RADIUS := 6

var bridge: CoreBridge
var capabilities: Dictionary = {}
var preview_payload: Dictionary = {}
var previewed_path := ""
var pending_preview_path := ""
var is_preview_loading := false
var translated_controls: Array[Dictionary] = []
var localized_value_options: Array[OptionButton] = []
var tabs: TabContainer
var language_label: Label
var language_option: OptionButton
var browse_button: Button
var preview_button: Button
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
var parameter_editor_task := ""
var parameter_editor_mode := ""
var choose_folder_button: Button
var refresh_review_button: Button
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
var open_results_button: Button
var file_dialog: FileDialog
var folder_dialog: FileDialog
var last_result_dir := ""
var last_result_path := ""
var status_key := "READY"
var status_detail := ""
var last_warnings: Array = []
var configuration_io
var pending_config_path := ""
var is_analysis_running := false
var progress_key := "PROGRESS_WAITING"
var progress_values: Dictionary = {}
var primary_validation_option: OptionButton
var figure_choices: VBoxContainer
var copy_error_button: Button
var error_details: TextEdit
var run_folder_name := ""
var sample_data_button: Button
var figure_option: OptionButton
var validation_result_option: OptionButton
var validation_result_entries: Dictionary = {}
var checked_icon: Texture2D
var unchecked_icon: Texture2D



func _ready() -> void:
	get_window().min_size = Vector2i(1000, 700)
	PsyMLI18n.install()
	TranslationServer.set_locale("zh_CN")
	_build_theme()
	_bind_scene()
	bridge = %CoreBridge
	bridge.preview_ready.connect(_on_preview_ready)
	bridge.preview_failed.connect(_on_preview_failed)
	bridge.event_received.connect(_on_core_event)
	capabilities = bridge.execute_json_sync(PackedStringArray(["capabilities"]))
	if capabilities.has("error"):
		_show_error(capabilities["error"].get("message", "PsyML Core unavailable"))
	else:
		_populate_models()
	_apply_language()
	if "--psyml-smoke-test" in OS.get_cmdline_user_args():
		preload("res://scripts/native_smoke.gd").run(self)


func _build_theme() -> void:
	var app_theme := Theme.new()
	app_theme.default_font_size = 16
	for control_type in ["Label", "Button", "OptionButton", "LineEdit", "TextEdit", "Tree", "ItemList"]:
		app_theme.set_color("font_color", control_type, TEXT)
	app_theme.set_color("font_hover_color", "Button", TEXT)
	app_theme.set_color("font_pressed_color", "Button", TEXT)
	app_theme.set_color("font_selected_color", "TabBar", TEXT)
	app_theme.set_color("font_unselected_color", "TabBar", Color("59657a"))
	app_theme.set_color("font_selected_color", "ItemList", Color.WHITE)
	app_theme.set_color("font_readonly_color", "TextEdit", TEXT)
	app_theme.set_stylebox("panel", "TabContainer", _style_box(Color.WHITE, RADIUS))
	app_theme.set_stylebox("panel", "PanelContainer", _style_box(SURFACE, RADIUS))
	app_theme.set_stylebox("panel", "Tree", _style_box(Color.WHITE, RADIUS, BORDER))
	app_theme.set_stylebox("panel", "ItemList", _style_box(Color.WHITE, RADIUS, BORDER))
	app_theme.set_stylebox("selected", "ItemList", _style_box(ACCENT, RADIUS))
	app_theme.set_stylebox("selected_focus", "ItemList", _style_box(ACCENT, RADIUS))
	app_theme.set_stylebox("normal", "LineEdit", _style_box(Color.WHITE, RADIUS, Color("cbd2e1")))
	app_theme.set_stylebox("focus", "LineEdit", _style_box(Color.TRANSPARENT, RADIUS, ACCENT))
	app_theme.set_stylebox("normal", "TextEdit", _style_box(Color.WHITE, RADIUS, Color("cbd2e1")))
	app_theme.set_stylebox("read_only", "TextEdit", _style_box(Color("fbfcff"), RADIUS, Color("cbd2e1")))
	for button_type in ["Button", "OptionButton"]:
		app_theme.set_stylebox("normal", button_type, _style_box(Color("f1f3f6"), RADIUS))
		app_theme.set_stylebox("hover", button_type, _style_box(Color("e7eaf0"), RADIUS))
		app_theme.set_stylebox("pressed", button_type, _style_box(Color("dde1eb"), RADIUS))
		app_theme.set_stylebox("focus", button_type, _style_box(Color.TRANSPARENT, RADIUS, ACCENT))
		app_theme.set_stylebox("disabled", button_type, _style_box(Color("eef0f4"), RADIUS))
		app_theme.set_color("font_disabled_color", button_type, MUTED)
	app_theme.set_stylebox("tab_selected", "TabBar", _style_box(Color.WHITE, RADIUS))
	app_theme.set_stylebox("tab_unselected", "TabBar", _style_box(Color("e3e7ef"), RADIUS))
	app_theme.set_stylebox("background", "ProgressBar", _style_box(Color("e3e7ef"), RADIUS))
	app_theme.set_stylebox("fill", "ProgressBar", _style_box(ACCENT, RADIUS))
	app_theme.set_type_variation("AccentButton", "Button")
	app_theme.set_stylebox("normal", "AccentButton", _style_box(ACCENT, RADIUS))
	app_theme.set_stylebox("hover", "AccentButton", _style_box(Color("4d6bea"), RADIUS))
	app_theme.set_stylebox("pressed", "AccentButton", _style_box(Color("405ed8"), RADIUS))
	app_theme.set_stylebox("focus", "AccentButton", _style_box(Color.TRANSPARENT, RADIUS, Color("263f9f")))
	app_theme.set_stylebox("disabled", "AccentButton", _style_box(Color("b8c2e8"), RADIUS))
	app_theme.set_color("font_color", "AccentButton", Color.WHITE)
	app_theme.set_color("font_hover_color", "AccentButton", Color.WHITE)
	app_theme.set_color("font_disabled_color", "AccentButton", Color("f5f6fb"))
	app_theme.set_type_variation("DangerButton", "Button")
	app_theme.set_stylebox("normal", "DangerButton", _style_box(Color("fff0f0"), RADIUS, Color("e6a3a3")))
	app_theme.set_stylebox("hover", "DangerButton", _style_box(Color("ffe1e1"), RADIUS, Color("cf6f6f")))
	app_theme.set_stylebox("pressed", "DangerButton", _style_box(Color("f8caca"), RADIUS, Color("b84f4f")))
	app_theme.set_stylebox("focus", "DangerButton", _style_box(Color("fff0f0"), RADIUS, Color("b84f4f")))
	app_theme.set_stylebox("disabled", "DangerButton", _style_box(Color("eef0f4"), RADIUS))
	app_theme.set_color("font_color", "DangerButton", Color("9f3030"))
	app_theme.set_color("font_hover_color", "DangerButton", Color("842424"))
	app_theme.set_color("font_disabled_color", "DangerButton", MUTED)
	app_theme.set_color("font_uneditable_color", "LineEdit", MUTED)
	app_theme.set_color("font_focus_color", "Button", TEXT)
	app_theme.set_color("font_focus_color", "OptionButton", TEXT)
	app_theme.set_color("font_focus_color", "AccentButton", Color.WHITE)
	app_theme.set_color("font_focus_color", "DangerButton", Color("842424"))
	app_theme.set_color("default_color", "RichTextLabel", TEXT)
	app_theme.set_color("font_pressed_color", "AccentButton", Color.WHITE)
	app_theme.set_color("font_pressed_color", "DangerButton", Color("842424"))
	app_theme.set_color("font_selected_color", "ItemList", TEXT)
	app_theme.set_stylebox("selected", "ItemList", _style_box(Color("e6e9fc"), RADIUS))
	app_theme.set_stylebox("selected_focus", "ItemList", _style_box(Color("e6e9fc"), RADIUS, ACCENT))
	app_theme.set_constant("line_separation", "ItemList", 4)
	app_theme.set_color("guide_color", "Tree", Color.TRANSPARENT)
	app_theme.set_color("font_color", "Tree", TEXT)
	app_theme.set_color("font_selected_color", "Tree", TEXT)
	app_theme.set_stylebox("selected", "Tree", _style_box(Color("e6e9fc"), RADIUS))
	app_theme.set_stylebox("selected_focus", "Tree", _style_box(Color("e6e9fc"), RADIUS, ACCENT))
	app_theme.set_color("title_button_color", "Tree", MUTED)
	for state in ["normal", "hover", "pressed"]:
		app_theme.set_stylebox("title_button_" + state, "Tree", _style_box(SURFACE, 0))
	for kind in ["Tree", "ItemList", "TextEdit"]:
		app_theme.set_stylebox("focus", kind, _style_box(Color.TRANSPARENT, RADIUS, ACCENT))
	app_theme.set_stylebox("read_only", "LineEdit", _style_box(SURFACE, RADIUS, BORDER))
	var selected_tab := _style_box(Color.WHITE, RADIUS)
	selected_tab.border_color = ACCENT
	selected_tab.border_width_bottom = 2
	app_theme.set_stylebox("tab_selected", "TabContainer", selected_tab)
	app_theme.set_stylebox("tab_unselected", "TabContainer", _style_box(Color.TRANSPARENT, RADIUS))
	app_theme.set_stylebox("tab_hovered", "TabContainer", _style_box(Color("e9ecf2"), RADIUS))
	app_theme.set_stylebox("tab_focus", "TabContainer", _style_box(Color.TRANSPARENT, RADIUS, ACCENT))
	app_theme.set_color("font_selected_color", "TabContainer", TEXT)
	app_theme.set_color("font_unselected_color", "TabContainer", MUTED)
	app_theme.set_color("font_hovered_color", "TabContainer", TEXT)
	preload("res://scripts/light_theme.gd").apply_to(app_theme, TEXT, MUTED, SURFACE, BORDER, ACCENT)
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


func _bind_scene() -> void:
	tabs = %Tabs
	language_label = %LanguageLabel
	language_option = %LanguageOption
	translated_controls.append({"node": language_label, "key": "LANGUAGE"})
	for item in ["中文", "English", "Français"]:
		language_option.add_item(item)
	language_option.selected = 0
	language_option.item_selected.connect(_on_language_selected)
	_bind_data_tab()
	_bind_config_tab()
	_bind_review_tab()
	_bind_results_tab()
	_bind_dialogs()
	_bind_feedback_controls()
	configuration_io = preload("res://scripts/configuration_io.gd").new(self)


func _bind_data_tab() -> void:
	data_path_edit = %DataPathEdit
	data_summary_label = %DataSummaryLabel
	variable_tree = %VariableTree
	sample_tree = %SampleTree
	feature_list = %FeatureList
	browse_button = %BrowseButton
	preview_button = %PreviewButton
	translated_controls.append_array(
		[
			{"node": %DataHeading, "key": "DATA_HEADING"},
			{"node": %DataSourceSectionLabel, "key": "DATA_SOURCE_SECTION"},
			{"node": %DataPathLabel, "key": "DATA_PATH"},
			{"node": browse_button, "key": "BROWSE"},
			{"node": preview_button, "key": "PREVIEW"},
			{"node": %VariablesLabel, "key": "VARIABLES"},
			{"node": %SampleLabel, "key": "SAMPLE"},
			{"node": %FeaturesLabel, "key": "FEATURES"},
		]
	)
	browse_button.pressed.connect(func(): file_dialog.popup_centered_ratio(0.8))
	preview_button.pressed.connect(_request_preview)
	data_path_edit.text_changed.connect(_on_data_path_changed)
	feature_list.multi_selected.connect(func(_index, _selected): _refresh_review())


func _bind_config_tab() -> void:
	task_option = %TaskOption
	target_option = %TargetOption
	group_option = %GroupOption
	missing_option = %MissingOption
	scaling_option = %ScalingOption
	validation_list = %ValidationList
	folds_spin = %FoldsSpin
	model_list = %ModelList
	tuning_option = %TuningOption
	selection_metric_option = %SelectionMetricOption
	inner_folds_spin = %InnerFoldsSpin
	max_candidates_spin = %MaxCandidatesSpin
	parameter_editor = %ParameterEditor
	translated_controls.append_array(
		[
			{"node": %ConfigureHeading, "key": "CONFIG_HEADING"},
			{"node": %DesignSectionLabel, "key": "RESEARCH_DESIGN_SECTION"},
			{"node": %TaskLabel, "key": "TASK"},
			{"node": %TargetLabel, "key": "TARGET"},
			{"node": %GroupLabel, "key": "GROUP"},
			{"node": %MissingLabel, "key": "MISSING"},
			{"node": %ScalingLabel, "key": "SCALING"},
			{"node": %ValidationLabel, "key": "VALIDATION"},
			{"node": %FoldsLabel, "key": "FOLDS"},
			{"node": %ModelLabel, "key": "MODEL"},
			{"node": %PrimaryValidationHelp, "key": "PRIMARY_VALIDATION_HELP"},
			{"node": %ParameterSectionLabel, "key": "PARAMETER_SECTION"},
			{"node": %TuningLabel, "key": "TUNING"},
			{"node": %SelectionMetricLabel, "key": "SELECTION_METRIC"},
			{"node": %InnerFoldsLabel, "key": "INNER_FOLDS"},
			{"node": %MaxCandidatesLabel, "key": "MAX_CANDIDATES"},
			{"node": %ParameterHelpLabel, "key": "PARAMETER_HELP"},
		]
	)
	_populate_value_option(missing_option, ["drop", "mean", "median", "mode"])
	missing_option.select(2)
	_populate_value_option(scaling_option, ["none", "standard", "minmax"])
	scaling_option.select(1)
	_populate_value_option(tuning_option, ["tuning_none", "tuning_quick", "tuning_custom"])
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


func _populate_value_option(option: OptionButton, values: Array) -> void:
	for value in values:
		option.add_item(tr("OPTION_" + str(value).to_upper()))
		option.set_item_metadata(option.item_count - 1, value)
	localized_value_options.append(option)


func _populate_task_options() -> void:
	var previous = task_option.get_item_metadata(task_option.selected) if task_option.item_count else null
	task_option.clear()
	for task in ["classification", "regression"]:
		task_option.add_item(tr(task.to_upper()))
		task_option.set_item_metadata(task_option.item_count - 1, task)
		if task == previous:
			task_option.select(task_option.item_count - 1)


func _bind_review_tab() -> void:
	output_edit = %OutputEdit
	review_text = %ReviewText
	progress_detail_label = %ProgressDetailLabel
	status_label = %StatusLabel
	progress_bar = %ProgressBar
	cancel_button = %CancelButton
	run_button = %RunButton
	choose_folder_button = %ChooseFolderButton
	refresh_review_button = %RefreshReviewButton
	output_edit.text = OS.get_system_dir(OS.SYSTEM_DIR_DOCUMENTS).path_join("PsyML Results")
	_set_progress("PROGRESS_WAITING")
	translated_controls.append_array(
		[
			{"node": %ReviewHeading, "key": "REVIEW_HEADING"},
			{"node": %ConfigReviewSectionLabel, "key": "CONFIG_REVIEW_SECTION"},
			{"node": %OutputFolderLabel, "key": "OUTPUT_FOLDER"},
			{"node": choose_folder_button, "key": "CHOOSE_FOLDER"},
			{"node": refresh_review_button, "key": "REFRESH_REVIEW"},
			{"node": %OutputHelpLabel, "key": "OUTPUT_HELP"},
			{"node": %ExecutionSectionLabel, "key": "EXECUTION_SECTION"},
			{"node": %StopHelpLabel, "key": "STOP_HELP"},
			{"node": status_label, "key": "READY"},
			{"node": cancel_button, "key": "CANCEL"},
			{"node": run_button, "key": "RUN"},
		]
	)
	choose_folder_button.pressed.connect(func(): folder_dialog.popup_centered_ratio(0.75))
	refresh_review_button.pressed.connect(_refresh_review)
	output_edit.text_changed.connect(func(_text): _refresh_review())
	cancel_button.pressed.connect(_request_cancel)
	run_button.pressed.connect(_on_run_pressed)


func _bind_results_tab() -> void:
	no_results_label = %NoResultsLabel
	best_result_label = %BestResultLabel
	comparison_tree = %ComparisonTree
	warnings_text = %WarningsText
	metrics_tree = %MetricsTree
	predictions_tree = %PredictionsTree
	figure_view = %FigureView
	open_results_button = %OpenResultsButton
	translated_controls.append_array(
		[
			{"node": %ResultsHeading, "key": "RESULTS_HEADING"},
			{"node": no_results_label, "key": "NO_RESULTS"},
			{"node": %ResultSummarySectionLabel, "key": "RESULT_SUMMARY_SECTION"},
			{"node": %ComparisonsLabel, "key": "COMPARISONS"},
			{"node": %WarningsLabel, "key": "WARNINGS"},
			{"node": %MetricsLabel, "key": "METRICS"},
			{"node": %PredictionsLabel, "key": "PREDICTIONS"},
			{"node": %ResultVisualSectionLabel, "key": "RESULT_VISUAL_SECTION"},
			{"node": open_results_button, "key": "OPEN_RESULTS"},
		]
	)
	open_results_button.pressed.connect(_open_results)


func _bind_dialogs() -> void:
	file_dialog = %FileDialog
	folder_dialog = %FolderDialog
	file_dialog.file_selected.connect(_on_file_selected)
	folder_dialog.dir_selected.connect(func(path): output_edit.text = path; _refresh_review())


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
	for control in find_children("*", "Control", true, false):
		if control is Label:
			control.tooltip_text = tr("COPY_TEXT_HINT")
		elif control is Tree:
			control.tooltip_text = tr("COPY_ROW_HINT")
	if figure_choices != null:
		for child in figure_choices.get_children():
			if child is Label:
				child.text = tr("OUTPUT_FIGURES")
			elif child is CheckBox:
				child.text = tr("FIGURE_" + str(child.get_meta("figure")).to_upper())
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
	tabs.set_tab_hidden(1, true)
	tabs.set_tab_title(2, tr("TAB_REVIEW"))
	tabs.set_tab_title(3, tr("TAB_RESULTS"))
	_update_primary_validation()
	_update_checks()
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
	_refresh_progress_text()
	_populate_parameter_editor()
	_render_warnings()
	_refresh_review()
	if not last_result_path.is_empty():
		_load_results(last_result_path, false)


func _update_tree_titles() -> void:
	variable_tree.set_column_title(0, tr("COLUMN"))
	variable_tree.set_column_title(1, tr("TYPE"))
	variable_tree.set_column_title(2, tr("MISSING_COUNT"))
	metrics_tree.set_column_title(0, tr("METRICS"))
	metrics_tree.set_column_title(1, tr("VALUE"))


func _on_data_path_changed(path: String) -> void:
	if not previewed_path.is_empty() and path != previewed_path:
		preview_payload = {}
		previewed_path = ""
		variable_tree.clear()
		sample_tree.clear()
		feature_list.clear()
		target_option.clear()
		group_option.clear()
		data_summary_label.text = tr("NO_DATA")
	_refresh_review()


func _on_file_selected(path: String) -> void:
	data_path_edit.text = path
	_request_preview()


func _request_preview() -> void:
	if is_preview_loading or is_analysis_running:
		return
	if data_path_edit.text.strip_edges().is_empty():
		_show_error(tr("SELECT_DATA"))
		return
	_clear_results()
	preview_payload = {}
	previewed_path = ""
	variable_tree.clear()
	sample_tree.clear()
	feature_list.clear()
	target_option.clear()
	group_option.clear()
	pending_preview_path = data_path_edit.text
	is_preview_loading = true
	data_summary_label.text = tr("PREVIEW_LOADING")
	_update_action_states(false)
	bridge.request_preview(data_path_edit.text, true)


func _on_preview_ready(payload: Dictionary) -> void:
	is_preview_loading = false
	if pending_preview_path != data_path_edit.text:
		pending_preview_path = ""
		_update_action_states(false)
		return
	previewed_path = pending_preview_path
	pending_preview_path = ""
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
		row.set_text(2, str(int(column.missing_count)))
		feature_list.add_item(column.name)
		feature_list.set_item_metadata(feature_list.item_count - 1, column.name)
		feature_list.select(feature_list.item_count - 1, false)
		target_option.add_item(column.name)
		target_option.set_item_metadata(target_option.item_count - 1, column.name)
		group_option.add_item(column.name)
		group_option.set_item_metadata(group_option.item_count - 1, column.name)
	_populate_sample(payload.get("sample", []))
	_on_column_role_changed()
	# Keep the researcher on the combined data/setup page.


func _populate_sample(rows: Array) -> void:
	sample_tree.clear()
	if rows.is_empty():
		return
	var headers: Array = rows[0].keys()
	sample_tree.columns = headers.size()
	sample_tree.column_titles_visible = true
	for index in range(headers.size()):
		sample_tree.set_column_title(index, str(headers[index]))
		sample_tree.set_column_custom_minimum_width(index, 150)
		sample_tree.set_column_expand(index, false)
	var root := sample_tree.create_item()
	for values in rows:
		var item := sample_tree.create_item(root)
		for index in range(headers.size()):
			item.set_text(index, str(values.get(headers[index], "")))


func _on_preview_failed(error: Dictionary) -> void:
	is_preview_loading = false
	pending_preview_path = ""
	data_summary_label.text = tr("NO_DATA")
	_refresh_review()
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
	_populate_figures()
	_update_primary_validation()
	_update_checks()


func _capture_parameter_values() -> void:
	if parameter_editor_mode != "tuning_custom":
		return
	for key in parameter_controls:
		var controls: Dictionary = parameter_controls[key]
		saved_parameter_values[parameter_editor_task + "::" + str(key)] = {
			"enabled": controls.enabled.button_pressed,
			"values": controls.values.text,
		}


func _populate_parameter_editor() -> void:
	if parameter_editor == null or capabilities.is_empty() or capabilities.has("error"):
		return
	_capture_parameter_values()
	parameter_editor_task = task_option.get_item_metadata(task_option.selected)
	for child in parameter_editor.get_children():
		parameter_editor.remove_child(child)
		child.queue_free()
	parameter_controls.clear()
	var tuning_mode: String = tuning_option.get_item_metadata(tuning_option.selected)
	parameter_editor_mode = tuning_mode
	if tuning_mode == "tuning_none":
		var no_search := Label.new()
		no_search.text = tr("NO_PARAMETER_SEARCH")
		no_search.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		parameter_editor.add_child(no_search)
		_configure_readable_controls(parameter_editor)
		_refresh_review()
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
			var saved_key := parameter_editor_task + "::" + key
			if tuning_mode == "tuning_custom" and saved_parameter_values.has(saved_key):
				enabled.button_pressed = saved_parameter_values[saved_key].enabled
				values.text = saved_parameter_values[saved_key].values
			values.text_changed.connect(func(_text): _refresh_review())
			enabled.toggled.connect(func(_pressed): _refresh_review())
			parameter_grid.add_child(values)
			parameter_controls[key] = {"enabled": enabled, "values": values}
	_configure_readable_controls(parameter_editor)
	_set_parameter_inputs_enabled(not is_analysis_running)
	_refresh_review()


func _selected_values(list_control: ItemList) -> Array[String]:
	var values: Array[String] = []
	for index in list_control.get_selected_items():
		values.append(list_control.get_item_metadata(index))
	return values


func _selected_models() -> Array[String]:
	return _selected_values(model_list)


func _selected_validations() -> Array[String]:
	var selected := _selected_values(validation_list)
	if primary_validation_option != null and primary_validation_option.selected >= 0:
		var primary = primary_validation_option.get_item_metadata(primary_validation_option.selected)
		if primary != null and primary in selected:
			selected.erase(primary)
			selected.push_front(primary)
	return selected


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
		validation_list.set_item_tooltip(index, tr("GROUP_REQUIRED") if unavailable else "")
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
	target_option.tooltip_text = str(target)
	group_option.tooltip_text = str(group) if group != null else tr("NONE")
	for index in range(feature_list.item_count):
		var column = feature_list.get_item_metadata(index)
		feature_list.set_item_disabled(index, column == target or column == group)
		feature_list.set_item_tooltip(index, str(column) + (" — " + tr("ROLE_EXCLUDED") if column == target or column == group else ""))
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
		# Godot JSON parses numbers as floats. Serialize integer count candidates
		# as integers; fractional min_samples candidates below 1 remain fractions.
		var count_parameters := ["n_neighbors", "n_estimators", "max_depth", "min_samples_leaf", "min_samples_split", "max_leaf_nodes", "max_iter", "random_state", "cv", "n_jobs", "degree", "n_components"]
		if parts[1] in count_parameters:
			for index in range(parsed.size()):
				if parsed[index] is float and is_finite(parsed[index]) and parsed[index] == floor(parsed[index]):
					parsed[index] = int(parsed[index])
		grids[parts[0]][parts[1]] = parsed
	return {"grids": grids}


func _build_config() -> Dictionary:
	if is_preview_loading or preview_payload.is_empty() or previewed_path != data_path_edit.text:
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
	var output_path := output_edit.text.strip_edges()
	if output_path.is_empty() or not output_path.is_absolute_path():
		return {"error": tr("SELECT_OUTPUT")}
	if run_folder_name.is_empty():
		run_folder_name = _new_run_folder()
	output_path = output_path.path_join(run_folder_name)
	var grid_payload := _parameter_grid_payload()
	if grid_payload.has("error"):
		return grid_payload
	var tuning_mode: String = tuning_option.get_item_metadata(tuning_option.selected)
	var config := {
		"schema_version": "1.0",
		"task": task_option.get_item_metadata(task_option.selected),
		"target_column": target_option.get_item_metadata(target_option.selected),
		"model_name": models[0],
		"model_names": models,
		"input_path": data_path_edit.text,
		"output_dir": output_path,
		"group_column": group_option.get_item_metadata(group_option.selected),
		"feature_columns": features,
		"test_size": 0.2,
		"random_seed": 42,
		"validation_strategy": validations[0],
		"primary_validation": primary_validation_option.get_item_metadata(primary_validation_option.selected),
		"validation_strategies": validations,
		"n_splits": int(folds_spin.value),
		"missing_strategy": missing_option.get_item_metadata(missing_option.selected),
		"scaling": scaling_option.get_item_metadata(scaling_option.selected),
		"include_data_hash": true,
		"model_params": {},
		"figure_types": _selected_figures(),
		"tuning_mode": tuning_mode.trim_prefix("tuning_"),
		"parameter_grids": grid_payload.grids,
		"selection_metric": selection_metric_option.get_item_metadata(
			selection_metric_option.selected
		),
		"inner_splits": int(inner_folds_spin.value),
		"selection_protocol": "nested_family_v1",
		"max_candidates": int(max_candidates_spin.value),
	}

	return configuration_io.enrich(config) if configuration_io != null else config


func _refresh_review() -> void:
	_update_checks()
	_update_primary_validation()
	if review_text == null:
		return
	var config := _build_config()
	if config.has("error"):
		review_text.text = config.error
	else:
		review_text.text = JSON.stringify(config, "  ")
	_update_action_states(not config.has("error"))


func _analysis_inputs() -> Array[Control]:
	return [
		data_path_edit,
		browse_button,
		preview_button,
		sample_data_button,
		feature_list,
		task_option,
		target_option,
		group_option,
		missing_option,
		scaling_option,
		primary_validation_option,
		validation_list,
		folds_spin,
		model_list,
		tuning_option,
		selection_metric_option,
		inner_folds_spin,
		max_candidates_spin,
		output_edit,
		choose_folder_button,
		refresh_review_button,
	]


func _set_control_interactive(control: Control, enabled: bool) -> void:
	if control is LineEdit:
		control.editable = enabled
	elif control is SpinBox:
		control.editable = enabled
	elif control is BaseButton:
		control.disabled = not enabled
	elif control is ItemList:
		control.mouse_filter = Control.MOUSE_FILTER_STOP if enabled else Control.MOUSE_FILTER_IGNORE
		control.focus_mode = Control.FOCUS_ALL if enabled else Control.FOCUS_NONE
		control.modulate = Color.WHITE if enabled else Color(1, 1, 1, 0.58)


func _set_parameter_inputs_enabled(enabled: bool) -> void:
	var tuning_mode: String = tuning_option.get_item_metadata(tuning_option.selected)
	for child in figure_choices.get_children():
		if child is CheckBox:
			child.disabled = not enabled
	for key in parameter_controls:
		var controls: Dictionary = parameter_controls[key]
		controls.enabled.disabled = not enabled or tuning_mode == "tuning_quick"
		controls.values.editable = enabled and tuning_mode == "tuning_custom"


func _set_running_state(running: bool) -> void:
	is_analysis_running = running
	configuration_io.set_enabled(not running)
	for control in _analysis_inputs():
		_set_control_interactive(control, not running)
	_set_parameter_inputs_enabled(not running)
	if not running:
		_update_validation_availability()
	var config_valid := not _build_config().has("error") if not running else false
	_update_action_states(config_valid)


func _update_action_states(config_valid: bool) -> void:
	preview_button.disabled = (
		is_analysis_running
		or is_preview_loading
		or data_path_edit.text.strip_edges().is_empty()
	)
	browse_button.disabled = is_analysis_running or is_preview_loading
	run_button.disabled = is_analysis_running or is_preview_loading or not config_valid
	run_button.tooltip_text = tr("RUNNING") if is_analysis_running else str(_build_config().get("error", ""))
	preview_button.tooltip_text = tr("PREVIEW_LOADING") if is_preview_loading else tr("SELECT_DATA")
	cancel_button.tooltip_text = tr("STOP_HELP") if is_analysis_running else tr("NO_RUNNING_TASK")
	open_results_button.tooltip_text = tr("NO_RESULTS") if last_result_dir.is_empty() else last_result_dir
	cancel_button.disabled = not is_analysis_running
	open_results_button.disabled = last_result_dir.is_empty()


func _on_run_pressed() -> void:
	run_folder_name = _new_run_folder()
	var config := _build_config()
	if config.has("error"):
		_show_error(config.error)
		return
	_clear_results()
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
	_set_progress("PROGRESS_STARTING")
	progress_bar.value = 0.0
	_set_running_state(true)
	if not bridge.start_analysis(pending_config_path):
		_set_running_state(false)
		_cleanup_pending_config()
		_show_error("PsyML Core is already running")


func _request_cancel() -> void:
	if not bridge.is_running():
		return
	_set_status("CANCELLING")
	cancel_button.disabled = true
	_set_progress("PROGRESS_CANCELLING")
	bridge.cancel_analysis()


func _on_core_event(event: Dictionary) -> void:
	progress_bar.value = float(event.get("progress", 0.0))
	match event.get("event", ""):
		"started":
			_set_running_state(true)
			_set_status("RUNNING")
		"progress":
			_set_status("RUNNING")
			var completed := int(event.get("completed_tasks", 0))
			var total := int(event.get("total_tasks", 0))
			var remaining := int(event.get("remaining_tasks", 0))
			var eta_value = event.get("estimated_remaining_seconds", null)
			var model := str(event.get("current_model", ""))
			var validation := str(event.get("current_validation", ""))
			var current_fold := int(event.get("current_fold", 1))
			if completed == 0:
				_set_progress("PROGRESS_PLANNED", {"total": total})
			else:
				_set_progress(
					"PROGRESS_DETAIL",
					{
						"completed": completed,
						"total": total,
						"remaining": remaining,
						"eta_seconds": eta_value,
						"model": model,
						"validation": validation,
						"fold": current_fold,
					}
				)
		"completed":
			_cleanup_pending_config()
			_set_running_state(false)
			_set_status("COMPLETED")
			_set_progress("PROGRESS_COMPLETED")
			_load_results(event.result_path)
		"cancelled":
			_cleanup_pending_config()
			_set_running_state(false)
			_set_status("CANCELLED")
			_set_progress("PROGRESS_CANCELLED")
		"failed":
			_cleanup_pending_config()
			_set_running_state(false)
			_show_core_error(event.get("error", {}))


func _set_progress(key: String, values: Dictionary = {}) -> void:
	progress_key = key
	progress_values = values.duplicate(true)
	_refresh_progress_text()


func _refresh_progress_text() -> void:
	if progress_detail_label == null:
		return
	if progress_key == "PROGRESS_PLANNED":
		progress_detail_label.text = tr(progress_key) % int(progress_values.get("total", 0))
	elif progress_key == "PROGRESS_DETAIL":
		var eta_value = progress_values.get("eta_seconds", null)
		var eta := tr("ESTIMATING") if eta_value == null else _format_duration(float(eta_value))
		progress_detail_label.text = tr(progress_key) % [
			int(progress_values.get("completed", 0)),
			int(progress_values.get("total", 0)),
			int(progress_values.get("remaining", 0)),
			eta,
			_model_display(str(progress_values.get("model", ""))),
			_validation_display(str(progress_values.get("validation", ""))),
			int(progress_values.get("fold", 1)),
		]
	else:
		progress_detail_label.text = tr(progress_key)


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


func _clear_results() -> void:
	last_result_dir = ""
	last_result_path = ""
	validation_result_entries.clear()
	validation_result_option.clear()
	validation_result_option.hide()
	last_warnings = []
	best_result_label.text = ""
	warnings_text.text = ""
	for tree in [comparison_tree, metrics_tree, predictions_tree]:
		tree.clear()
	figure_view.texture = null
	figure_option.clear()
	figure_option.hide()
	no_results_label.visible = true
	open_results_button.disabled = true


func _load_results(result_path: String, navigate := true, as_child := false) -> void:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(result_path))
	if not parsed is Dictionary or parsed.get("status", "") not in ["completed", "completed_with_errors"] or not parsed.has("metrics") or not parsed.has("artifacts"):
		_clear_results()
		_show_error("Invalid or incomplete result.json")
		return
	var previous_validation = null
	if last_result_path == result_path and validation_result_option.selected >= 0:
		previous_validation = validation_result_option.get_item_metadata(validation_result_option.selected)
	if not as_child:
		last_result_path = result_path
	last_result_dir = result_path.get_base_dir()
	if parsed.get("evaluation_scope", "") == "independent_validations":
		_load_independent_results(parsed, previous_validation)
		if navigate:
			tabs.current_tab = 3
		return
	if not as_child:
		validation_result_entries.clear()
		validation_result_option.hide()
	open_results_button.disabled = false
	no_results_label.visible = false
	last_warnings = parsed.get("warnings", [])
	best_result_label.text = tr("VALIDATION_RESULT" if as_child else "BEST_RESULT") % [
		_model_display(str(parsed.get("best_model", ""))),
		_validation_display(str(parsed.get("best_validation", ""))),
		_metric_display(str(parsed.get("selection_metric", ""))),
	]
	best_result_label.text += "\n" + tr("FINAL_PARAMETERS") + JSON.stringify(parsed.get("best_parameters", {}))
	var nested: bool = parsed.get("evaluation_scope", "") == "nested_selection_procedure"
	var scope_key := "NESTED_METRICS" if nested else "PRESPECIFIED_METRICS"
	if as_child:
		scope_key = "VIEWING_NESTED_METRICS" if nested else "VIEWING_FIXED_METRICS"
	best_result_label.text += "\n" + tr(scope_key)
	_render_warnings()
	metrics_tree.clear()
	var root := metrics_tree.create_item()
	var metric_width := 220
	for metric in parsed.metrics:
		var item := metrics_tree.create_item(root)
		var metric_name := _metric_display(metric)
		item.set_text(0, metric_name)
		item.set_tooltip_text(0, metric_name)
		metric_width = maxi(metric_width, ceili(metrics_tree.get_theme_font("font").get_string_size(metric_name, HORIZONTAL_ALIGNMENT_LEFT, -1, metrics_tree.get_theme_font_size("font_size")).x) + 24)
		item.set_text(1, "%.6f" % parsed.metrics[metric])
	metrics_tree.set_column_custom_minimum_width(0, metric_width)
	metrics_tree.set_column_custom_minimum_width(1, 100)
	var artifacts: Dictionary = parsed.artifacts
	_load_csv_preview(last_result_dir.path_join(artifacts.model_comparison), comparison_tree, 30)
	_load_predictions(last_result_dir.path_join(artifacts.predictions))
	figure_option.clear()
	figure_view.texture = null
	for key in artifacts:
		if str(key).begins_with("figure_"):
			figure_option.add_item(tr(str(key).to_upper()))
			figure_option.set_item_metadata(figure_option.item_count - 1, artifacts[key])
	if figure_option.item_count == 0 and artifacts.has("figure"):
		figure_option.add_item("Figure")
		figure_option.set_item_metadata(0, artifacts.figure)
	figure_option.visible = figure_option.item_count > 0
	if figure_option.item_count > 0:
		_show_selected_figure(0)
	if navigate:
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
		var header := str(headers[index])
		tree.set_column_title(index, _column_display(header))
		tree.set_column_custom_minimum_width(index, _column_minimum_width(header))
		tree.set_column_expand(index, false)
	var root := tree.create_item()
	var shown := 0
	while not file.eof_reached() and shown < maximum_rows:
		var values := file.get_csv_line()
		if values.size() == 1 and values[0].is_empty():
			continue
		var item := tree.create_item(root)
		for index in range(min(headers.size(), values.size())):
			var header := str(headers[index])
			var value := str(values[index])
			if header == "model":
				value = _model_display(value)
			elif header == "validation":
				value = _validation_display(value)
			elif header == "selection_metric":
				value = _metric_display(value)
			elif header == "status":
				value = _status_display(value)
			elif header == "rank" and value.is_valid_float():
				value = str(int(value.to_float()))
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


func _column_display(value: String) -> String:
	var key := "COLUMN_" + value.to_upper()
	var localized := tr(key)
	return value if localized == key else localized


func _column_minimum_width(value: String) -> int:
	var widths := {
		"rank": 64,
		"model": 150,
		"validation": 160,
		"selection_metric": 150,
		"selection_score": 130,
		"status": 100,
		"error": 180,
		"row_index": 100,
		"fold": 90,
		"observed": 110,
		"predicted": 110,
	}
	return int(widths.get(value, 120))


func _status_display(value: String) -> String:
	var key := "STATUS_" + value.to_upper()
	var localized := tr(key)
	return value if localized == key else localized


func _open_results() -> void:
	if not last_result_dir.is_empty():
		OS.shell_open(last_result_dir)


func _show_error(message: String) -> void:
	if status_label != null:
		status_key = "ERROR"
		status_detail = message
		if error_details != null:
			error_details.text = message
			error_details.show()
			copy_error_button.show()
		status_label.text = tr("ERROR") % message
		status_label.add_theme_color_override("font_color", Color("a12c35"))
		progress_bar.value = 0.0
		_set_progress("PROGRESS_FAILED")


func _set_status(key: String) -> void:
	status_key = key
	status_detail = ""
	if error_details != null:
		error_details.hide()
		copy_error_button.hide()
	status_label.text = tr(key)
	status_label.add_theme_color_override("font_color", TEXT)


func _show_core_error(error: Dictionary) -> void:
	var code := str(error.get("code", "analysis_failed")).to_upper()
	var key := "ERROR_" + code
	var localized := tr(key)
	if localized == key:
		localized = tr("ERROR_ANALYSIS_FAILED")
	var detail := str(error.get("message", ""))
	if TranslationServer.get_locale().begins_with("zh"):
		if "parameter" in detail.to_lower():
			localized += "\n参数候选未能完成拟合。请检查下方具体参数名、类型和取值范围；计数参数使用整数，比例参数使用合法小数。"
			var explanations := {
				"max_depth": "max_depth：树的最大深度必须为正整数，或用 null 表示不限制。",
				"min_samples_leaf": "min_samples_leaf：叶节点最少样本数使用正整数；样本比例应为 (0, 1) 内的小数。",
				"n_neighbors": "n_neighbors：邻居数必须是正整数，且不能超过每个内层训练折的样本数。",
				"n_estimators": "n_estimators：基学习器数量必须是正整数。",
			}
			for parameter in explanations:
				if parameter in detail:
					localized += "\n" + explanations[parameter]
		elif "at least n_splits unique groups" in detail:
			localized += "\n独立组数少于外层折数。请降低折数，或核对分组列是否选错。"
		elif "group" in detail.to_lower():
			localized += "\n请检查分组列是否有缺失、独立组数是否足够，以及每折的类别分布。"
		elif "class" in detail.to_lower() or "split" in detail.to_lower():
			localized += "\n请检查目标类别及每类样本数，必要时减少折数。"
		elif "output" in detail.to_lower():
			localized += "\n请检查输出路径和写入权限，使用新的结果目录。"
	_show_error(localized + ("\n" + detail if not detail.is_empty() else ""))


func _localized_warning(warning: String) -> String:
	# Independent-result warnings carry their validation identifier as a prefix.
	var prefix_end := warning.find("] ")
	if warning.begins_with("[") and prefix_end > 1:
		var strategy := warning.substr(1, prefix_end - 1)
		return "[" + _validation_display(strategy) + "] " + _localized_warning(warning.substr(prefix_end + 2))
	if warning.begins_with("Primary metrics evaluate the nested"):
		return tr("WARN_NESTED_SELECTION")
	if warning.begins_with("Model-family selection"):
		return tr("WARN_MODEL_SELECTION")
	if warning.begins_with("Dropped "):
		var count := warning.get_slice(" ", 1).to_int()
		if warning.contains("with missing target values"):
			return tr("WARN_TARGET_DROPPED") % count
		if warning.contains("because missing_strategy='drop'"):
			return tr("WARN_DROPPED") % count
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
	warnings_text.text = tr("NO_WARNINGS") if warning_lines.is_empty() else "\n".join(warning_lines)


func _new_run_folder() -> String:
	return "run_" + Time.get_datetime_string_from_system().replace(":", "-") + "_%d" % Time.get_ticks_usec()


func _bind_feedback_controls() -> void:
	var icon_image := Image.new()
	icon_image.load_svg_from_string('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect x="2" y="2" width="16" height="16" rx="3" fill="white" stroke="#626977"/></svg>')
	unchecked_icon = ImageTexture.create_from_image(icon_image)
	icon_image = Image.new()
	icon_image.load_svg_from_string('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect x="2" y="2" width="16" height="16" rx="3" fill="#5261c9"/><path d="M5 10 L9 14 L15 6" stroke="white" fill="none" stroke-width="2"/></svg>')
	checked_icon = ImageTexture.create_from_image(icon_image)
	var parent := %PrimaryValidationHelp.get_parent()
	primary_validation_option = OptionButton.new()
	primary_validation_option.fit_to_longest_item = false
	primary_validation_option.clip_text = true
	parent.add_child(primary_validation_option)
	primary_validation_option.item_selected.connect(func(_index): _refresh_review())
	figure_choices = VBoxContainer.new()
	parameter_editor.get_parent().add_child(figure_choices)
	sample_data_button = Button.new()
	translated_controls.append({"node": sample_data_button, "key": "SAMPLE_DATA"})
	browse_button.get_parent().add_child(sample_data_button)
	sample_data_button.pressed.connect(func():
		file_dialog.current_dir = CoreBridge.examples_directory()
		file_dialog.popup_centered_ratio(0.8)
	)
	copy_error_button = Button.new()
	translated_controls.append({"node": copy_error_button, "key": "COPY_ERROR"})
	status_label.get_parent().get_parent().add_child(copy_error_button)
	copy_error_button.pressed.connect(func(): DisplayServer.clipboard_set(status_detail))
	copy_error_button.hide()
	error_details = TextEdit.new()
	error_details.editable = false
	error_details.custom_minimum_size.y = 150
	error_details.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	copy_error_button.get_parent().add_child(error_details)
	error_details.hide()
	figure_option = OptionButton.new()
	figure_view.get_parent().add_child(figure_option)
	figure_view.get_parent().move_child(figure_option, figure_view.get_index())
	figure_option.item_selected.connect(_show_selected_figure)
	validation_result_option = OptionButton.new()
	validation_result_option.fit_to_longest_item = false
	validation_result_option.clip_text = true
	validation_result_option.custom_minimum_size.y = 42
	var result_content := best_result_label.get_parent()
	result_content.add_child(validation_result_option)
	result_content.move_child(validation_result_option, 0)
	validation_result_option.item_selected.connect(_on_validation_result_selected)
	validation_result_option.hide()
	_configure_readable_controls(self)


func _configure_readable_controls(node: Node) -> void:
	if node is ScrollContainer or node is Tree or node is ItemList or node is TextEdit or (node is RichTextLabel and node.scroll_active):
		# Consume wheel events even at a nested scroller's boundary.
		node.mouse_force_pass_scroll_events = false
	if node is ScrollContainer:
		node.gui_input.connect(_stop_scroll_chaining.bind(node))
	if node is RichTextLabel:
		node.selection_enabled = true
		if not node.scroll_active:
			node.mouse_filter = Control.MOUSE_FILTER_PASS
			node.mouse_force_pass_scroll_events = true
	if node is Label:
		node.mouse_filter = Control.MOUSE_FILTER_PASS
		node.tooltip_text = tr("COPY_TEXT_HINT")
		node.gui_input.connect(func(event):
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				DisplayServer.clipboard_set(node.text)
		)
	if node is Tree:
		node.tooltip_text = tr("COPY_ROW_HINT")
		node.gui_input.connect(func(event):
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				var row = node.get_selected()
				if row != null:
					var values := PackedStringArray()
					for column in range(node.columns):
						values.append(row.get_text(column))
					DisplayServer.clipboard_set("\t".join(values))
		)
	for child in node.get_children():
		_configure_readable_controls(child)


func _update_checks() -> void:
	if checked_icon == null:
		return
	for list_control in [feature_list, model_list, validation_list]:
		for index in range(list_control.item_count):
			list_control.set_item_icon(index, checked_icon if list_control.is_selected(index) else unchecked_icon)


func _update_primary_validation() -> void:
	if primary_validation_option == null:
		return
	var previous = "__initial__"
	if primary_validation_option.selected >= 0:
		previous = primary_validation_option.get_item_metadata(primary_validation_option.selected)
	primary_validation_option.clear()
	primary_validation_option.add_item(tr("NO_PRIMARY_VALIDATION"))
	primary_validation_option.set_item_metadata(0, null)
	for value in _selected_values(validation_list):
		primary_validation_option.add_item(tr("PRIMARY_VALIDATION") + ": " + _validation_display(value))
		var index := primary_validation_option.item_count - 1
		primary_validation_option.set_item_metadata(index, value)
		if value == previous:
			primary_validation_option.select(index)
	if previous != null and primary_validation_option.selected == 0 and primary_validation_option.item_count > 1:
		primary_validation_option.select(1)


func _populate_figures() -> void:
	if figure_choices == null:
		return
	for child in figure_choices.get_children():
		figure_choices.remove_child(child)
		child.queue_free()
	var task: String = task_option.get_item_metadata(task_option.selected)
	var choices := ["confusion_matrix", "class_distribution"] if task == "classification" else ["observed_vs_predicted", "residuals", "residual_distribution"]
	var heading := Label.new()
	heading.text = tr("OUTPUT_FIGURES")
	figure_choices.add_child(heading)
	for key in choices:
		var checkbox := CheckBox.new()
		checkbox.text = tr("FIGURE_" + str(key).to_upper())
		checkbox.set_meta("figure", key)
		checkbox.button_pressed = true
		figure_choices.add_child(checkbox)
		checkbox.toggled.connect(func(_value): _refresh_review())


func _selected_figures() -> Array[String]:
	var figures: Array[String] = []
	if figure_choices != null:
		for child in figure_choices.get_children():
			if child is CheckBox and child.button_pressed:
				figures.append(child.get_meta("figure"))
	return figures


func _show_selected_figure(index: int) -> void:
	var image := Image.load_from_file(last_result_dir.path_join(figure_option.get_item_metadata(index)))
	if image != null and not image.is_empty():
		figure_view.texture = ImageTexture.create_from_image(image)


func _stop_scroll_chaining(event: InputEvent, control: Control) -> void:
	var wheel: bool = event is InputEventMouseButton and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN, MOUSE_BUTTON_WHEEL_LEFT, MOUSE_BUTTON_WHEEL_RIGHT]
	if not wheel and not event is InputEventPanGesture:
		return
	var point: Vector2 = control.get_global_transform() * event.position
	# Internal title buttons/scrollbars may still forward events. Only suppress
	# the ancestor's response; retain native scrolling in the nested widget.
	for child in control.find_children("*", "Control", true, false):
		if not (child is Tree or child is ItemList or child is ScrollContainer or child is TextEdit or (child is RichTextLabel and child.scroll_active)):
			continue
		if not child.is_visible_in_tree() or not child.get_global_rect().has_point(point):
			continue
		var ancestor: Node = child.get_parent()
		var clipped := false
		while ancestor is Control and ancestor != control:
			if ancestor.clip_contents and not ancestor.get_global_rect().has_point(point):
				clipped = true
				break
			ancestor = ancestor.get_parent()
		if not clipped:
			control.accept_event()
			return


func _clear_result_tables() -> void:
	for tree in [comparison_tree, metrics_tree, predictions_tree]:
		tree.clear()
	figure_view.texture = null
	figure_option.clear()
	figure_option.hide()


func _load_independent_results(parsed: Dictionary, previous_validation) -> void:
	_clear_result_tables()
	validation_result_entries = parsed.get("validation_results", {})
	validation_result_option.clear()
	validation_result_option.add_item(tr("CHOOSE_VALIDATION_RESULT"))
	validation_result_option.set_item_metadata(0, null)
	for validation in validation_result_entries:
		var entry: Dictionary = validation_result_entries[validation]
		var label := _validation_display(validation)
		if entry.get("status", "") == "failed":
			label += " — " + tr("VALIDATION_FAILED")
		validation_result_option.add_item(label)
		var index := validation_result_option.item_count - 1
		validation_result_option.set_item_metadata(index, validation)
		if validation == previous_validation:
			validation_result_option.select(index)
	validation_result_option.show()
	no_results_label.hide()
	open_results_button.disabled = false
	best_result_label.text = tr("INDEPENDENT_RESULTS")
	if parsed.get("status", "") == "completed_with_errors":
		best_result_label.text += "\n" + tr("PARTIAL_VALIDATION_RESULTS")
	last_warnings = parsed.get("warnings", [])
	_render_warnings()
	if validation_result_option.selected > 0:
		_on_validation_result_selected(validation_result_option.selected)


func _on_validation_result_selected(index: int) -> void:
	var validation = validation_result_option.get_item_metadata(index)
	if validation == null:
		_load_results(last_result_path, false)
		return
	var entry: Dictionary = validation_result_entries[validation]
	if entry.get("status", "") == "completed":
		_load_results(last_result_path.get_base_dir().path_join(entry.result_path), false, true)
	else:
		_clear_result_tables()
		last_result_dir = last_result_path.get_base_dir().path_join("validations").path_join(validation)
		best_result_label.text = _validation_display(validation) + " — " + tr("VALIDATION_FAILED")
		last_warnings = [str(entry.get("error", {}).get("message", ""))]
		_render_warnings()
