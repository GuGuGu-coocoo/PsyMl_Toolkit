extends SceneTree
## Passive screenshot harness: every application action is performed through the UI.
## F12 saves the visible viewport. No configuration, navigation or run is automated.

var main: Control
var capture_count := 0


class CaptureHotkey extends Node:
	func _input(event: InputEvent) -> void:
		if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F12:
			get_tree().call_deferred("capture_visible_page")


func _initialize() -> void:
	call_deferred("start_window")


func start_window() -> void:
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	root.add_child(CaptureHotkey.new())


func capture_visible_page() -> void:
	var directory := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if directory.is_empty():
		push_error("Set PSYML_SCREENSHOT_DIR before taking a manual capture")
		return
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(directory)
	capture_count += 1
	var path := directory.path_join("%02d-%s-page%d.png" % [capture_count, TranslationServer.get_locale(), main.tabs.current_tab + 1])
	var error := root.get_viewport().get_texture().get_image().save_png(path)
	if error != OK:
		push_error(error_string(error))
	else:
		print("PSYML_MANUAL_CAPTURE=" + path)
