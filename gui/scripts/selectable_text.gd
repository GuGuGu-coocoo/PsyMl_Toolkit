extends RichTextLabel
## Readable values and help text grow with the page and keep native selection.


func _init() -> void:
	fit_content = true
	scroll_active = false
	selection_enabled = true
	context_menu_enabled = true
	shortcut_keys_enabled = true
	focus_mode = Control.FOCUS_ALL
	mouse_filter = Control.MOUSE_FILTER_PASS
	mouse_force_pass_scroll_events = true
	autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
