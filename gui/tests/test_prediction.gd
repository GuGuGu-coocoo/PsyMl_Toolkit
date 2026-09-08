extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _wait(page) -> void:
	var deadline := Time.get_ticks_msec() + 25000
	while page.busy and Time.get_ticks_msec() < deadline:
		await create_timer(.05).timeout
	assert(not page.busy, "Prediction operation timed out")

func _write(path: String, content: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(content)
	file.close()

func _run() -> void:
	if not OS.get_environment("PSYML_PREDICTION_CAPTURE").is_empty():
		root.size = Vector2i(1280, 1000)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var page = main.prediction_page
	assert(main.tabs.get_tab_count() == 5 and main.tabs.is_tab_hidden(1))
	assert(main.tabs.get_tab_title(4) == "4  模型与预测")
	assert(page.predict_button.disabled and page.model_button.disabled)
	assert(not page.data_button.disabled)
	var directory := OS.get_temp_dir().path_join("psyml-prediction-ui-%d" % Time.get_ticks_usec())
	DirAccess.make_dir_recursive_absolute(directory)
	# Exercise each task through real full-data training, disk save and GUI inference.
	for task in ["classification", "regression"]:
		var input := ProjectSettings.globalize_path("res://../examples/synthetic/" + task + ".csv")
		var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../examples/synthetic/" + task + "_config.json"))
		config.input_path = input
		config.output_dir = directory.path_join(task)
		config.figure_types = []
		for field in ["n_splits", "random_seed", "inner_splits", "max_candidates"]:
			if config.has(field):
				config[field] = int(config[field])
		if task == "classification":
			config.model_name = "logistic_regression"
			config.model_names = ["logistic_regression"]
			config.tuning_mode = "none"
			config.parameter_grids = {}
		var config_path := directory.path_join(task + ".json")
		_write(config_path, JSON.stringify(config))
		var response: Dictionary = main.bridge.execute_json_sync(PackedStringArray(["run", "--config", config_path]))
		assert(not response.has("error"), str(response))
		var model_path: String = str(config.output_dir).path_join(response.model_export.model_path)
		# Data-first and model-first must both trigger automatic checks.
		page.trust.button_pressed = true
		if task == "classification":
			page.load_data(input)
			await _wait(page)
			assert(page.predict_button.disabled)
		page.load_model(model_path)
		await _wait(page)
		page.load_data(input)
		await _wait(page)
		assert(page.error_message.is_empty(), page.error_message)
		assert(page.compatibility.compatible and not page.predict_button.disabled)
		assert(page.data.row_count > 0 and page.required_tree.get_root().get_first_child() != null)
		page.run_prediction()
		assert(page.predict_button.disabled)
		await _wait(page)
		assert(page.error_message.is_empty(), page.error_message)
		assert(not page.export_button.disabled and not page.predictions.is_empty())
		var names: Array = []
		for column in page.predictions.columns:
			names.append(column.name)
		if task == "classification":
			assert("predicted_class" in names and "probability_0" in names and "probability_1" in names)
		else:
			assert("predicted_value" in names and not "probability_0" in names)
		for locale in range(3):
			main._on_language_selected(locale)
			assert(not page.predict_button.disabled and not page.export_button.disabled)
			assert(page.model_info.text.contains(str(page.metadata.n_features)))
			var capture_dir := OS.get_environment("PSYML_PREDICTION_CAPTURE")
			if task == "classification" and not capture_dir.is_empty():
				var destination := capture_dir.path_join(["zh", "en", "fr"][locale])
				DirAccess.make_dir_recursive_absolute(destination)
				main.tabs.current_tab = 4
				page.page.scroll_vertical = 0
				await process_frame
				await process_frame
				await RenderingServer.frame_post_draw
				root.get_texture().get_image().save_png(destination.path_join("09-prediction.png"))
				page.page.ensure_control_visible(page.result_tree)
				await process_frame
				await process_frame
				await RenderingServer.frame_post_draw
				root.get_texture().get_image().save_png(destination.path_join("10-prediction-results.png"))
		var exported := directory.path_join(task + "_predictions.xlsx")
		page.export_predictions(exported)
		await _wait(page)
		assert(FileAccess.file_exists(exported), page.error_message)
		if task == "classification":
			var reordered := directory.path_join("reordered.csv")
			_write(reordered, "new_id,category,score,target\n101,A,1.5,0\n102,B,-1.2,1\n")
			page.load_data(reordered)
			await _wait(page)
			assert(page.compatibility.compatible)
			page.run_prediction()
			await _wait(page)
			assert(page.predictions.row_count == 2)
			assert(page.predictions.columns[0].name == "new_id")
			assert(page.predictions.sample[0].new_id == 101)
			var wrong_type := directory.path_join("wrong_type.csv")
			_write(wrong_type, "score,category\ntwenty,A\nthirty,B\n")
			page.load_data(wrong_type)
			await _wait(page)
			assert(page.predict_button.disabled)
			assert(page.compatibility.errors[0].code == "incompatible_type")
		# Selecting incompatible data clears every old output before the request completes.
		var missing := directory.path_join("missing.csv")
		_write(missing, "unrelated\n1\n2\n")
		page.load_data(missing)
		assert(page.predictions.is_empty() and page.export_button.disabled and page.predict_button.disabled)
		await _wait(page)
		assert(not page.compatibility.compatible and page.predict_button.disabled)
		assert(page.compatibility.errors[0].code == "missing_feature")
		page.trust.button_pressed = false
		assert(page.metadata.is_empty() and page.predict_button.disabled)
	# Compact ordered mapping for a fitted model without feature names.
	var manual := directory.path_join("manual.pkl")
	var output: Array = []
	assert(OS.execute(main.bridge.python_executable(), PackedStringArray(["-c", "import sys, joblib, numpy as np; from sklearn.linear_model import LinearRegression; joblib.dump(LinearRegression().fit(np.array([[1,5],[2,8],[3,7]]), [1,4,9]), sys.argv[1])", manual]), output, true) == 0)
	var mapping_data := directory.path_join("mapping.csv")
	_write(mapping_data, "second,first\n5,1\n8,2\n")
	page.trust.button_pressed = true
	page.load_model(manual)
	await _wait(page)
	page.load_data(mapping_data)
	await _wait(page)
	assert(page.mapping_toggle.visible and page.predict_button.disabled)
	assert(page.mapping_options.size() == 2)
	page.mapping_options[0].select(2)
	page.mapping_options[1].select(1)
	page.confirm_mapping()
	await _wait(page)
	assert(page.compatibility.compatible and not page.predict_button.disabled)
	page.run_prediction()
	await _wait(page)
	assert(page.predictions.row_count == 2 and not page.export_button.disabled)
	page.mapping_options[0].item_selected.emit(1)
	assert(page.predict_button.disabled and page.export_button.disabled)
	# Readable failures must leave the application usable.
	var corrupt := directory.path_join("corrupt.joblib")
	_write(corrupt, "not a model")
	page.trust.button_pressed = true
	page.load_model(corrupt)
	await _wait(page)
	assert(not page.error_message.is_empty() and page.predict_button.disabled)
	assert(not page.data_button.disabled)
	print("PSYML_PREDICTION_UI_OK")
	quit(0)
