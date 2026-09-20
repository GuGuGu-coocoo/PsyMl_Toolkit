extends SceneTree
## Capture the fitted-coefficients UI for visual QA (synthetic data only).
##
## Run windowed (not --headless) with PSYML_PYTHON and PSYML_SCREENSHOT_DIR set:
##   PSYML_SCREENSHOT_DIR=tmp/screenshots \
##   godot --path gui --script res://tests/capture_coefficients.gd
## Screenshots for zh/en/fr are saved as coefficients-zh.png, coefficients-en.png,
## coefficients-fr.png.

const TestPaths = preload("res://tests/test_paths.gd")


func _initialize() -> void:
	call_deferred("_capture")


func _write(path: String, content: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(content)
	file.close()


func _wait_busy(page) -> void:
	var deadline := Time.get_ticks_msec() + 60000
	while page.busy and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not page.busy, "Prediction operation timed out")


func _wait_coefficients(page) -> void:
	var deadline := Time.get_ticks_msec() + 120000
	while page.coefficients_busy and Time.get_ticks_msec() < deadline:
		await create_timer(.1).timeout
	assert(not page.coefficients_busy, "Coefficient extraction timed out")


func _grab(path: String) -> void:
	await RenderingServer.frame_post_draw
	await process_frame
	await process_frame
	root.get_viewport().get_texture().get_image().save_png(path)


func _scroll_to(control: Control) -> void:
	var node: Node = control.get_parent()
	while node != null:
		if node is ScrollContainer:
			node.ensure_control_visible(control)
			return
		node = node.get_parent()


func _capture() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	root.size = Vector2i(1280, 1000)
	var output := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if output.is_empty():
		output = TestPaths.temp_dir().path_join("screenshots")
	DirAccess.make_dir_recursive_absolute(output)
	var directory := TestPaths.temp_dir().path_join("coefficients-capture-%d" % Time.get_ticks_usec())
	DirAccess.make_dir_recursive_absolute(directory)
	var page = main.prediction_page

	var input := ProjectSettings.globalize_path("res://../examples/quickstart/classification_train.csv")
	var predict_input := ProjectSettings.globalize_path("res://../examples/quickstart/classification_predict.csv")
	var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../examples/quickstart/classification_coefficients_config.json"))
	config.input_path = input
	config.output_dir = directory.path_join("run")
	config.figure_types = []
	for field in ["n_splits", "random_seed", "inner_splits", "max_candidates"]:
		if config.has(field):
			config[field] = int(config[field])
	var config_path := directory.path_join("config.json")
	_write(config_path, JSON.stringify(config))
	var response: Dictionary = main.bridge.execute_json_sync(PackedStringArray(["run", "--config", config_path]))
	assert(not response.has("error"), str(response))
	var model_path: String = str(config.output_dir).path_join(response.model_export.model_path)

	page.trust.button_pressed = true
	page.load_model(model_path)
	await _wait_busy(page)
	page.load_data(predict_input)
	await _wait_busy(page)
	page.run_coefficients()
	await _wait_coefficients(page)
	assert(page.coefficients_error.is_empty(), page.coefficients_error)
	main.tabs.current_tab = 4
	for locale in [0, 1, 2]:
		main._on_language_selected(locale)
		await create_timer(0.2).timeout
		# The coefficients block sits after the prediction and explanation sections;
		# bring the block's own table (and everything above it) into view.
		_scroll_to(page.coefficients_tree)
		await create_timer(0.4).timeout
		await _grab(output.path_join("coefficients-%s.png" % ["zh", "en", "fr"][locale]))
	print("PSYML_COEFFICIENTS_CAPTURE_OK")
	quit(0)
