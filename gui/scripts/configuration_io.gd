extends RefCounted

var main: Control
var import_button: Button
var save_button: Button
var import_dialog: FileDialog
var save_dialog: FileDialog
var relink_dialog: FileDialog
var seed: SpinBox
var test_fraction: SpinBox
var data_hash: CheckBox
var fixed_parameters: LineEdit
var extra_grids: LineEdit
var notice: Label
var source_path := ""
var model_order: Array = []
var validation_order: Array = []
var feature_order: Array = []


func _init(owner: Control) -> void:
	main = owner
	var row := HBoxContainer.new()
	main.browse_button.get_parent().get_parent().add_child(row)
	import_button = _button(row, "IMPORT_CONFIG")
	save_button = _button(row, "SAVE_CONFIG")
	import_dialog = _dialog(FileDialog.FILE_MODE_OPEN_FILE, PackedStringArray(["*.json ; JSON"]))
	save_dialog = _dialog(FileDialog.FILE_MODE_SAVE_FILE, PackedStringArray(["*.json ; JSON"]))
	relink_dialog = _dialog(FileDialog.FILE_MODE_OPEN_FILE, main.file_dialog.filters)
	import_button.pressed.connect(func():
		import_dialog.title = main.tr("IMPORT_CONFIG")
		import_dialog.current_dir = CoreBridge.examples_directory()
		import_dialog.popup_centered_ratio(0.8))
	save_button.pressed.connect(func():
		save_dialog.title = main.tr("SAVE_CONFIG")
		save_dialog.current_file = "analysis_config.json"
		save_dialog.popup_centered_ratio(0.8))
	import_dialog.file_selected.connect(import_file)
	save_dialog.file_selected.connect(save_file)
	relink_dialog.file_selected.connect(func(path): import_file(source_path, path))
	notice = Label.new()
	notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	row.get_parent().add_child(notice)
	main.translated_controls.append({"node": notice, "key": "CONFIG_IO_HELP"})
	var grid := GridContainer.new()
	grid.columns = 2
	main.parameter_editor.get_parent().add_child(grid)
	_label(grid, "TEST_FRACTION")
	test_fraction = _spin(grid, 0.000000001, 0.999999999, 0, 0.2)
	test_fraction.allow_lesser = true
	test_fraction.allow_greater = true
	_label(grid, "RANDOM_SEED")
	seed = _spin(grid, 0, 4294967295, 1, 42)
	_label(grid, "DATA_HASH")
	data_hash = CheckBox.new()
	data_hash.button_pressed = true
	grid.add_child(data_hash)
	data_hash.toggled.connect(func(_value): main._refresh_review())
	_label(grid, "FIXED_PARAMETERS")
	fixed_parameters = _json_field(grid)
	_label(grid, "EXTRA_GRIDS")
	extra_grids = _json_field(grid)
	var help := Label.new()
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	grid.get_parent().add_child(help)
	main.translated_controls.append({"node": help, "key": "ADVANCED_CONFIG_HELP"})


func _button(parent: Node, key: String) -> Button:
	var button := Button.new()
	parent.add_child(button)
	main.translated_controls.append({"node": button, "key": key})
	return button


func _label(parent: Node, key: String) -> void:
	var label := Label.new()
	label.custom_minimum_size.x = 120
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	main.translated_controls.append({"node": label, "key": key})


func _spin(parent: Node, minimum: float, maximum: float, step_value: float, initial: float) -> SpinBox:
	var control := SpinBox.new()
	control.min_value = minimum
	control.max_value = maximum
	control.step = step_value
	control.value = initial
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(control)
	control.value_changed.connect(func(_value): main._refresh_review())
	return control


func _json_field(parent: Node) -> LineEdit:
	var control := LineEdit.new()
	control.text = "{}"
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	control.custom_minimum_size.x = 180
	parent.add_child(control)
	control.text_changed.connect(func(_value): main._refresh_review())
	return control


func _dialog(mode: FileDialog.FileMode, filters: PackedStringArray) -> FileDialog:
	var dialog := FileDialog.new()
	dialog.access = FileDialog.ACCESS_FILESYSTEM
	dialog.file_mode = mode
	dialog.filters = filters
	main.add_child(dialog)
	return dialog


func import_file(path: String, data_override := "") -> bool:
	if main.is_analysis_running or main.is_preview_loading:
		return false
	var arguments := PackedStringArray(["import-config", "--config", path])
	if not data_override.is_empty():
		arguments.append_array(["--input", data_override])
	var response: Dictionary = main.bridge.execute_json_sync(arguments)
	if response.has("error"):
		main._show_core_error(response.error)
		return false
	if response.get("needs_data", false):
		source_path = path
		relink_dialog.title = main.tr("RELINK_DATA")
		relink_dialog.current_dir = path.get_base_dir()
		relink_dialog.popup_centered_ratio(0.8)
		return false
	apply_configuration(response.config, response.preview)
	return true


func choose(option: OptionButton, value) -> void:
	for index in range(option.item_count):
		if option.get_item_metadata(index) == value:
			option.select(index)
			return


func select_values(list: ItemList, values: Array) -> void:
	list.deselect_all()
	for index in range(list.item_count):
		if list.get_item_metadata(index) in values:
			list.select(index, false)


func ordered(values: Array, previous: Array) -> Array:
	var result: Array = []
	for value in previous:
		if value in values:
			result.append(value)
	for value in values:
		if not value in result:
			result.append(value)
	return result


func apply_configuration(config: Dictionary, preview: Dictionary) -> void:
	main._clear_results()
	choose(main.task_option, config.task)
	main._on_task_changed()
	main.data_path_edit.text = config.input_path
	main.pending_preview_path = config.input_path
	main._on_preview_ready(preview)
	choose(main.target_option, config.target_column)
	choose(main.group_option, config.group_column)
	main._on_column_role_changed()
	var features: Array = config.feature_columns if config.feature_columns != null else []
	if config.feature_columns == null:
		for column in preview.columns:
			if column.name != config.target_column and column.name != config.group_column:
				features.append(column.name)
	feature_order = features.duplicate()
	select_values(main.feature_list, features)
	model_order = config.model_names.duplicate()
	validation_order = config.validation_strategies.duplicate()
	select_values(main.model_list, model_order)
	select_values(main.validation_list, validation_order)
	main._update_primary_validation()
	choose(main.primary_validation_option, config.primary_validation)
	choose(main.missing_option, config.missing_strategy)
	choose(main.scaling_option, config.scaling)
	choose(main.tuning_option, "tuning_" + config.tuning_mode)
	if config.selection_metric != null:
		choose(main.selection_metric_option, config.selection_metric)
	seed.value = config.random_seed
	test_fraction.value = config.test_size
	data_hash.button_pressed = config.include_data_hash
	main.folds_spin.max_value = max(main.folds_spin.max_value, config.n_splits)
	main.folds_spin.value = config.n_splits
	main.inner_folds_spin.max_value = max(main.inner_folds_spin.max_value, config.inner_splits)
	main.inner_folds_spin.value = config.inner_splits
	main.max_candidates_spin.value = config.max_candidates
	fixed_parameters.text = JSON.stringify(config.model_params)
	extra_grids.text = "{}"
	main.parameter_controls.clear()
	main.saved_parameter_values.clear()
	main._populate_parameter_editor()
	var extras: Dictionary = config.parameter_grids.duplicate(true)
	for key in main.parameter_controls:
		var parts: PackedStringArray = str(key).split("::")
		var controls: Dictionary = main.parameter_controls[key]
		controls.enabled.button_pressed = config.parameter_grids.get(parts[0], {}).has(parts[1])
		if controls.enabled.button_pressed:
			controls.values.text = JSON.stringify(config.parameter_grids[parts[0]][parts[1]])
			if config.tuning_mode == "custom":
				extras[parts[0]].erase(parts[1])
	for model in extras.keys():
		if extras[model].is_empty():
			extras.erase(model)
	extra_grids.text = JSON.stringify(extras)
	var figures: Array = config.figure_types if config.figure_types != null else ["confusion_matrix" if config.task == "classification" else "observed_vs_predicted"]
	for child in main.figure_choices.get_children():
		if child is CheckBox:
			child.button_pressed = child.get_meta("figure") in figures
	# Results always use a new local folder, avoiding overwrites or foreign-machine paths.
	main.run_folder_name = ""
	main._refresh_review()
	main.tabs.current_tab = 0


func enrich(config: Dictionary) -> Dictionary:
	if test_fraction.value <= 0 or test_fraction.value >= 1:
		return {"error": main.tr("TEST_FRACTION") + " : 0 < x < 1"}
	var params = JSON.parse_string(fixed_parameters.text)
	var extras = JSON.parse_string(extra_grids.text)
	if not params is Dictionary or not extras is Dictionary:
		return {"error": main.tr("INVALID_JSON_OBJECT")}
	config.model_params = params
	for model in extras:
		if not model in config.model_names or not extras[model] is Dictionary:
			return {"error": main.tr("INVALID_JSON_OBJECT")}
		if not config.parameter_grids.has(model):
			config.parameter_grids[model] = {}
		for parameter in extras[model]:
			var values = extras[model][parameter]
			if not values is Array or values.is_empty():
				return {"error": main.tr("INVALID_JSON_OBJECT")}
			config.parameter_grids[model][parameter] = values
	config.random_seed = int(seed.value)
	config.test_size = test_fraction.value
	config.include_data_hash = data_hash.button_pressed
	config.model_names = ordered(config.model_names, model_order)
	config.model_name = config.model_names[0]
	config.validation_strategies = ordered(config.validation_strategies, validation_order)
	config.validation_strategy = config.validation_strategies[0]
	config.feature_columns = ordered(config.feature_columns, feature_order)
	return config


func save_file(path: String) -> bool:
	var config: Dictionary = main._build_config()
	if config.has("error"):
		main._show_error(config.error)
		return false
	# Relative data paths make adjacent data/config files transferable together.
	if path.get_base_dir() == str(config.input_path).get_base_dir():
		config.input_path = str(config.input_path).get_file()
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		main._show_error(main.tr("CONFIG_SAVE_FAILED"))
		return false
	file.store_string(JSON.stringify(config, "  "))
	file.close()
	return true


func set_enabled(enabled: bool) -> void:
	for control in [import_button, save_button, seed, test_fraction, data_hash, fixed_parameters, extra_grids]:
		main._set_control_interactive(control, enabled)
