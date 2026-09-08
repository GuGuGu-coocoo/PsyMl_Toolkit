extends Node
## Local inference UI; the core owns schema validation and prediction semantics.

const DataPreview = preload("res://scripts/data_preview.gd")
var main: Control
var bridge: CoreBridge
var page: ScrollContainer
var model_button: Button
var data_button: Button
var predict_button: Button
var export_button: Button
var trust: CheckBox
var model_path_label: Label
var data_path_label: Label
var model_info: TextEdit
var required_tree: Tree
var variables_tree: Tree
var sample_tree: Tree
var result_tree: Tree
var summary: Label
var result_summary: Label
var status: Label
var mapping_toggle: Button
var mapping_box: VBoxContainer
var mapping_options: Array[OptionButton] = []
var mapping_confirm: Button
var model_dialog: FileDialog
var data_dialog: FileDialog
var export_dialog: FileDialog
var model_path := ""
var input_path := ""
var metadata: Dictionary = {}
var model_notices: Array = []
var data: Dictionary = {}
var predictions: Dictionary = {}
var compatibility: Dictionary = {}
var mapping: Array[String] = []
var result_path := ""
var default_suffix := ".xlsx"
var operation := ""
var busy := false
var error_message := ""
var export_path := ""


func build(owner: Control) -> void:
	main = owner
	bridge = CoreBridge.new()
	add_child(bridge)
	bridge.response_ready.connect(_response)
	page = ScrollContainer.new()
	page.name = "ModelPrediction"
	page.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	main.tabs.add_child(page)
	var margin := MarginContainer.new()
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 20)
	page.add_child(margin)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	margin.add_child(content)
	label(content, "PREDICTION_HEADING").add_theme_font_size_override("font_size", 24)
	label(content, "PREDICTION_HELP")
	trust = CheckBox.new()
	content.add_child(trust)
	main.translated_controls.append({"node": trust, "key": "TRUST_MODEL"})
	trust.toggled.connect(func(value):
		if not value:
			model_path = ""
			metadata = {}
			compatibility = {}
			_clear_predictions()
		refresh_language())
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 20)
	content.add_child(columns)
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(left)
	columns.add_child(right)
	model_button = button(left, "LOAD_MODEL")
	model_path_label = label(left, "NO_MODEL")
	label(left, "MODEL_INFORMATION")
	model_info = TextEdit.new()
	model_info.editable = false
	model_info.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	model_info.custom_minimum_size.y = 190
	left.add_child(model_info)
	label(left, "REQUIRED_FEATURES")
	required_tree = tree(left, 145)
	required_tree.columns = 3
	mapping_toggle = button(left, "MANUAL_MAPPING")
	mapping_toggle.toggle_mode = true
	mapping_box = VBoxContainer.new()
	left.add_child(mapping_box)
	mapping_box.hide()
	mapping_toggle.toggled.connect(func(value): mapping_box.visible = value)
	data_button = button(right, "LOAD_PREDICTION_DATA")
	data_path_label = label(right, "NO_DATA")
	summary = label(right, "NO_DATA")
	variables_tree = tree(right, 145)
	label(right, "SAMPLE")
	sample_tree = tree(right, 170)
	status = label(content, "PREDICTION_WAITING")
	var actions := HBoxContainer.new()
	content.add_child(actions)
	predict_button = button(actions, "RUN_PREDICTION")
	export_button = button(actions, "EXPORT_PREDICTION")
	result_summary = label(content, "PREDICTION_RESULTS")
	result_tree = tree(content, 180)
	label(content, "PREDICTION_SCIENCE")
	model_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_FILE, PackedStringArray(["*.joblib,*.pkl ; sklearn / joblib"]))
	data_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_FILE, main.file_dialog.filters)
	export_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_SAVE_FILE, PackedStringArray())
	model_button.pressed.connect(func():
		model_dialog.title = tr("LOAD_MODEL")
		model_dialog.popup_centered_ratio(0.8))
	data_button.pressed.connect(func():
		data_dialog.title = tr("LOAD_PREDICTION_DATA")
		data_dialog.popup_centered_ratio(0.8))
	model_dialog.file_selected.connect(load_model)
	data_dialog.file_selected.connect(load_data)
	predict_button.pressed.connect(run_prediction)
	export_button.pressed.connect(_choose_export)
	export_dialog.file_selected.connect(export_predictions)
	main._configure_readable_controls(page)


func label(parent: Node, key: String) -> Label:
	var control := Label.new()
	control.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(control)
	main.translated_controls.append({"node": control, "key": key})
	return control


func button(parent: Node, key: String) -> Button:
	var control := Button.new()
	parent.add_child(control)
	main.translated_controls.append({"node": control, "key": key})
	return control


func tree(parent: Node, height: int) -> Tree:
	var control := Tree.new()
	control.hide_root = true
	control.column_titles_visible = true
	control.custom_minimum_size.y = height
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(control)
	return control


func _request(kind: String, arguments: PackedStringArray) -> void:
	operation = kind
	busy = true
	error_message = ""
	refresh_language()
	bridge.request_json(arguments)


func load_model(path: String) -> void:
	if busy or not trust.button_pressed:
		return
	model_path = path
	metadata = {}
	model_notices = []
	compatibility = {}
	mapping.clear()
	_clear_predictions()
	_request("model", PackedStringArray(["model-info", "--model", path, "--trust-model"]))


func load_data(path: String) -> void:
	if busy:
		return
	input_path = path
	data = {}
	compatibility = {}
	mapping.clear()
	_clear_predictions()
	_request("data", PackedStringArray(["preview", "--input", path, "--include-sample"]))


func _arguments() -> PackedStringArray:
	var args := PackedStringArray(["predict", "--model", model_path, "--input", input_path, "--trust-model"])
	for name in mapping:
		args.append_array(["--feature", name])
	return args


func _check() -> void:
	if metadata.is_empty() or data.is_empty():
		refresh_language()
		return
	compatibility = {}
	var args := _arguments()
	args.append("--check-only")
	_request("check", args)


func _response(payload: Dictionary) -> void:
	busy = false
	if payload.has("error"):
		error_message = str(payload.error.get("message", tr("PREDICTION_FAILED")))
		if operation in ["model", "check", "predict"]:
			compatibility = {}
		refresh_language()
		return
	match operation:
		"model":
			metadata = payload.model
			model_notices = payload.get("warnings", [])
			_build_mapping()
			_check()
		"data":
			data = payload
			_build_mapping()
			_check()
		"check":
			metadata = payload.model
			model_notices = payload.get("warnings", [])
			data = payload.preview
			compatibility = payload.compatibility
			default_suffix = payload.default_output_suffix
		"predict":
			metadata = payload.model
			model_notices = payload.get("warnings", [])
			data = payload.preview
			compatibility = payload.compatibility
			predictions = payload.predictions
			result_path = payload.output_path
		"export":
			export_path = payload.output_path
	refresh_language()


func run_prediction() -> void:
	if busy or not compatibility.get("compatible", false) or not trust.button_pressed:
		return
	_clear_predictions()
	var directory := ProjectSettings.globalize_path("user://prediction")
	DirAccess.make_dir_recursive_absolute(directory)
	result_path = directory.path_join("prediction_%d_%d.parquet" % [OS.get_process_id(), Time.get_ticks_usec()])
	var args := _arguments()
	args.append_array(["--output", result_path])
	_request("predict", args)


func _build_mapping() -> void:
	mapping_toggle.visible = not metadata.is_empty() and metadata.get("feature_names", []).is_empty()
	for child in mapping_box.get_children():
		child.queue_free()
	mapping_options.clear()
	if not mapping_toggle.visible or data.is_empty():
		mapping_box.hide()
		mapping_toggle.button_pressed = false
		return
	for index in range(int(metadata.n_features)):
		var option := OptionButton.new()
		option.fit_to_longest_item = false
		option.add_item("%d —" % (index + 1))
		option.set_item_metadata(0, "")
		for column in data.columns:
			option.add_item("%d  %s" % [index + 1, column.name])
			option.set_item_metadata(option.item_count - 1, column.name)
		mapping_box.add_child(option)
		mapping_options.append(option)
		option.item_selected.connect(func(_index):
			mapping.clear()
			compatibility = {}
			_clear_predictions()
			refresh_language())
	mapping_confirm = Button.new()
	mapping_confirm.text = tr("CONFIRM_MAPPING")
	mapping_box.add_child(mapping_confirm)
	mapping_confirm.pressed.connect(confirm_mapping)


func confirm_mapping() -> void:
	if busy:
		return
	mapping.clear()
	for option in mapping_options:
		mapping.append(str(option.get_item_metadata(option.selected)))
	_clear_predictions()
	_check()


func _choose_export() -> void:
	if busy or predictions.is_empty():
		return
	var filters := PackedStringArray()
	var formats: Array = main.capabilities.get("output_formats", [".csv", ".xlsx", ".parquet"])
	filters.append("*%s ; %s" % [default_suffix, default_suffix.trim_prefix(".").to_upper()])
	for suffix in formats:
		if suffix != default_suffix:
			filters.append("*%s ; %s" % [suffix, str(suffix).trim_prefix(".").to_upper()])
	export_dialog.filters = filters
	export_dialog.title = tr("EXPORT_PREDICTION")
	export_dialog.current_dir = input_path.get_base_dir()
	export_dialog.current_file = input_path.get_file().get_basename() + "_predictions" + default_suffix
	export_dialog.popup_centered_ratio(0.8)


func export_predictions(path: String) -> void:
	if busy or predictions.is_empty():
		return
	if path in [input_path, model_path, model_path.get_base_dir().path_join("model_metadata.json")]:
		error_message = tr("PRESERVE_SOURCE")
		refresh_language()
		return
	# The native Save As dialog confirms replacement of an existing destination.
	_request("export", PackedStringArray(["export-table", "--input", result_path, "--output", path, "--overwrite"]))


func _clear_predictions() -> void:
	if not result_path.is_empty():
		DirAccess.remove_absolute(result_path)
	result_path = ""
	export_path = ""
	predictions = {}


func refresh_language() -> void:
	main.tabs.set_tab_title(4, tr("TAB_PREDICTION"))
	model_button.disabled = busy or not trust.button_pressed
	trust.disabled = busy
	data_button.disabled = busy
	predict_button.disabled = busy or not trust.button_pressed or not compatibility.get("compatible", false)
	export_button.disabled = busy or predictions.is_empty()
	for option in mapping_options:
		option.disabled = busy
	if is_instance_valid(mapping_confirm):
		mapping_confirm.disabled = busy
		mapping_confirm.text = tr("CONFIRM_MAPPING")
	mapping_toggle.visible = not metadata.is_empty() and metadata.get("feature_names", []).is_empty()
	if not mapping_toggle.visible:
		mapping_box.hide()
	model_path_label.tooltip_text = model_path
	model_path_label.text = model_path.get_file() if not model_path.is_empty() else tr("NO_MODEL")
	data_path_label.tooltip_text = input_path
	data_path_label.text = input_path.get_file() if not input_path.is_empty() else tr("NO_DATA")
	summary.text = tr("DATA_SUMMARY") % [data.row_count, data.column_count] if not data.is_empty() else tr("NO_DATA")
	DataPreview.variables(variables_tree, data.get("columns", []))
	DataPreview.sample(sample_tree, data.get("sample", []), data.get("columns", []))
	DataPreview.sample(result_tree, predictions.get("sample", []), predictions.get("columns", []))
	for index in range(result_tree.columns):
		result_tree.set_column_custom_minimum_width(index, maxi(120, result_tree.get_column_title(index).length() * 8 + 20))
	result_summary.text = tr("PREDICTION_RESULTS")
	if not predictions.is_empty():
		result_summary.text += " · " + tr("DATA_SUMMARY") % [predictions.row_count, predictions.column_count]
	model_info.text = ""
	if not metadata.is_empty():
		for pair in [["TASK", "task"], ["PREDICTION_MODEL", "model_name"], ["ESTIMATOR", "estimator_class"], ["PIPELINE_STEPS", "pipeline_steps"], ["PREDICTOR_COUNT", "n_features"], ["TARGET", "target_column"], ["CLASSES", "classes"], ["SUPPORTS_PROBABILITY", "supports_probability"], ["PSYML_VERSION", "psyml_version"], ["SKLEARN_VERSION", "sklearn_version"], ["CREATED_TIME", "created_time"], ["SELECTION_METRIC", "selection_metric"], ["MODEL_PARAMETERS", "best_parameters"]]:
			var value = metadata.get(pair[1], null)
			var display := tr("UNAVAILABLE") if value == null else str(value)
			if pair[1] == "task":
				display = tr(str(value).to_upper())
			if pair[1] == "n_features":
				display = str(int(value))
			if value is bool:
				display = tr("YES" if value else "NO")
			model_info.text += tr(pair[0]) + ": " + display + "\n"
	required_tree.clear()
	for index in range(3):
		required_tree.set_column_title(index, tr(["COLUMN", "EXPECTED_TYPE", "COMPATIBILITY_STATUS"][index]))
	var root := required_tree.create_item()
	var required: Array = compatibility.get("required_features", [])
	if required.is_empty():
		for name in metadata.get("feature_names", []):
			required.append({"name": name, "expected_type": metadata.get("feature_types", {}).get(name, "unknown"), "status": "waiting"})
	for feature in required:
		var item := required_tree.create_item(root)
		item.set_text(0, feature.name)
		item.set_text(1, tr("FEATURE_TYPE_" + str(feature.expected_type).to_upper()))
		item.set_text(2, tr("CHECK_" + str(feature.status).to_upper()))
	status.text = tr("PREDICTION_BUSY") if busy else tr("PREDICTION_WAITING")
	if not busy:
		if not error_message.is_empty():
			status.text = error_message
		elif not compatibility.is_empty():
			status.text = tr("PREDICTION_COMPATIBLE") if compatibility.compatible else tr("PREDICTION_INCOMPATIBLE")
			for error in compatibility.get("errors", []):
				status.text += "\n" + tr("CHECK_" + str(error.code).to_upper()) + ": " + str(error.get("feature", metadata.get("n_features", "")))
			if input_path.get_extension().to_lower() in ["xls", "sas7bdat"]:
				status.text += "\n" + tr("READONLY_EXPORT")
		if not model_notices.is_empty():
			status.text += "\n" + tr("MODEL_METADATA_FALLBACK")
		if not export_path.is_empty():
			status.text = tr("PREDICTION_EXPORTED") + " " + export_path


func _exit_tree() -> void:
	_clear_predictions()
