extends RefCounted
## FR-005 fitted coefficients on the results page: a compact, visible status line
## and an explicit way to open the artifacts produced by the analysis.
##
## Reads only what the runner already wrote into `result.json`; it never recomputes
## science and never refits anything.

var main: Control
var heading: Label
var status_label: Label
var detail_label: Label
var open_button: Button
var current_dir := ""
var current_artifacts: Dictionary = {}
var current_entry: Dictionary = {}


func _init(owner: Control) -> void:
	main = owner


func build() -> void:
	var parent: Node = main.predictions_tree.get_parent()
	heading = Label.new()
	heading.add_theme_font_size_override("font_size", 18)
	parent.add_child(heading)
	main.translated_controls.append({"node": heading, "key": "RESULT_COEFFICIENTS_SECTION"})

	status_label = Label.new()
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(status_label)

	detail_label = Label.new()
	detail_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(detail_label)

	open_button = Button.new()
	parent.add_child(open_button)
	main.translated_controls.append({"node": open_button, "key": "OPEN_COEFFICIENTS_FOLDER"})
	open_button.pressed.connect(_open)
	clear()


func clear() -> void:
	current_entry = {}
	current_artifacts = {}
	current_dir = ""
	if heading == null:
		return
	heading.hide()
	status_label.text = ""
	status_label.hide()
	detail_label.text = ""
	detail_label.hide()
	open_button.hide()


func load_result(parsed: Dictionary, result_dir: String) -> void:
	clear()
	var entry = parsed.get("coefficients", {})
	if typeof(entry) != TYPE_DICTIONARY or entry.is_empty():
		return
	current_entry = entry
	current_dir = result_dir
	current_artifacts = entry.get("artifacts", {}) if typeof(entry.get("artifacts", {})) == TYPE_DICTIONARY else {}
	_render()


func _render() -> void:
	heading.show()
	status_label.show()
	open_button.show()
	open_button.disabled = current_artifacts.is_empty()
	status_label.text = ""
	detail_label.text = ""
	detail_label.hide()
	var status := str(current_entry.get("status", ""))
	if status == "available":
		var verification: Dictionary = current_entry.get("verification", {})
		status_label.text = main.tr("COEFFICIENTS_RESULTS") + " · " + (main.tr("COEFFICIENTS_SUMMARY") % [
			str(current_entry.get("family", "")),
			str(current_entry.get("fit_scope", main.tr("UNAVAILABLE"))),
			_verification_text(verification),
			str(verification.get("max_abs_error", main.tr("UNAVAILABLE"))),
		])
		var artifacts: Array[String] = []
		for key in current_artifacts:
			artifacts.append(str(key))
		if not artifacts.is_empty():
			detail_label.text = main.tr("RESULT_COEFFICIENTS_ARTIFACTS") + " " + ", ".join(artifacts)
			detail_label.show()
	elif status == "unsupported":
		status_label.text = main.tr("COEFFICIENTS_UNSUPPORTED") % str(current_entry.get("reason", ""))
		open_button.disabled = true
	else:
		status_label.text = main.tr("COEFFICIENTS_ERROR") % str(current_entry.get("reason", main.tr("UNAVAILABLE")))
		open_button.disabled = true


func _verification_text(verification: Dictionary) -> String:
	if not verification.get("performed", false):
		return main.tr("COEFFICIENTS_VERIFY_NO_INPUT")
	if verification.get("verified", false):
		return main.tr("COEFFICIENTS_VERIFY_OK")
	return main.tr("COEFFICIENTS_VERIFY_FAILED")


func _open() -> void:
	if current_dir.is_empty():
		return
	var target := current_dir.path_join("coefficients")
	if not DirAccess.dir_exists_absolute(target):
		target = current_dir
	if DirAccess.dir_exists_absolute(target):
		OS.shell_open(target)


func refresh_language() -> void:
	if heading == null or current_entry.is_empty():
		return
	_render()
