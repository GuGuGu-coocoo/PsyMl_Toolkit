extends SceneTree

func _initialize() -> void:
	call_deferred("_capture")

func _capture() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	root.size = Vector2i(1000, 700)
	var output := OS.get_environment("PSYML_SCREENSHOT_DIR")
	DirAccess.make_dir_recursive_absolute(output)
	var directory := "/tmp/PsyML 长路径 avec espaces/" + "research_session_".repeat(7)
	DirAccess.make_dir_recursive_absolute(directory)
	var path := directory.path_join("long_variables.tsv")
	var file := FileAccess.open(path, FileAccess.WRITE)
	var long_target := "outcome_研究变量_mesure_".repeat(7)
	file.store_string("score\t" + long_target + "\tparticipant\n")
	for i in range(24):
		file.store_string("%s\t%s\tg%s\n" % [i / 24.0, i % 2, i / 2])
	file.close()
	main._on_file_selected(path)
	var deadline := Time.get_ticks_msec() + 15000
	while main.preview_payload.is_empty() and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	assert(not main.preview_payload.is_empty())
	main.target_option.select(1)
	main.group_option.select(3)
	main._on_column_role_changed()
	for locale in [0, 1, 2]:
		main._on_language_selected(locale)
		for page in [0, 1]:
			main.tabs.current_tab = page
			await create_timer(0.2).timeout
			await process_frame
			root.get_viewport().get_texture().get_image().save_png(
				output.path_join("long-%d-%d.png" % [locale, page]))
	main.tabs.current_tab = 2
	main.output_edit.text = "/tmp/psyml-focus-" + str(Time.get_ticks_usec())
	main._refresh_review()
	main.feature_list.select(0, false)
	main._refresh_review()
	main.refresh_review_button.grab_focus()
	await process_frame
	await process_frame
	root.get_viewport().get_texture().get_image().save_png(output.path_join("keyboard-focus.png"))
	print("PSYML_LONG_NAMES_OK")
	quit(0)
