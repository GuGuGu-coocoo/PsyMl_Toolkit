extends Node
## Local inference UI; the core owns schema validation and prediction semantics.

const DataPreview = preload("res://scripts/data_preview.gd")
const OutputLocation = preload("res://scripts/output_location.gd")
const EXPLANATION_EXPORT_ORDER := ["csv", "png", "notes", "json"]
var main: Control
var bridge: CoreBridge
var page: ScrollContainer
var output_edit: LineEdit
var output_choose_button: Button
var output_help: Label
var output_dialog: FileDialog
var output_root_sync := false
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
var background_button: Button
var background_label: Label
var background_dialog: FileDialog
var explain_row: SpinBox
var explain_class: OptionButton
var explain_class_box: VBoxContainer
var explain_background_size: SpinBox
var explain_cycles: SpinBox
var explain_button: Button
var explain_cancel_button: Button
var explain_status: Label
var explain_summary: Label
var explain_tree: Tree
var explain_view: TextureRect
var explain_open_button: Button
var explain_folder_button: Button
var explain_export_button: Button
var explain_export_dialog: FileDialog
var background_path := ""
var explain_busy := false
var explanation: Dictionary = {}
var explain_error := ""
var explain_output_dir := ""
var explain_artifacts: Dictionary = {}
var explain_request := 0
var explain_staging_root := ""
var explain_note := ""
const COEFFICIENT_EXPORT_ORDER := ["csv", "notes", "json"]
var coefficients_button: Button
var coefficients_cancel_button: Button
var coefficients_status: Label
var coefficients_summary: Label
var coefficients_outputs: Label
var coefficients_tree: Tree
var coefficients_open_button: Button
var coefficients_export_button: Button
var coefficients_export_dialog: FileDialog
var coefficients_busy := false
var coefficient_report: Dictionary = {}
var coefficients_error := ""
var coefficients_output_dir := ""
var coefficients_artifacts: Dictionary = {}
var coefficients_request := 0
var coefficients_staging_root := ""
var coefficients_note := ""


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
	# Page 4 shares page 2's result root: prediction, SHAP and coefficient
	# artifacts go into new run subfolders under prediction/, explanation/ and
	# coefficients/ inside it. Nothing is inferred from the model location and
	# there is no hidden fallback.
	var output_row := HBoxContainer.new()
	output_row.add_theme_constant_override("separation", 14)
	content.add_child(output_row)
	var output_label: Label = label(output_row, "OUTPUT_FOLDER")
	# Keep the row label on one line like page 2. An autowrapping label has no
	# useful minimum width inside an HBoxContainer and collapses to about one
	# character per line, which also inflates the whole row.
	output_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	output_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	output_edit = LineEdit.new()
	output_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	output_row.add_child(output_edit)
	output_choose_button = button(output_row, "CHOOSE_FOLDER")
	output_help = label(content, "PREDICTION_OUTPUT_HELP")
	output_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_DIR, PackedStringArray())
	output_choose_button.pressed.connect(func():
		output_dialog.title = tr("CHOOSE_FOLDER")
		if not main.output_edit.text.strip_edges().is_empty():
			output_dialog.current_dir = main.output_edit.text.strip_edges()
		output_dialog.popup_centered_ratio(0.8))
	output_dialog.dir_selected.connect(set_output_root)
	output_edit.text_changed.connect(_on_output_edit_changed)
	trust = CheckBox.new()
	content.add_child(trust)
	main.translated_controls.append({"node": trust, "key": "TRUST_MODEL"})
	trust.toggled.connect(func(value):
		if explain_busy:
			return
		if not value:
			model_path = ""
			metadata = {}
			compatibility = {}
			_clear_predictions()
			_clear_explanation()
			_clear_coefficients()
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
	label(content, "EXPLAIN_HEADING").add_theme_font_size_override("font_size", 20)
	label(content, "EXPLAIN_HELP")
	# Background selection gets its own row: a long path label must never share an
	# HBox with the controls, or automatic wrapping collapses it into a column of
	# single characters and stretches the whole page.
	var explain_background_row := HBoxContainer.new()
	explain_background_row.add_theme_constant_override("separation", 14)
	content.add_child(explain_background_row)
	background_button = button(explain_background_row, "LOAD_BACKGROUND")
	background_label = Label.new()
	background_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	background_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	background_label.clip_text = true
	background_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	background_label.custom_minimum_size.x = 220
	explain_background_row.add_child(background_label)
	main.translated_controls.append({"node": background_label, "key": "NO_BACKGROUND"})
	var explain_options := HBoxContainer.new()
	explain_options.add_theme_constant_override("separation", 14)
	content.add_child(explain_options)
	var row_box := VBoxContainer.new()
	explain_options.add_child(row_box)
	label(row_box, "EXPLAIN_ROW")
	explain_row = _spin(row_box, 1, 100000, 1)
	explain_class_box = VBoxContainer.new()
	explain_options.add_child(explain_class_box)
	label(explain_class_box, "EXPLAIN_CLASS")
	explain_class = OptionButton.new()
	explain_class.custom_minimum_size.x = 120
	explain_class_box.add_child(explain_class)
	var size_box := VBoxContainer.new()
	explain_options.add_child(size_box)
	label(size_box, "EXPLAIN_BACKGROUND_SIZE")
	explain_background_size = _spin(size_box, 1, 100, 50)
	var cycles_box := VBoxContainer.new()
	explain_options.add_child(cycles_box)
	label(cycles_box, "EXPLAIN_CYCLES")
	explain_cycles = _spin(cycles_box, 1, 20, 5)
	var explain_actions := HBoxContainer.new()
	content.add_child(explain_actions)
	explain_button = button(explain_actions, "RUN_EXPLANATION")
	explain_cancel_button = button(explain_actions, "CANCEL_EXPLANATION")
	var explain_deliver := HBoxContainer.new()
	explain_deliver.add_theme_constant_override("separation", 14)
	content.add_child(explain_deliver)
	explain_open_button = button(explain_deliver, "OPEN_WATERFALL")
	explain_folder_button = button(explain_deliver, "OPEN_RESULTS_FOLDER")
	explain_export_button = button(explain_deliver, "EXPORT_EXPLANATION")
	explain_status = label(content, "EXPLAIN_WAITING")
	explain_summary = label(content, "EXPLAIN_RESULTS")
	explain_view = TextureRect.new()
	explain_view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	explain_view.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	explain_view.custom_minimum_size.y = 220
	explain_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	explain_view.hide()
	content.add_child(explain_view)
	explain_tree = tree(content, 200)
	explain_tree.columns = 4
	label(content, "EXPLAIN_SCIENCE")
	label(content, "COEFFICIENTS_HEADING").add_theme_font_size_override("font_size", 20)
	label(content, "COEFFICIENTS_HELP")
	var coefficients_actions := HBoxContainer.new()
	content.add_child(coefficients_actions)
	coefficients_button = button(coefficients_actions, "RUN_COEFFICIENTS")
	coefficients_cancel_button = button(coefficients_actions, "CANCEL_COEFFICIENTS")
	var coefficients_deliver := HBoxContainer.new()
	coefficients_deliver.add_theme_constant_override("separation", 14)
	content.add_child(coefficients_deliver)
	coefficients_open_button = button(coefficients_deliver, "OPEN_COEFFICIENTS_FOLDER")
	coefficients_export_button = button(coefficients_deliver, "EXPORT_COEFFICIENTS")
	coefficients_status = label(content, "COEFFICIENTS_WAITING")
	coefficients_summary = label(content, "COEFFICIENTS_RESULTS")
	coefficients_outputs = label(content, "COEFFICIENTS_OUTPUTS")
	coefficients_tree = tree(content, 200)
	coefficients_tree.columns = 4
	label(content, "COEFFICIENTS_SCIENCE")
	model_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_FILE, PackedStringArray(["*.joblib,*.pkl ; sklearn / joblib"]))
	data_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_FILE, main.file_dialog.filters)
	export_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_SAVE_FILE, PackedStringArray())
	background_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_FILE, main.file_dialog.filters)
	explain_export_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_DIR, PackedStringArray())
	coefficients_export_dialog = main.configuration_io._dialog(FileDialog.FILE_MODE_OPEN_DIR, PackedStringArray())
	model_button.pressed.connect(func():
		model_dialog.title = tr("LOAD_MODEL")
		model_dialog.popup_centered_ratio(0.8))
	data_button.pressed.connect(func():
		data_dialog.title = tr("LOAD_PREDICTION_DATA")
		if input_path.is_empty():
			data_dialog.current_dir = CoreBridge.quickstart_directory()
		data_dialog.popup_centered_ratio(0.8))
	model_dialog.file_selected.connect(load_model)
	data_dialog.file_selected.connect(load_data)
	predict_button.pressed.connect(run_prediction)
	export_button.pressed.connect(_choose_export)
	export_dialog.file_selected.connect(export_predictions)
	background_button.pressed.connect(func():
		background_dialog.title = tr("LOAD_BACKGROUND")
		if background_path.is_empty():
			background_dialog.current_dir = input_path.get_base_dir() if not input_path.is_empty() else CoreBridge.quickstart_directory()
		background_dialog.popup_centered_ratio(0.8))
	background_dialog.file_selected.connect(load_background)
	explain_button.pressed.connect(run_explanation)
	explain_cancel_button.pressed.connect(cancel_explanation)
	explain_open_button.pressed.connect(open_waterfall)
	explain_folder_button.pressed.connect(open_explanation_folder)
	explain_export_button.pressed.connect(_choose_explanation_export)
	explain_export_dialog.dir_selected.connect(export_explanation)
	explain_row.value_changed.connect(func(_value):
		if explain_busy:
			return
		_clear_explanation()
		refresh_language())
	explain_class.item_selected.connect(func(_index):
		if explain_busy:
			return
		_clear_explanation()
		refresh_language())
	explain_background_size.value_changed.connect(func(_value):
		if explain_busy:
			return
		_clear_explanation()
		refresh_language())
	explain_cycles.value_changed.connect(func(_value):
		if explain_busy:
			return
		_clear_explanation()
		refresh_language())
	bridge.explanation_ready.connect(_explanation_response)
	bridge.explanation_failed.connect(_explanation_failed)
	bridge.explanation_cancelled.connect(_explanation_cancelled)
	coefficients_button.pressed.connect(run_coefficients)
	coefficients_cancel_button.pressed.connect(cancel_coefficients)
	coefficients_open_button.pressed.connect(open_coefficients_folder)
	coefficients_export_button.pressed.connect(_choose_coefficients_export)
	coefficients_export_dialog.dir_selected.connect(export_coefficients)
	bridge.coefficients_ready.connect(_coefficients_response)
	bridge.coefficients_failed.connect(_coefficients_failed)
	bridge.coefficients_cancelled.connect(_coefficients_cancelled)
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


func _spin(parent: Node, minimum: int, maximum: int, value: int) -> SpinBox:
	var control := SpinBox.new()
	control.min_value = minimum
	control.max_value = maximum
	control.step = 1
	control.value = value
	control.custom_minimum_size.x = 90
	parent.add_child(control)
	return control


func _request(kind: String, arguments: PackedStringArray) -> void:
	operation = kind
	busy = true
	error_message = ""
	refresh_language()
	bridge.request_json(arguments)


func set_output_root(path: String) -> void:
	# Page 2 and page 4 share one result root; the page-2 setting is the source.
	main.output_edit.text = path
	main._refresh_review()
	sync_output_root()


func sync_output_root() -> void:
	if output_edit == null or main == null or main.output_edit == null:
		return
	if output_edit.text == main.output_edit.text:
		return
	output_root_sync = true
	output_edit.text = main.output_edit.text
	output_root_sync = false


func _on_output_edit_changed(text: String) -> void:
	if output_root_sync:
		return
	main.output_edit.text = text
	main._refresh_review()


func _freeze_output_directory(family: String) -> Dictionary:
	# Resolve and freeze the shared root when the operation starts; a missing or
	# unwritable root is a visible error and never becomes a user:// fallback.
	var root := OutputLocation.shared_root(main)
	if not str(root.error).is_empty():
		return {"path": "", "root": "", "error": tr(str(root.error))}
	var frozen := OutputLocation.create_run_directory(str(root.path), family)
	if not str(frozen.error).is_empty():
		return {"path": "", "root": str(frozen.root), "error": tr(str(frozen.error))}
	return {"path": str(frozen.path), "root": str(frozen.root), "error": ""}


func load_model(path: String) -> void:
	if busy or explain_busy or coefficients_busy or not trust.button_pressed:
		return
	model_path = path
	metadata = {}
	model_notices = []
	compatibility = {}
	mapping.clear()
	_clear_predictions()
	_clear_explanation()
	_clear_coefficients()
	_request("model", PackedStringArray(["model-info", "--model", path, "--trust-model"]))


func load_data(path: String) -> void:
	if busy or explain_busy or coefficients_busy:
		return
	input_path = path
	data = {}
	compatibility = {}
	mapping.clear()
	_clear_predictions()
	_clear_explanation()
	_clear_coefficients()
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
			_build_explanation_classes()
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
			_build_explanation_classes()
		"predict":
			metadata = payload.model
			model_notices = payload.get("warnings", [])
			data = payload.preview
			compatibility = payload.compatibility
			predictions = payload.predictions
			result_path = payload.output_path
			_build_explanation_classes()
		"export":
			export_path = payload.output_path
	refresh_language()


func run_prediction() -> void:
	if busy or explain_busy or coefficients_busy or not compatibility.get("compatible", false) or not trust.button_pressed:
		return
	var frozen := _freeze_output_directory(OutputLocation.PREDICTION)
	if not str(frozen.error).is_empty():
		error_message = str(frozen.error)
		refresh_language()
		return
	_clear_predictions()
	# The frozen run folder is new, so the prediction file never overwrites an
	# earlier run; the file itself stays on disk when the UI is cleared.
	result_path = str(frozen.path).path_join("predictions.parquet")
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
	if busy or explain_busy or coefficients_busy:
		return
	mapping.clear()
	for option in mapping_options:
		mapping.append(str(option.get_item_metadata(option.selected)))
	_clear_predictions()
	_check()


func _choose_export() -> void:
	if busy or explain_busy or coefficients_busy or predictions.is_empty():
		return
	var filters := PackedStringArray()
	var formats: Array = main.capabilities.get("output_formats", [".csv", ".xlsx", ".parquet"])
	filters.append("*%s ; %s" % [default_suffix, default_suffix.trim_prefix(".").to_upper()])
	for suffix in formats:
		if suffix != default_suffix:
			filters.append("*%s ; %s" % [suffix, str(suffix).trim_prefix(".").to_upper()])
	export_dialog.filters = filters
	export_dialog.title = tr("EXPORT_PREDICTION")
	# The dialog opens where the actual artifact lives; explicit Save As stays
	# available and keeps its own overwrite confirmation.
	export_dialog.current_dir = (
		result_path.get_base_dir() if not result_path.is_empty() else input_path.get_base_dir()
	)
	export_dialog.current_file = input_path.get_file().get_basename() + "_predictions" + default_suffix
	export_dialog.popup_centered_ratio(0.8)


func export_predictions(path: String) -> void:
	if busy or explain_busy or coefficients_busy or predictions.is_empty():
		return
	if path in [input_path, model_path, model_path.get_base_dir().path_join("model_metadata.json")]:
		error_message = tr("PRESERVE_SOURCE")
		refresh_language()
		return
	# The native Save As dialog confirms replacement of an existing destination.
	_request("export", PackedStringArray(["export-table", "--input", result_path, "--output", path, "--overwrite"]))


func _clear_predictions() -> void:
	# UI state only: a completed prediction file lives in the selected result
	# root, so changing data/model or retrying never deletes a finished run.
	result_path = ""
	export_path = ""
	predictions = {}


func load_background(path: String) -> void:
	if busy or explain_busy or coefficients_busy:
		return
	background_path = path
	_clear_explanation()
	refresh_language()


func _build_explanation_classes() -> void:
	explain_class.clear()
	var classes: Array = metadata.get("classes") if metadata.get("classes") is Array else []
	for index in range(classes.size()):
		explain_class.add_item(tr("CLASS_INDEX_LABEL") % [index, str(classes[index])])
		explain_class.set_item_metadata(index, index)
	if classes.is_empty():
		explain_class.add_item(tr("UNAVAILABLE"))


func run_explanation() -> void:
	if busy or explain_busy or coefficients_busy or not trust.button_pressed:
		return
	if metadata.is_empty() or input_path.is_empty() or not compatibility.get("compatible", false):
		return
	if background_path.is_empty():
		explain_error = tr("EXPLAIN_BACKGROUND_REQUIRED")
		refresh_language()
		return
	if metadata.get("task") == "classification" and explain_class.selected < 0:
		explain_error = tr("EXPLAIN_CLASS_REQUIRED")
		refresh_language()
		return
	var frozen := _freeze_output_directory(OutputLocation.EXPLANATION)
	if not str(frozen.error).is_empty():
		explain_error = str(frozen.error)
		refresh_language()
		return
	explain_staging_root = str(frozen.root)
	_cleanup_owned_staging()
	_clear_explanation()
	explain_output_dir = str(frozen.path)
	var args := PackedStringArray([
		"explain", "--model", model_path, "--input", input_path,
		"--background", background_path, "--row", str(int(explain_row.value)),
		"--background-size", str(int(explain_background_size.value)),
		"--cycles", str(int(explain_cycles.value)), "--seed", "42",
		"--trust-model", "--output-dir", explain_output_dir])
	for name in mapping:
		args.append_array(["--feature", name])
	if metadata.get("task") == "classification":
		args.append_array(["--class-index", str(int(explain_class.get_item_metadata(explain_class.selected)))])
	explain_busy = true
	explain_error = ""
	refresh_language()
	if not bridge.start_explanation(args):
		explain_busy = false
		refresh_language()
		return
	explain_request = bridge.explanation_generation()


func cancel_explanation() -> void:
	if not explain_busy:
		return
	explain_busy = false
	bridge.cancel_explanation()


func _explanation_response(payload: Dictionary, generation: int) -> void:
	if generation != explain_request:
		return
	explain_busy = false
	if payload.has("error"):
		explain_error = str(payload.error.get("message", tr("EXPLAIN_FAILED")))
		explanation = {}
		explain_artifacts = {}
		refresh_language()
		return
	explanation = payload.get("explanation", {})
	explain_artifacts = payload.get("artifacts", {})
	if payload.get("output_dir"):
		explain_output_dir = str(payload.output_dir)
	if explanation.is_empty():
		explain_error = tr("EXPLAIN_FAILED")
	refresh_language()


func _explanation_failed(error: Dictionary, generation: int) -> void:
	if generation != explain_request:
		return
	explain_busy = false
	explanation = {}
	explain_artifacts = {}
	explain_error = str(error.get("message", tr("EXPLAIN_FAILED")))
	refresh_language()


func _explanation_cancelled(generation: int) -> void:
	if generation != explain_request:
		return
	explain_busy = false
	explanation = {}
	explain_artifacts = {}
	explain_error = tr("EXPLAIN_CANCELLED")
	refresh_language()


func _cleanup_owned_staging() -> void:
	# Remove only this tool's own incomplete staging directories; never touch
	# completed explanation output directories or their artifacts.
	OutputLocation.cleanup_staging(explain_staging_root, OutputLocation.EXPLANATION)


func open_waterfall() -> void:
	var path := str(explain_artifacts.get("png", ""))
	if path.is_empty() or not FileAccess.file_exists(path):
		explain_error = tr("EXPLAIN_NO_ARTIFACT")
		refresh_language()
		return
	OS.shell_open(path)


func open_explanation_folder() -> void:
	if explain_output_dir.is_empty() or not DirAccess.dir_exists_absolute(explain_output_dir):
		explain_error = tr("EXPLAIN_NO_ARTIFACT")
		refresh_language()
		return
	OS.shell_open(explain_output_dir)


func _choose_explanation_export() -> void:
	if explain_artifacts.is_empty():
		explain_error = tr("EXPLAIN_NO_ARTIFACT")
		refresh_language()
		return
	explain_export_dialog.title = tr("EXPORT_EXPLANATION")
	# Point at the actual artifacts; the explicit export still never overwrites.
	if not explain_output_dir.is_empty():
		explain_export_dialog.current_dir = explain_output_dir
	explain_export_dialog.popup_centered_ratio(0.8)


func _explanation_source_dir() -> String:
	for key in EXPLANATION_EXPORT_ORDER:
		if explain_artifacts.has(key):
			return str(explain_artifacts[key]).get_base_dir()
	return ""


func _explanation_file_ready(path: String) -> bool:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return false
	var length := file.get_length()
	file.close()
	return length > 0


func _explanation_directory_empty(path: String) -> bool:
	var directory := DirAccess.open(path)
	if directory == null:
		return false
	return directory.get_files().is_empty() and directory.get_directories().is_empty()


func _explanation_index_matches_at(json_path: String) -> bool:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if typeof(parsed) != TYPE_DICTIONARY:
		return false
	var index = parsed.get("artifacts", {})
	if typeof(index) != TYPE_DICTIONARY:
		return false
	for key in EXPLANATION_EXPORT_ORDER:
		if str(index.get(key, "")) != str(explain_artifacts[key]).get_file():
			return false
	return true


func export_explanation(directory: String) -> void:
	# Delivery is all-or-nothing and never overwrites existing files: the target
	# is a new/empty directory, or a unique new subdirectory of the chosen
	# folder. Every source artifact is checked first, the JSON completion marker
	# is copied last and re-verified, and a failed copy removes only the files it
	# created and reports an error without a success marker.
	explain_error = ""
	explain_note = ""
	if explain_artifacts.is_empty():
		explain_error = tr("EXPLAIN_NO_ARTIFACT")
		refresh_language()
		return
	for key in EXPLANATION_EXPORT_ORDER:
		if not explain_artifacts.has(key) or not _explanation_file_ready(str(explain_artifacts[key])):
			explain_error = tr("EXPLAIN_EXPORT_INCOMPLETE")
			refresh_language()
			return
	var source_dir := _explanation_source_dir().simplify_path()
	var base := directory.simplify_path()
	if source_dir != "" and base == source_dir:
		explain_error = tr("EXPLAIN_EXPORT_SAME_DIR")
		refresh_language()
		return
	var target := base
	var created_target := false
	if not DirAccess.dir_exists_absolute(target):
		DirAccess.make_dir_recursive_absolute(target)
		if not DirAccess.dir_exists_absolute(target):
			explain_error = tr("EXPLAIN_EXPORT_FAILED")
			refresh_language()
			return
		created_target = true
	elif not _explanation_directory_empty(target):
		target = base.path_join("psyml-explanation-%d-%d" % [OS.get_process_id(), Time.get_ticks_usec()])
		DirAccess.make_dir_recursive_absolute(target)
		if not DirAccess.dir_exists_absolute(target):
			explain_error = tr("EXPLAIN_EXPORT_FAILED")
			refresh_language()
			return
		created_target = true
	if not _explanation_index_matches_at(str(explain_artifacts["json"])):
		if created_target and _explanation_directory_empty(target):
			DirAccess.remove_absolute(target)
		explain_error = tr("EXPLAIN_EXPORT_INCOMPLETE")
		refresh_language()
		return
	for key in EXPLANATION_EXPORT_ORDER:
		var destination := target.path_join(str(explain_artifacts[key]).get_file())
		if FileAccess.file_exists(destination):
			if created_target and _explanation_directory_empty(target):
				DirAccess.remove_absolute(target)
			explain_error = tr("EXPLAIN_EXPORT_EXISTS")
			refresh_language()
			return
	var written: Array[String] = []
	var failed := false
	for key in EXPLANATION_EXPORT_ORDER:
		var source := str(explain_artifacts[key])
		var destination := target.path_join(source.get_file())
		if DirAccess.copy_absolute(source, destination) != OK or not _explanation_file_ready(destination):
			failed = true
			break
		written.append(destination)
	if not failed:
		var copied_json := target.path_join(str(explain_artifacts["json"]).get_file())
		if not _explanation_index_matches_at(copied_json):
			failed = true
	if failed:
		for path in written:
			DirAccess.remove_absolute(path)
		if created_target and _explanation_directory_empty(target):
			DirAccess.remove_absolute(target)
		explain_error = tr("EXPLAIN_EXPORT_FAILED")
		refresh_language()
		return
	explain_note = tr("EXPLAIN_EXPORTED") + " " + target
	refresh_language()


func _clear_explanation() -> void:
	# Clears the UI only; completed artifacts stay on disk and remain accessible.
	explanation = {}
	explain_error = ""
	explain_artifacts = {}
	explain_output_dir = ""
	explain_note = ""


func run_coefficients() -> void:
	if busy or explain_busy or coefficients_busy or not trust.button_pressed:
		return
	if metadata.is_empty() or model_path.is_empty():
		return
	var frozen := _freeze_output_directory(OutputLocation.COEFFICIENTS)
	if not str(frozen.error).is_empty():
		coefficients_error = str(frozen.error)
		refresh_language()
		return
	coefficients_staging_root = str(frozen.root)
	_cleanup_owned_coefficients_staging()
	_clear_coefficients()
	coefficients_output_dir = str(frozen.path)
	var args := PackedStringArray(["coefficients", "--model", model_path, "--trust-model",
		"--output-dir", coefficients_output_dir])
	if not input_path.is_empty() and compatibility.get("compatible", false):
		args.append_array(["--input", input_path])
		for name in mapping:
			args.append_array(["--feature", name])
	coefficients_busy = true
	coefficients_error = ""
	refresh_language()
	if not bridge.start_coefficients(args):
		coefficients_busy = false
		refresh_language()
		return
	coefficients_request = bridge.explanation_generation()


func cancel_coefficients() -> void:
	if not coefficients_busy:
		return
	coefficients_busy = false
	bridge.cancel_explanation()


func _coefficients_response(payload: Dictionary, generation: int) -> void:
	if generation != coefficients_request:
		return
	coefficients_busy = false
	if payload.has("error"):
		coefficients_error = str(payload.error.get("message", tr("COEFFICIENTS_FAILED")))
		coefficient_report = {}
		coefficients_artifacts = {}
		refresh_language()
		return
	coefficient_report = payload.get("coefficients", {})
	coefficients_artifacts = payload.get("artifacts", {})
	if payload.get("output_dir"):
		coefficients_output_dir = str(payload.output_dir)
	if coefficient_report.is_empty():
		coefficients_error = tr("COEFFICIENTS_FAILED")
	refresh_language()


func _coefficients_failed(error: Dictionary, generation: int) -> void:
	if generation != coefficients_request:
		return
	coefficients_busy = false
	coefficient_report = {}
	coefficients_artifacts = {}
	coefficients_error = str(error.get("message", tr("COEFFICIENTS_FAILED")))
	refresh_language()


func _coefficients_cancelled(generation: int) -> void:
	if generation != coefficients_request:
		return
	coefficients_busy = false
	coefficient_report = {}
	coefficients_artifacts = {}
	coefficients_error = tr("COEFFICIENTS_CANCELLED")
	refresh_language()


func _cleanup_owned_coefficients_staging() -> void:
	# Remove only this tool's own incomplete staging directories.
	OutputLocation.cleanup_staging(coefficients_staging_root, OutputLocation.COEFFICIENTS)


func open_coefficients_folder() -> void:
	if coefficients_output_dir.is_empty() or not DirAccess.dir_exists_absolute(coefficients_output_dir):
		coefficients_error = tr("COEFFICIENTS_NO_ARTIFACT")
		refresh_language()
		return
	OS.shell_open(coefficients_output_dir)


func _choose_coefficients_export() -> void:
	if coefficients_artifacts.is_empty():
		coefficients_error = tr("COEFFICIENTS_NO_ARTIFACT")
		refresh_language()
		return
	coefficients_export_dialog.title = tr("EXPORT_COEFFICIENTS")
	# Point at the actual artifacts; the explicit export still never overwrites.
	if not coefficients_output_dir.is_empty():
		coefficients_export_dialog.current_dir = coefficients_output_dir
	coefficients_export_dialog.popup_centered_ratio(0.8)


func _coefficients_source_dir() -> String:
	for key in COEFFICIENT_EXPORT_ORDER:
		if coefficients_artifacts.has(key):
			return str(coefficients_artifacts[key]).get_base_dir()
	return ""


func _coefficients_index_matches_at(json_path: String) -> bool:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if typeof(parsed) != TYPE_DICTIONARY:
		return false
	var index = parsed.get("artifacts", {})
	if typeof(index) != TYPE_DICTIONARY:
		return false
	for key in COEFFICIENT_EXPORT_ORDER:
		if str(index.get(key, "")) != str(coefficients_artifacts[key]).get_file():
			return false
	return true


func export_coefficients(directory: String) -> void:
	# Delivery is all-or-nothing and never overwrites existing files, mirroring the
	# explanation export: a new/empty directory or a unique subdirectory, JSON last.
	coefficients_error = ""
	coefficients_note = ""
	if coefficients_artifacts.is_empty():
		coefficients_error = tr("COEFFICIENTS_NO_ARTIFACT")
		refresh_language()
		return
	for key in COEFFICIENT_EXPORT_ORDER:
		if not coefficients_artifacts.has(key) or not _explanation_file_ready(str(coefficients_artifacts[key])):
			coefficients_error = tr("COEFFICIENTS_EXPORT_INCOMPLETE")
			refresh_language()
			return
	var source_dir := _coefficients_source_dir().simplify_path()
	var base := directory.simplify_path()
	if source_dir != "" and base == source_dir:
		coefficients_error = tr("COEFFICIENTS_EXPORT_SAME_DIR")
		refresh_language()
		return
	var target := base
	var created_target := false
	if not DirAccess.dir_exists_absolute(target):
		DirAccess.make_dir_recursive_absolute(target)
		if not DirAccess.dir_exists_absolute(target):
			coefficients_error = tr("COEFFICIENTS_EXPORT_FAILED")
			refresh_language()
			return
		created_target = true
	elif not _explanation_directory_empty(target):
		target = base.path_join("psyml-coefficients-%d-%d" % [OS.get_process_id(), Time.get_ticks_usec()])
		DirAccess.make_dir_recursive_absolute(target)
		if not DirAccess.dir_exists_absolute(target):
			coefficients_error = tr("COEFFICIENTS_EXPORT_FAILED")
			refresh_language()
			return
		created_target = true
	if not _coefficients_index_matches_at(str(coefficients_artifacts["json"])):
		if created_target and _explanation_directory_empty(target):
			DirAccess.remove_absolute(target)
		coefficients_error = tr("COEFFICIENTS_EXPORT_INCOMPLETE")
		refresh_language()
		return
	for key in COEFFICIENT_EXPORT_ORDER:
		var destination := target.path_join(str(coefficients_artifacts[key]).get_file())
		if FileAccess.file_exists(destination):
			if created_target and _explanation_directory_empty(target):
				DirAccess.remove_absolute(target)
			coefficients_error = tr("COEFFICIENTS_EXPORT_EXISTS")
			refresh_language()
			return
	var written: Array[String] = []
	var failed := false
	for key in COEFFICIENT_EXPORT_ORDER:
		var source := str(coefficients_artifacts[key])
		var destination := target.path_join(source.get_file())
		if DirAccess.copy_absolute(source, destination) != OK or not _explanation_file_ready(destination):
			failed = true
			break
		written.append(destination)
	if not failed:
		var copied_json := target.path_join(str(coefficients_artifacts["json"]).get_file())
		if not _coefficients_index_matches_at(copied_json):
			failed = true
	if failed:
		for path in written:
			DirAccess.remove_absolute(path)
		if created_target and _explanation_directory_empty(target):
			DirAccess.remove_absolute(target)
		coefficients_error = tr("COEFFICIENTS_EXPORT_FAILED")
		refresh_language()
		return
	coefficients_note = tr("COEFFICIENTS_EXPORTED") + " " + target
	refresh_language()


func _clear_coefficients() -> void:
	# Clears the UI only; completed artifacts stay on disk and remain accessible.
	coefficient_report = {}
	coefficients_error = ""
	coefficients_artifacts = {}
	coefficients_output_dir = ""
	coefficients_note = ""


func _fill_coefficients_tree() -> void:
	coefficients_tree.clear()
	var titles := ["COL_OUTPUT", "COL_FEATURE", "COL_SOURCE", "COL_COEFFICIENT"]
	for index in range(4):
		coefficients_tree.set_column_title(index, tr(titles[index]))
	var root := coefficients_tree.create_item()
	coefficients_summary.text = tr("COEFFICIENTS_RESULTS")
	coefficients_outputs.text = tr("COEFFICIENTS_OUTPUTS")
	if coefficient_report.is_empty():
		return
	var status := str(coefficient_report.get("status", ""))
	if status == "unsupported":
		coefficients_summary.text += " · " + (tr("COEFFICIENTS_UNSUPPORTED") % str(coefficient_report.get("reason", "")))
		return
	if status != "available":
		coefficients_summary.text += " · " + (tr("COEFFICIENTS_ERROR") % str(coefficient_report.get("reason", tr("UNAVAILABLE"))))
		return
	var rows: Array = coefficient_report.get("output", {}).get("rows", [])
	var features: Array = coefficient_report.get("features", [])
	var coefficients: Array = coefficient_report.get("coefficients", [])
	var intercepts: Array = coefficient_report.get("intercept", [])
	var shown := 0
	var total := rows.size() * features.size()
	for row in rows:
		for feature in features:
			if shown >= 300:
				break
			var row_index := int(row.get("row_index", 0))
			var feature_index := int(feature.get("index", 0))
			var item := coefficients_tree.create_item(root)
			item.set_text(0, str(row.get("label", "")))
			item.set_text(1, str(feature.get("name", "")))
			item.set_text(2, str(feature.get("source", "")))
			var value = coefficients[row_index][feature_index]
			item.set_text(3, String.num(float(value), 6))
			item.set_tooltip_text(0, _coefficient_output_tooltip(row, row_index, intercepts))
			item.set_tooltip_text(1, str(feature.get("name", "")))
			item.set_tooltip_text(2, str(feature.get("source", "")))
			shown += 1
		if shown >= 300:
			break
	# Every output axis is shown with its own intercept, class/reference meaning,
	# score-vs-probability unit and drop/encoding-independent label.
	var output_lines: Array[String] = []
	for row in rows:
		var row_index := int(row.get("row_index", 0))
		output_lines.append("%s · %s: %s · %s" % [
			str(row.get("label", "")),
			tr("COL_INTERCEPT"),
			_coefficient_number(intercepts, row_index),
			str(row.get("unit", "")),
		])
	coefficients_outputs.text = tr("COEFFICIENTS_OUTPUTS") + "\n" + "\n".join(output_lines)
	if shown < total:
		coefficients_summary.text += " · " + (tr("COEFFICIENTS_ROW_LIMIT") % [shown, total])
	var verification: Dictionary = coefficient_report.get("verification", {})
	var verify_text := tr("COEFFICIENTS_VERIFY_NO_INPUT")
	if verification.get("performed", false):
		verify_text = tr("COEFFICIENTS_VERIFY_OK") if verification.get("verified", false) else tr("COEFFICIENTS_VERIFY_FAILED")
	var fit_scope := str(coefficient_report.get("model", {}).get("fit_scope", tr("UNAVAILABLE")))
	coefficients_summary.text += " · " + (tr("COEFFICIENTS_SUMMARY") % [
		str(coefficient_report.get("family", "")),
		fit_scope,
		verify_text,
		str(verification.get("max_abs_error", tr("UNAVAILABLE")))])


func _coefficient_output_tooltip(row: Dictionary, row_index: int, intercepts: Array) -> String:
	return "%s · %s: %s · %s" % [
		str(row.get("label", "")),
		tr("COL_INTERCEPT"),
		_coefficient_number(intercepts, row_index),
		str(row.get("unit", "")),
	]


func _coefficient_number(values: Array, index: int) -> String:
	if index < 0 or index >= values.size() or values[index] == null:
		return tr("UNAVAILABLE")
	return String.num(float(values[index]), 6)


func _fill_explanation_tree() -> void:
	explain_tree.clear()
	for index in range(4):
		explain_tree.set_column_title(index, tr(["COL_FEATURE", "COL_VALUE", "COL_CONTRIBUTION", "COL_DIRECTION"][index]))
	var root := explain_tree.create_item()
	explain_summary.text = tr("EXPLAIN_RESULTS")
	if explanation.is_empty():
		_update_explanation_artifacts()
		return
	var base := str(explanation.get("base_value", ""))
	var output := str(explanation.get("model_output", ""))
	var error := String.num(float(explanation.get("reconstruction_abs_error", 0.0)), 10)
	explain_summary.text += " · " + (tr("EXPLAIN_SUMMARY") % [base, output, error])
	if explanation.get("task", "") == "classification":
		explain_summary.text += " · " + tr("EXPLAIN_TARGET") + ": " + str(explanation.get("target_class", ""))
	for record in explanation.get("sample_features", []):
		var item := explain_tree.create_item(root)
		item.set_text(0, str(record.get("name", "")))
		item.set_text(1, "<missing>" if record.get("missing", false) else str(record.get("value", "")))
		item.set_text(2, String.num(float(record.get("contribution", 0.0)), 6))
		item.set_text(3, tr("DIRECTION_POSITIVE") if str(record.get("direction", "")) == "positive" else tr("DIRECTION_NEGATIVE"))
		item.set_tooltip_text(0, str(record.get("name", "")))
		item.set_tooltip_text(1, str(record.get("value", "")))
	_update_explanation_artifacts()


func _update_explanation_artifacts() -> void:
	explain_view.texture = null
	explain_view.hide()
	var png := str(explain_artifacts.get("png", ""))
	if png.is_empty() or not FileAccess.file_exists(png):
		return
	var image := Image.load_from_file(png)
	if image != null:
		explain_view.texture = ImageTexture.create_from_image(image)
		explain_view.show()


func refresh_language() -> void:
	main.tabs.set_tab_title(4, tr("TAB_PREDICTION"))
	model_button.disabled = busy or explain_busy or coefficients_busy or not trust.button_pressed
	trust.disabled = busy or explain_busy or coefficients_busy
	data_button.disabled = busy or explain_busy or coefficients_busy
	predict_button.disabled = busy or explain_busy or coefficients_busy or not trust.button_pressed or not compatibility.get("compatible", false)
	export_button.disabled = busy or explain_busy or coefficients_busy or predictions.is_empty()
	for option in mapping_options:
		option.disabled = busy or explain_busy or coefficients_busy
	if is_instance_valid(mapping_confirm):
		mapping_confirm.disabled = busy or explain_busy or coefficients_busy
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
	background_button.disabled = busy or explain_busy or coefficients_busy
	background_label.tooltip_text = background_path
	background_label.text = background_path.get_file() if not background_path.is_empty() else tr("NO_BACKGROUND")
	explain_row.editable = not (busy or explain_busy or coefficients_busy)
	explain_row.max_value = maxi(1, int(data.get("row_count", 1)))
	if explain_row.value > explain_row.max_value:
		explain_row.value = explain_row.max_value
	var classification: bool = str(metadata.get("task", "")) == "classification"
	explain_class_box.visible = classification
	explain_class.disabled = busy or explain_busy or coefficients_busy
	explain_background_size.editable = not (busy or explain_busy or coefficients_busy)
	explain_cycles.editable = not (busy or explain_busy or coefficients_busy)
	var ready: bool = (not busy and not explain_busy and not coefficients_busy and trust.button_pressed
		and not metadata.is_empty() and not input_path.is_empty()
		and compatibility.get("compatible", false) and not background_path.is_empty())
	explain_button.disabled = not ready
	explain_cancel_button.disabled = not explain_busy
	explain_open_button.disabled = explain_busy or coefficients_busy or not explain_artifacts.has("png")
	explain_folder_button.disabled = explain_busy or coefficients_busy or explain_artifacts.is_empty()
	explain_export_button.disabled = explain_busy or coefficients_busy or explain_artifacts.is_empty()
	if explain_busy:
		explain_status.text = tr("EXPLAIN_BUSY")
	elif not explain_error.is_empty():
		explain_status.text = explain_error
	elif not explain_note.is_empty():
		explain_status.text = explain_note
	elif not explanation.is_empty():
		explain_status.text = tr("EXPLAIN_DONE")
	else:
		explain_status.text = tr("EXPLAIN_WAITING")
	_fill_explanation_tree()
	var coefficients_ready: bool = (not busy and not explain_busy and not coefficients_busy
		and trust.button_pressed and not metadata.is_empty() and not model_path.is_empty())
	coefficients_button.disabled = not coefficients_ready
	coefficients_cancel_button.disabled = not coefficients_busy
	coefficients_open_button.disabled = coefficients_busy or coefficients_artifacts.is_empty()
	coefficients_export_button.disabled = coefficients_busy or coefficients_artifacts.is_empty()
	if coefficients_busy:
		coefficients_status.text = tr("COEFFICIENTS_BUSY")
	elif not coefficients_error.is_empty():
		coefficients_status.text = coefficients_error
	elif not coefficients_note.is_empty():
		coefficients_status.text = coefficients_note
	elif not coefficient_report.is_empty():
		var coefficient_status := str(coefficient_report.get("status", ""))
		if coefficient_status == "available":
			coefficients_status.text = tr("COEFFICIENTS_DONE")
		elif coefficient_status == "unsupported":
			coefficients_status.text = tr("COEFFICIENTS_UNSUPPORTED") % str(coefficient_report.get("reason", ""))
		else:
			coefficients_status.text = tr("COEFFICIENTS_ERROR") % str(coefficient_report.get("reason", tr("UNAVAILABLE")))
	else:
		coefficients_status.text = tr("COEFFICIENTS_WAITING")
	_fill_coefficients_tree()
	if output_edit != null:
		output_edit.placeholder_text = tr("SELECT_OUTPUT")
		sync_output_root()


func _exit_tree() -> void:
	if explain_busy:
		bridge.cancel_explanation()
	if coefficients_busy:
		bridge.cancel_explanation()
	_clear_explanation()
	_clear_coefficients()
	_clear_predictions()
