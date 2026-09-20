extends SceneTree

const TestPaths = preload("res://tests/test_paths.gd")
const OutputLocation = preload("res://scripts/output_location.gd")
const NativeSmoke = preload("res://scripts/native_smoke.gd")

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

func _file_size(path: String) -> int:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return -1
	var length := file.get_length()
	file.close()
	return length


func _user_output_state() -> Dictionary:
	# Snapshot the hidden application-data folders with a bounded depth so a
	# failed operation can be checked to not have fallen back there.
	var state := {}
	for family in ["prediction", "explanation", "coefficients"]:
		_collect_user_files(ProjectSettings.globalize_path("user://" + family), family, state, 0)
	return state


func _collect_user_files(path: String, label: String, state: Dictionary, depth: int) -> void:
	var directory := DirAccess.open(path)
	if directory == null:
		return
	for name in directory.get_files():
		state[label.path_join(name)] = _file_size(path.path_join(name))
	if depth >= 3:
		return
	for name in directory.get_directories():
		_collect_user_files(path.path_join(name), label.path_join(name), state, depth + 1)


func _run_directories(root: String) -> Array:
	var names: Array = []
	var directory := DirAccess.open(root.path_join("prediction"))
	if directory == null:
		return names
	for name in directory.get_directories():
		names.append(name)
	return names


func _prediction_delivery_states(
		main, page, opened: Array[String], directory: String, model_path: String, data_path: String) -> void:
	# Delivery states: every state that is not a completed run must
	# keep the button disabled and make the open action refuse without calling the
	# opener; only a new successful run restores opening for its own run folder.
	var smoke_root: String = NativeSmoke.smoke_root()
	assert(smoke_root.is_absolute_path() and DirAccess.dir_exists_absolute(smoke_root), smoke_root)
	var configured_tmp := OS.get_environment("PSYML_TEST_TMP").strip_edges()
	if not configured_tmp.is_empty():
		assert(smoke_root == configured_tmp, "PSYML_TEST_TMP must drive the smoke root")
	var root: String = page.output_edit.text
	page.trust.button_pressed = true
	page.load_model(model_path)
	await _wait(page)
	page.load_data(data_path)
	await _wait(page)
	assert(page.mapping_toggle.visible and page.predict_button.disabled)
	page.mapping_options[0].select(2)
	page.mapping_options[1].select(1)
	page.confirm_mapping()
	await _wait(page)
	assert(page.compatibility.get("compatible", false) and not page.predict_button.disabled)

	# First failure: the check passed, but the core predict cannot read the input
	# any more. The frozen run folder exists without a CSV, so the former
	# "directory exists" test must not be enough to offer or open it.
	var parked_input := directory.path_join("delivery-parked-input.csv")
	assert(DirAccess.rename_absolute(data_path, parked_input) == OK)
	var runs_before := _run_directories(root)
	page.run_prediction()
	await _wait(page)
	assert(not page.error_message.is_empty())
	assert(page.predictions.is_empty())
	assert(page.prediction_folder_button.disabled)
	assert(page.prediction_ready() == not page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.is_empty(), str(opened))
	assert(page.error_message == main.tr("PREDICTION_NO_ARTIFACT"), page.error_message)
	var new_runs: Array = _run_directories(root).filter(func(name): return not runs_before.has(name))
	assert(new_runs.size() == 1, str(new_runs))
	# The exact former false positive: this failed run allocated its own folder
	# and result_path points inside it, but no CSV was written.
	var failed_dir: String = page.result_path.get_base_dir()
	assert(failed_dir.get_base_dir() == root.path_join("prediction"), page.result_path)
	assert(failed_dir.get_file() == str(new_runs[0]), page.result_path)
	assert(DirAccess.dir_exists_absolute(failed_dir))
	assert(not FileAccess.file_exists(page.result_path), "a failed run must not leave a CSV")

	# Restoring the input and completing a run restores opening for this run; the
	# bundled smoke helper accepts exactly this run's CSV and folder target.
	assert(DirAccess.rename_absolute(parked_input, data_path) == OK)
	page.error_message = ""
	page.load_data(data_path)
	await _wait(page)
	assert(page.mapping_toggle.visible and page.predict_button.disabled)
	page.mapping_options[0].select(2)
	page.mapping_options[1].select(1)
	page.confirm_mapping()
	await _wait(page)
	assert(page.prediction_folder_button.disabled)
	page.run_prediction()
	await _wait(page)
	assert(page.error_message.is_empty(), page.error_message)
	assert(not page.predictions.is_empty() and not page.prediction_folder_button.disabled)
	var completed_csv: String = page.result_path
	assert(completed_csv.get_file() == "predictions.csv" and FileAccess.file_exists(completed_csv))
	assert(completed_csv.get_base_dir() != failed_dir)
	var delivery: String = NativeSmoke.verify_prediction_delivery(page)
	assert(delivery == "", delivery)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.size() == 1 and opened[0] == completed_csv.get_base_dir(), str(opened))

	# Changing the result root only affects later runs: the displayed completed
	# result is still this run's folder and opens correctly.
	var later_root := TestPaths.temp_dir().path_join("psyml delivery %d" % Time.get_ticks_usec())
	page.set_output_root(later_root)
	page.refresh_language()
	assert(not page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.size() == 1 and opened[0] == completed_csv.get_base_dir(), str(opened))
	assert(FileAccess.file_exists(completed_csv))
	page.set_output_root(root)
	page.refresh_language()

	# A CSV moved away no longer qualifies even though the run folder exists; the
	# GUI deletes nothing and putting the file back restores the same run.
	var parked_csv := directory.path_join("delivery-parked.csv")
	assert(DirAccess.rename_absolute(completed_csv, parked_csv) == OK)
	page.refresh_language()
	assert(page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.is_empty(), str(opened))
	assert(page.error_message == main.tr("PREDICTION_NO_ARTIFACT"), page.error_message)
	page.error_message = ""
	assert(DirAccess.rename_absolute(parked_csv, completed_csv) == OK)
	page.refresh_language()
	assert(not page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.size() == 1 and opened[0] == completed_csv.get_base_dir(), str(opened))

	# While a new run is in flight the previous completed result is not offered.
	page.run_prediction()
	assert(page.busy and page.prediction_folder_button.disabled)
	assert(page.prediction_ready() == not page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.is_empty(), str(opened))
	page.error_message = ""
	await _wait(page)
	assert(page.error_message.is_empty(), page.error_message)
	assert(not page.prediction_folder_button.disabled)
	var second_csv: String = page.result_path
	assert(second_csv != completed_csv and FileAccess.file_exists(second_csv))
	assert(second_csv.get_base_dir().get_base_dir() == root.path_join("prediction"), second_csv)

	# A retry that really fails clears the open state again; the earlier
	# successful CSV stays on disk and a later success restores opening.
	assert(DirAccess.rename_absolute(data_path, parked_input) == OK)
	var before_retry := _run_directories(root)
	page.run_prediction()
	await _wait(page)
	assert(not page.error_message.is_empty())
	assert(page.predictions.is_empty() and page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.is_empty(), str(opened))
	assert(FileAccess.file_exists(second_csv), "a failed retry must not delete an earlier successful CSV")
	var retry_runs: Array = _run_directories(root).filter(func(name): return not before_retry.has(name))
	assert(retry_runs.size() == 1, str(retry_runs))
	assert(
		not FileAccess.file_exists(root.path_join("prediction").path_join(str(retry_runs[0])).path_join("predictions.csv")),
		str(retry_runs))
	assert(DirAccess.rename_absolute(parked_input, data_path) == OK)
	page.error_message = ""
	page.load_data(data_path)
	await _wait(page)
	assert(page.mapping_toggle.visible and page.predict_button.disabled)
	page.mapping_options[0].select(2)
	page.mapping_options[1].select(1)
	page.confirm_mapping()
	await _wait(page)
	# Nothing becomes openable until a new run actually completes.
	assert(page.prediction_folder_button.disabled)
	page.run_prediction()
	await _wait(page)
	assert(page.error_message.is_empty(), page.error_message)
	assert(not page.prediction_folder_button.disabled)
	assert(page.result_path != second_csv and FileAccess.file_exists(page.result_path))
	opened.clear()
	page.open_prediction_folder()
	assert(opened.size() == 1 and opened[0] == page.result_path.get_base_dir(), str(opened))
	delivery = NativeSmoke.verify_prediction_delivery(page)
	assert(delivery == "", delivery)


func _run() -> void:
	if not OS.get_environment("PSYML_PREDICTION_CAPTURE").is_empty():
		root.size = Vector2i(1280, 1000)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var page = main.prediction_page
	# Open actions are verified against the exact target they hand to the OS
	# without launching a file manager from the test.
	var opened: Array[String] = []
	page.open_target_handler = func(path: String): opened.append(path)
	# Page 4 writes into the page-2 result root: use a Chinese path with spaces
	# so the shared-root logic is exercised on a non-trivial folder name.
	var output_root := TestPaths.temp_dir().path_join("psyml 输出 预测 %d" % Time.get_ticks_usec())
	page.set_output_root(output_root)
	assert(main.output_edit.text == output_root)
	assert(page.output_edit.text == output_root)
	assert(page.output_help.visible and page.output_help.text == main.tr("PREDICTION_OUTPUT_HELP"))
	# Two operations must never share one run folder, even in the same millisecond.
	var frozen_a: Dictionary = OutputLocation.create_run_directory(output_root, OutputLocation.PREDICTION)
	var frozen_b: Dictionary = OutputLocation.create_run_directory(output_root, OutputLocation.PREDICTION)
	assert(frozen_a.error.is_empty() and frozen_b.error.is_empty(), str(frozen_a) + str(frozen_b))
	assert(str(frozen_a.path) != str(frozen_b.path))
	assert(DirAccess.dir_exists_absolute(str(frozen_a.path)) and DirAccess.dir_exists_absolute(str(frozen_b.path)))
	assert(main.tabs.get_tab_count() == 5 and main.tabs.is_tab_hidden(1))
	assert(main.tabs.get_tab_title(4) == "4  模型与预测")
	assert(page.predict_button.disabled and page.model_button.disabled)
	assert(not page.data_button.disabled)
	var directory := TestPaths.temp_dir().path_join("psyml-prediction-ui-%d" % Time.get_ticks_usec())
	DirAccess.make_dir_recursive_absolute(directory)
	# Exercise each task through real full-data training, disk save and GUI inference.
	for task in ["classification", "regression"]:
		var input := ProjectSettings.globalize_path("res://../examples/quickstart/" + task + "_train.csv")
		var prediction_input := ProjectSettings.globalize_path("res://../examples/quickstart/" + task + "_predict.csv")
		var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../examples/quickstart/" + task + "_config.json"))
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
			page.load_data(prediction_input)
			await _wait(page)
			assert(page.predict_button.disabled)
		page.load_model(model_path)
		await _wait(page)
		page.load_data(prediction_input)
		await _wait(page)
		assert(page.error_message.is_empty(), page.error_message)
		assert(page.compatibility.compatible and not page.predict_button.disabled)
		assert(page.data.row_count > 0 and page.required_tree.get_root().get_first_child() != null)
		if task == "classification":
			# A missing or unwritable root must be a visible error, never a
			# silent fallback to the hidden user:// folder.
			var user_before := _user_output_state()
			page.set_output_root("")
			page.run_prediction()
			assert(page.error_message == main.tr("PREDICTION_OUTPUT_REQUIRED"), page.error_message)
			assert(page.result_path.is_empty() and page.predictions.is_empty())
			# Without a completed run there is no folder to open: a visible error
			# and a disabled button instead of opening the CSV or any fallback.
			assert(page.prediction_folder_button.disabled)
			opened.clear()
			page.open_prediction_folder()
			assert(page.error_message == main.tr("PREDICTION_NO_ARTIFACT"), page.error_message)
			assert(opened.is_empty())
			page.error_message = ""
			var blocked_root := directory.path_join("blocked-root")
			_write(blocked_root, "not a directory")
			page.set_output_root(blocked_root)
			page.run_prediction()
			assert(page.error_message == main.tr("OUTPUT_NOT_WRITABLE"), page.error_message)
			assert(page.result_path.is_empty())
			page.error_message = ""
			assert(_user_output_state() == user_before, "prediction must not fall back to user://")
			page.set_output_root(output_root)
		page.run_prediction()
		assert(page.predict_button.disabled)
		await _wait(page)
		assert(page.error_message.is_empty(), page.error_message)
		assert(not page.prediction_folder_button.disabled and not page.predictions.is_empty())
		assert(page.predictions.row_count == 10)
		assert(page.predictions.columns[0].name == "sample_id")
		# The artifact is really written under the selected root, in a new
		# prediction/run_* folder owned by this operation; the model folder is
		# never used to infer where a page-4 result belongs.
		var first_path: String = page.result_path
		assert(first_path.begins_with(output_root + "/"), first_path)
		assert(first_path.get_base_dir().get_base_dir() == output_root.path_join("prediction"), first_path)
		assert(first_path.get_base_dir().get_file().begins_with("run_"), first_path)
		assert(FileAccess.file_exists(first_path), first_path)
		assert(not first_path.begins_with(str(config.output_dir)), "page 4 must not write into the model folder")
		# The run folder holds one artifact only, a plain CSV the user can
		# open directly; no Parquet is written next to it.
		assert(first_path.get_file() == "predictions.csv", first_path)
		var artifact_names := DirAccess.open(first_path.get_base_dir()).get_files()
		assert(artifact_names.size() == 1 and artifact_names[0] == "predictions.csv", str(artifact_names))
		# Opening targets exactly this successful run folder, never the CSV file.
		assert(not page.prediction_folder_button.disabled)
		opened.clear()
		page.open_prediction_folder()
		assert(opened.size() == 1 and opened[0] == first_path.get_base_dir(), str(opened))
		assert(page.error_message.is_empty(), page.error_message)
		# Changing the root only affects later operations; the earlier artifact stays.
		var first_size := _file_size(first_path)
		var second_root := TestPaths.temp_dir().path_join("psyml 换目录 %d %s" % [Time.get_ticks_usec(), task])
		page.set_output_root(second_root)
		page.run_prediction()
		await _wait(page)
		assert(page.error_message.is_empty(), page.error_message)
		assert(page.result_path != first_path and page.result_path.begins_with(second_root + "/"), page.result_path)
		assert(
			FileAccess.file_exists(first_path) and _file_size(first_path) == first_size,
			"an earlier successful prediction must be preserved")
		page.set_output_root(output_root)
		var names: Array = []
		for column in page.predictions.columns:
			names.append(column.name)
		if task == "classification":
			assert("predicted_class" in names and "probability_0" in names and "probability_1" in names)
		else:
			assert("predicted_value" in names and not "probability_0" in names)
		for locale in range(3):
			main._on_language_selected(locale)
			assert(not page.predict_button.disabled and not page.prediction_folder_button.disabled)
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
		if task == "classification":
			# The GUI reads back the CSV it wrote, so the preview
			# matches the artifact exactly, including Chinese text, commas inside
			# quoted fields and empty cells. The removed export dialog has no
			# replacement: opening the run folder is the only delivery action.
			var round_trip := directory.path_join("csv 往返,特殊.csv")
			_write(round_trip, "new_id,category,score,note\n甲,\"乙,副\",1.5,\n201,C,-1.2,\"含,逗号\"\n")
			page.load_data(round_trip)
			await _wait(page)
			assert(page.compatibility.compatible)
			page.run_prediction()
			await _wait(page)
			assert(page.error_message.is_empty(), page.error_message)
			assert(page.result_path.get_file() == "predictions.csv", page.result_path)
			assert(page.result_path.get_base_dir().begins_with(output_root + "/"), page.result_path)
			var csv_file := FileAccess.open(page.result_path, FileAccess.READ)
			assert(csv_file != null, page.result_path)
			var headers := csv_file.get_csv_line()
			for index in range(4):
				assert(headers[index] == ["new_id", "category", "score", "note"][index], str(headers))
			var predicted_index := headers.find("predicted_class")
			var probability_index := headers.find("probability_0")
			assert(predicted_index == 4 and probability_index == 5, str(headers))
			assert(page.predictions.columns.size() == headers.size())
			for index in range(headers.size()):
				assert(page.predictions.columns[index].name == headers[index], str(headers))
			var first_row := csv_file.get_csv_line()
			var second_row := csv_file.get_csv_line()
			assert(first_row[0] == "甲" and first_row[1] == "乙,副" and first_row[3] == "", str(first_row))
			assert(second_row[2] == "-1.2" and second_row[3] == "含,逗号", str(second_row))
			assert(not first_row[predicted_index].is_empty(), str(first_row))
			assert(first_row[probability_index].is_valid_float(), str(first_row))
			assert(str(page.predictions.sample[0].category) == "乙,副", str(page.predictions.sample))
			assert(str(page.predictions.sample[1].note) == "含,逗号", str(page.predictions.sample))
			csv_file.close()
			# A run folder that no longer exists must be a visible error, never a
			# silent open of the CSV or of another folder.
			var saved_path: String = page.result_path
			page.result_path = directory.path_join("missing-run").path_join("predictions.csv")
			opened.clear()
			page.open_prediction_folder()
			assert(page.error_message == main.tr("PREDICTION_NO_ARTIFACT"), page.error_message)
			assert(opened.is_empty())
			page.error_message = ""
			page.result_path = saved_path
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
		assert(page.predictions.is_empty() and page.prediction_folder_button.disabled and page.predict_button.disabled)
		assert(not page.result_tree.column_titles_visible)
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
	assert(page.predictions.row_count == 2 and not page.prediction_folder_button.disabled)
	opened.clear()
	page.open_prediction_folder()
	assert(opened.size() == 1 and opened[0] == page.result_path.get_base_dir(), str(opened))
	page.mapping_options[0].item_selected.emit(1)
	assert(page.predict_button.disabled and page.prediction_folder_button.disabled)
	# Real state transitions of the shared readiness condition.
	await _prediction_delivery_states(main, page, opened, directory, manual, mapping_data)
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
