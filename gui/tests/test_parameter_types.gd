extends SceneTree

const TestPaths = preload("res://tests/test_paths.gd")

var failures := 0


func _initialize() -> void:
	call_deferred("run")


func check(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failures += 1


func check_type(value, expected_type: int, message: String) -> void:
	check(
		typeof(value) == expected_type,
		"%s (got %s: %s)" % [message, type_string(typeof(value)), str(value)]
	)


func run() -> void:
	# 1. The JSON reader keeps integer counts and decimal fractions apart.
	var parsed = CoreBridge.parse_json_document(
		'{"verbose": 0, "n_jobs": 1, "max_features": 1, "max_samples": 1.0, "min_samples_leaf": 0.25}'
	)
	check(parsed is Dictionary, "Typed parse rejected a valid document")
	check_type(parsed.get("verbose"), TYPE_INT, "verbose=0 must stay an integer")
	check_type(parsed.get("n_jobs"), TYPE_INT, "n_jobs=1 must stay an integer")
	check_type(parsed.get("max_features"), TYPE_INT, "max_features=1 must stay an integer")
	check_type(parsed.get("max_samples"), TYPE_FLOAT, "max_samples=1.0 must stay a float")
	check_type(parsed.get("min_samples_leaf"), TYPE_FLOAT, "0.25 must stay a float")
	check(parsed.get("max_features") == 1.0, "Integer value changed")
	check(CoreBridge.parse_json_document("progress noise") == null, "Invalid JSON accepted")

	# 2. Real window: fixed parameters keep their types through the review build.
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	# Test setup is independent of the host desktop Documents directory.
	main.output_edit.text = TestPaths.temp_dir().path_join("psyml test output")
	var example := CoreBridge.quickstart_directory().path_join("classification_config.json")
	check(main.configuration_io.import_file(example), "Import example failed")
	main.configuration_io.fixed_parameters.text = (
		'{"max_features": 1, "max_samples": 1.0, "verbose": 0, "n_jobs": 1, '
		+ '"min_samples_leaf": 1, "min_samples_split": 0.25}'
	)
	var built: Dictionary = main._build_config()
	check(not built.has("error"), "Review rejected the edited parameters: " + str(built.get("error")))
	var params: Dictionary = built.model_params
	check_type(params.get("max_features"), TYPE_INT, "Fixed max_features=1 lost its integer type")
	check_type(params.get("max_samples"), TYPE_FLOAT, "Fixed max_samples=1.0 lost its float type")
	check_type(params.get("verbose"), TYPE_INT, "Fixed verbose=0 lost its integer type")
	check_type(params.get("n_jobs"), TYPE_INT, "Fixed n_jobs=1 lost its integer type")
	check_type(params.get("min_samples_leaf"), TYPE_INT, "Fixed min_samples_leaf=1 lost its integer type")
	check_type(params.get("min_samples_split"), TYPE_FLOAT, "Fixed fraction lost its float type")

	# 3. Custom parameter controls keep the typed grid the user wrote.
	main.configuration_io.choose(main.tuning_option, "tuning_custom")
	main._populate_parameter_editor()
	var depth_key := "decision_tree::max_depth"
	check(main.parameter_controls.has(depth_key), "Custom control for max_depth is missing")
	main.parameter_controls[depth_key].values.text = "[1, 1.0]"
	built = main._build_config()
	var grid: Dictionary = built.parameter_grids["decision_tree"]
	check_type(grid["max_depth"][0], TYPE_INT, "Grid max_depth=1 lost its integer type")
	check_type(grid["max_depth"][1], TYPE_FLOAT, "Grid max_depth=1.0 lost its float type")

	# 4. Extra grids keep number types too.
	main.configuration_io.extra_grids.text = '{"decision_tree": {"min_samples_leaf": [1, 0.25]}}'
	built = main._build_config()
	grid = built.parameter_grids["decision_tree"]
	check_type(grid["min_samples_leaf"][0], TYPE_INT, "Extra grid integer lost its type")
	check_type(grid["min_samples_leaf"][1], TYPE_FLOAT, "Extra grid fraction lost its type")

	# 5. Saving writes the original number forms and reimport restores them.
	var temp := TestPaths.temp_dir().path_join("psyml_parameter_types_test.json")
	check(main.configuration_io.save_file(temp), "Save failed")
	var raw = CoreBridge.parse_json_document(FileAccess.get_file_as_string(temp))
	check(raw is Dictionary, "Saved configuration is not readable JSON")
	check_type(raw.model_params["max_features"], TYPE_INT, "Saved JSON wrote max_features as a float")
	check_type(raw.model_params["max_samples"], TYPE_FLOAT, "Saved JSON lost the decimal fraction")
	check(main.configuration_io.import_file(temp), "Reimport failed")
	built = main._build_config()
	check_type(built.model_params["max_features"], TYPE_INT, "Reimport changed max_features")
	check_type(built.model_params["max_samples"], TYPE_FLOAT, "Reimport changed max_samples")
	check_type(
		built.parameter_grids["decision_tree"]["max_depth"][1],
		TYPE_FLOAT,
		"Reimport changed the grid float",
	)

	# 6. Switching languages keeps every type.
	for language in [1, 2, 0]:
		main._on_language_selected(language)
		built = main._build_config()
		check_type(built.model_params["max_features"], TYPE_INT, "Language switch changed max_features")
		check_type(
			built.parameter_grids["decision_tree"]["max_depth"][1],
			TYPE_FLOAT,
			"Language switch changed the grid float",
		)

	DirAccess.remove_absolute(temp)
	print("PSYML_PARAMETER_TYPES_OK")
	quit(1 if failures else 0)
