extends SceneTree


func _initialize() -> void:
	call_deferred("_run_test")


func _choose_dummy(main: Control) -> void:
	for index in range(main.model_list.item_count):
		main.model_list.deselect(index)
		if main.model_list.get_item_metadata(index) == "dummy":
			main.model_list.select(index, false)
	main._populate_parameter_editor()


func _run_test() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	main.tuning_option.select(2)
	_choose_dummy(main)
	main.parameter_controls["dummy::strategy"].values.text = '["prior"]'
	main.task_option.select(1)
	main._on_task_changed()
	_choose_dummy(main)
	var regression = JSON.parse_string(main.parameter_controls["dummy::strategy"].values.text)
	if regression != ["mean", "median"]:
		push_error("Classification parameters leaked into regression: " + str(regression))
		quit(1)
		return
	main.parameter_controls["dummy::strategy"].values.text = '["median"]'
	main.task_option.select(0)
	main._on_task_changed()
	_choose_dummy(main)
	if JSON.parse_string(main.parameter_controls["dummy::strategy"].values.text) != ["prior"]:
		push_error("Classification custom values were not restored independently")
		quit(1)
		return
	main._on_language_selected(1)
	assert(JSON.parse_string(main.parameter_controls["dummy::strategy"].values.text) == ["prior"])
	main.tuning_option.select(1)
	main._populate_parameter_editor()
	main.tuning_option.select(2)
	main._populate_parameter_editor()
	assert(JSON.parse_string(main.parameter_controls["dummy::strategy"].values.text) == ["prior"])
	print("PSYML_PARAMETER_CONTEXT_OK")
	quit(0)
