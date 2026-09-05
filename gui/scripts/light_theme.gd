extends RefCounted
## Complete the light palette for inherited hover states and popup windows.

static func apply_to(app_theme: Theme, text: Color, muted: Color, surface: Color, border: Color, accent: Color) -> void:
	var defaults := ThemeDB.get_default_theme()
	for kind in ["Button", "OptionButton", "CheckBox", "CheckButton", "PopupMenu", "Tree", "ItemList", "LineEdit", "TextEdit", "TooltipLabel"]:
		for key in defaults.get_color_list(kind):
			if key.begins_with("font_") and not "outline" in key and not "shadow" in key:
				app_theme.set_color(key, kind, muted if "disabled" in key or "uneditable" in key or "placeholder" in key else text)
	for kind in ["LineEdit", "TextEdit"]:
		app_theme.set_color("selection_color", kind, Color("dce4ff"))
		app_theme.set_color("caret_color", kind, text)
	for key in ["icon_normal_color", "icon_hover_color", "icon_pressed_color", "icon_hover_pressed_color", "icon_focus_color"]:
		app_theme.set_color(key, "Button", text)
	app_theme.set_color("icon_disabled_color", "Button", Color("7e8898"))
	for key in ["clear_button_color", "clear_button_color_pressed"]:
		app_theme.set_color(key, "LineEdit", text)
	for side in ["up", "down"]:
		for state in ["", "hover_", "pressed_", "disabled_"]:
			app_theme.set_color(side + "_" + state + "icon_modulate", "SpinBox", muted if state == "disabled_" else text)
	for key in ["checkbox_checked_color", "checkbox_unchecked_color"]:
		app_theme.set_color(key, "CheckBox", accent)
	for kind in ["PopupMenu", "TooltipPanel", "AcceptDialog"]:
		var panel := StyleBoxFlat.new()
		panel.bg_color = Color.WHITE
		panel.border_color = border
		panel.set_border_width_all(1)
		panel.set_corner_radius_all(8)
		panel.set_content_margin_all(10)
		app_theme.set_stylebox("panel", kind, panel)
	for key in ["hover", "hovered", "hovered_dimmed", "hovered_selected", "hovered_selected_focus"]:
		var hover := StyleBoxFlat.new()
		hover.bg_color = Color("e6e9fc")
		hover.set_corner_radius_all(4)
		app_theme.set_stylebox(key, "PopupMenu" if key == "hover" else "Tree", hover)
	for key in ["embedded_border", "embedded_unfocused_border"]:
		var window_border: StyleBoxFlat = defaults.get_stylebox(key, "Window").duplicate()
		window_border.bg_color = Color.WHITE
		window_border.border_color = surface
		app_theme.set_stylebox(key, "Window", window_border)
	app_theme.set_color("title_color", "Window", text)
	var close_image := Image.new()
	close_image.load_svg_from_string('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><path d="M4 4 L12 12 M12 4 L4 12" stroke="#242b3b" stroke-width="2" stroke-linecap="round"/></svg>')
	for key in ["close", "close_pressed"]:
		app_theme.set_icon(key, "Window", ImageTexture.create_from_image(close_image))
	app_theme.set_color("folder_icon_color", "FileDialog", accent)
	app_theme.set_color("file_icon_color", "FileDialog", text)
	app_theme.set_color("file_disabled_color", "FileDialog", muted)
	# Preserve white lettering on the accent action across all button states.
	for state in ["font_color", "font_hover_color", "font_pressed_color", "font_hover_pressed_color", "font_focus_color"]:
		app_theme.set_color(state, "AccentButton", Color.WHITE)
