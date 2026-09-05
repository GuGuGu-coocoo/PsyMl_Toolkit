extends SceneTree

var failures := 0

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failures += 1

func run() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var example := ProjectSettings.globalize_path("res://../examples/synthetic/classification_config.json")
	check(main.configuration_io.import_file(example), "Import example failed")
	var imported: Dictionary = main._build_config()
	check(imported.target_column == "target", "Target not restored")
	check(imported.model_names == ["decision_tree"], "Model not restored")
	check(imported.group_column == "participant", "Group not restored")
	check(imported.feature_columns == ["score", "category"], "Features not restored")
	imported.primary_validation = null
	imported.validation_strategies = ["group_k_fold", "holdout"]
	imported.validation_strategy = "group_k_fold"
	imported.random_seed = 17
	imported.test_size = 0.3
	imported.include_data_hash = false
	imported.model_params = {"max_depth": 3}
	imported.tuning_mode = "custom"
	imported.parameter_grids = {"decision_tree": {"criterion": ["gini", "entropy"], "max_depth": [2, 4]}}
	imported.figure_types = []
	var temp := OS.get_temp_dir().path_join("psyml_config_import_test.json")
	var file := FileAccess.open(temp, FileAccess.WRITE)
	file.store_string(JSON.stringify(imported))
	file.close()
	check(main.configuration_io.import_file(temp), "Custom import failed")
	var actual: Dictionary = main._build_config()
	for key in ["primary_validation", "validation_strategies", "random_seed", "test_size", "include_data_hash", "model_params", "parameter_grids", "figure_types"]:
		check(JSON.parse_string(JSON.stringify(actual[key])) == JSON.parse_string(JSON.stringify(imported[key])), "Changed field: " + key + " " + str(actual[key]))
	for language in [1, 2, 0]:
		main._on_language_selected(language)
		actual = main._build_config()
		check(JSON.parse_string(JSON.stringify(actual.parameter_grids)) == JSON.parse_string(JSON.stringify(imported.parameter_grids)), "Locale changed grid")
	check(main.configuration_io.save_file(temp), "Save failed")
	check(main.configuration_io.import_file(temp), "Reimport failed")
	check(main.configuration_io.import_file(ProjectSettings.globalize_path("res://../examples/synthetic/regression_config.json")), "Regression import failed")
	actual = main._build_config()
	check(actual.task == "regression" and actual.model_params == {}, "Task retained old parameters")
	file = FileAccess.open(temp, FileAccess.WRITE)
	file.store_string('{"schema_version":"99"}')
	file.close()
	check(not main.configuration_io.import_file(temp), "Invalid schema accepted")
	check(main._build_config() == actual, "Invalid import changed configuration")
	DirAccess.remove_absolute(temp)
	print("PSYML_CONFIG_IMPORT_OK")
	quit(1 if failures else 0)
