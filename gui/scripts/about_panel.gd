extends PanelContainer
## A non-modal link panel: no embedded manual, network calls or analysis state.

const REPOSITORY := "https://github.com/GuGuGu-coocoo/PsyMl_Toolkit"
var main: Control
var entry: Button
var close_button: Button
var heading: Label
var version: Label
var note: RichTextLabel
var links: Array[Button] = []
var previous_focus: Control
var open_url: Callable = OS.shell_open


func build(owner: Control) -> void:
	main = owner
	name = "AboutPanel"
	z_index = 10
	mouse_filter = Control.MOUSE_FILTER_STOP
	var panel_style = main._style_box(Color.WHITE, 8, main.BORDER)
	panel_style.shadow_color = Color(0, 0, 0, 0.18)
	panel_style.shadow_size = 10
	add_theme_stylebox_override("panel", panel_style)
	custom_minimum_size = Vector2(440, 0)
	size = Vector2(500, 300)
	entry = Button.new()
	entry.name = "AboutButton"
	main.language_option.get_parent().add_child(entry)
	entry.pressed.connect(show_panel)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	add_child(content)
	var top := HBoxContainer.new()
	content.add_child(top)
	heading = Label.new()
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(heading)
	close_button = Button.new()
	top.add_child(close_button)
	close_button.pressed.connect(close_panel)
	version = Label.new()
	content.add_child(version)
	note = preload("res://scripts/selectable_text.gd").new()
	content.add_child(note)
	for key in ["ABOUT_PROJECT", "ABOUT_README", "ABOUT_GUIDE"]:
		var link := Button.new()
		link.set_meta("key", key)
		content.add_child(link)
		links.append(link)
		link.pressed.connect(func(): open_link(key))
	main.resized.connect(_position_panel)
	resized.connect(_position_panel)
	minimum_size_changed.connect(func(): _position_panel.call_deferred())
	refresh_language()
	hide()


func link_urls() -> Dictionary:
	var locale := TranslationServer.get_locale()
	var language := "ZH" if locale.begins_with("zh") else ("FR" if locale.begins_with("fr") else "EN")
	var readme := "README.md" if language == "EN" else "README_" + language + ".md"
	return {"ABOUT_PROJECT": REPOSITORY,
		"ABOUT_README": REPOSITORY + "/blob/main/" + readme,
		"ABOUT_GUIDE": REPOSITORY + "/blob/main/docs/RESEARCHER_GUIDE_" + language + ".md"}


func refresh_language() -> void:
	entry.text = main.tr("ABOUT")
	heading.text = main.tr("ABOUT_TITLE")
	close_button.text = main.tr("CLOSE")
	version.text = "PsyML Toolkit " + main._display_version(main._resolve_version()) + " · Apache 2.0"
	note.text = main.tr("ABOUT_NETWORK")
	var urls := link_urls()
	for link in links:
		var key: String = link.get_meta("key")
		link.text = main.tr(key)
		link.tooltip_text = urls[key]
	_position_panel()


func _position_panel() -> void:
	if main != null:
		size = Vector2(minf(500, main.size.x - 48), get_combined_minimum_size().y)
		position = (main.size - size) / 2


func show_panel() -> void:
	if not visible:
		previous_focus = get_viewport().gui_get_focus_owner()
	refresh_language()
	show()
	_position_panel()
	close_button.grab_focus()


func close_panel() -> void:
	var focus := get_viewport().gui_get_focus_owner()
	var owns_focus := focus != null and is_ancestor_of(focus)
	hide()
	if owns_focus:
		if is_instance_valid(previous_focus) and previous_focus.is_visible_in_tree():
			previous_focus.grab_focus()
		else:
			entry.grab_focus()


func _unhandled_key_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close_panel()
		get_viewport().set_input_as_handled()


func open_link(key: String) -> void:
	var urls := link_urls()
	if not urls.has(key):
		return
	var error: int = open_url.call(urls[key])
	note.text = main.tr("ABOUT_NETWORK") if error == OK else main.tr("ABOUT_OPEN_FAILED") + "\n" + str(urls[key])
