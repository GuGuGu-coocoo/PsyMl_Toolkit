extends SceneTree


func _initialize() -> void:
	call_deferred("_capture")


func _capture() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	var requested_locale := OS.get_environment("PSYML_SCREENSHOT_LOCALE")
	var locale_index := PsyMLI18n.LOCALES.find(requested_locale)
	if locale_index >= 0:
		main._on_language_selected(locale_index)
	await process_frame
	await process_frame
	var image := root.get_viewport().get_texture().get_image()
	var output_path := OS.get_environment("PSYML_SCREENSHOT_PATH")
	if output_path.is_empty():
		output_path = OS.get_temp_dir().path_join("psyml-ui.png")
	var error := image.save_png(output_path)
	if error != OK:
		push_error("Could not save screenshot: %s" % error_string(error))
		quit(1)
		return
	print("PSYML_SCREENSHOT=" + output_path)
	quit(0)
