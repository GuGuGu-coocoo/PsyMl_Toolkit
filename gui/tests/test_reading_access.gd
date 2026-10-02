extends SceneTree
## Selection/copy, responsive layout and non-modal About regression coverage.

var opened_urls: Array[String] = []


func _initialize() -> void:
	call_deferred("_run")


func _open(url: String) -> int:
	opened_urls.append(url)
	return OK


func _settle() -> void:
	for frame in range(4):
		await process_frame


func _run() -> void:
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await _settle()
	assert(ProjectSettings.get_setting("display/window/stretch/aspect") == "expand")
	assert(root.content_scale_aspect == Window.CONTENT_SCALE_ASPECT_EXPAND)
	main.output_edit.text = preload("res://tests/test_paths.gd").temp_dir().path_join("reading-access-%s" % Time.get_ticks_usec())
	assert(main.configuration_io.import_file(CoreBridge.quickstart_directory().path_join("classification_coefficients_config.json")))
	main._on_run_pressed()
	assert(main.is_analysis_running)
	main.about_ui.show_panel()
	main.about_ui.close_panel()
	assert(main.is_analysis_running)
	var deadline := Time.get_ticks_msec() + 120000
	while main.is_analysis_running and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	assert(main.status_key == "COMPLETED", main.status_detail)
	var result: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(main.last_result_path))
	var page = main.prediction_page
	page.trust.button_pressed = true
	page.load_model(main.last_result_dir.path_join(result.model_export.model_path))
	while page.busy and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	page.load_data(CoreBridge.quickstart_directory().path_join("classification_predict.csv"))
	while page.busy and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	page.run_prediction()
	while page.busy and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	assert(page.error_message.is_empty(), page.error_message)
	page.run_coefficients()
	while page.coefficients_busy and Time.get_ticks_msec() < deadline:
		await create_timer(0.05).timeout
	assert(page.coefficients_error.is_empty(), page.coefficients_error)
	var original_config: Dictionary = main._build_config()
	var original_state: bool = main.is_analysis_running
	var about = main.about_ui
	about.open_url = _open
	var expected_readmes := ["README_ZH.md", "README.md", "README_FR.md"]
	var languages := ["ZH", "EN", "FR"]
	for locale in range(3):
		main._on_language_selected(locale)
		await _settle()
		main.language_option.grab_focus()
		about.show_panel()
		about.show_panel()
		await _settle()
		assert(about.visible)
		assert(root.gui_get_focus_owner() == about.close_button)
		assert(not about.entry.text.is_empty() and about.entry.text != "ABOUT")
		assert(about.note.text == main.tr("ABOUT_NETWORK"))
		var menu: PopupMenu = main.configuration_io.notice.get_menu()
		assert(menu.get_item_text(menu.get_item_index(RichTextLabel.MENU_COPY)) == main.tr("COPY_SELECTION"))
		var urls: Dictionary = about.link_urls()
		assert(urls.ABOUT_PROJECT == about.REPOSITORY)
		assert(urls.ABOUT_README == about.REPOSITORY + "/blob/main/" + expected_readmes[locale])
		assert(urls.ABOUT_GUIDE == about.REPOSITORY + "/blob/main/docs/RESEARCHER_GUIDE_" + languages[locale] + ".md")
		for key in urls:
			about.open_link(key)
			assert(opened_urls.back() == urls[key])
		assert("0.3.1" in about.version.text)
		# Opening a link or switching language must not modify the analysis state.
		assert(main.is_analysis_running == original_state)
		assert(main._build_config() == original_config, "Config changed: %s -> %s" % [original_config, main._build_config()])
		about.close_button.pressed.emit()
		assert(not about.visible)
		assert(root.gui_get_focus_owner() == main.language_option)
		about.show_panel()
		var escape := InputEventAction.new()
		escape.action = "ui_cancel"
		escape.pressed = true
		about._unhandled_key_input(escape)
		assert(not about.visible)
		about.open_url = func(_url): return ERR_CANT_OPEN
		about.open_link("ABOUT_GUIDE")
		assert(main.tr("ABOUT_OPEN_FAILED") in about.note.text)
		assert(urls.ABOUT_GUIDE in about.note.text)
		about.open_url = _open
		for window_size in [Vector2i(1280, 800), Vector2i(1280, 720), Vector2i(1000, 700), Vector2i(1920, 800)]:
			root.size = window_size
			await _settle()
			assert(main.size.is_equal_approx(root.get_visible_rect().size))
			assert(main.get_node("Background").size.is_equal_approx(main.size))
			for page_index in [0, 2, 3, 4]:
				main.tabs.current_tab = page_index
				await _settle()
				for node in main.find_children("*", "Button", true, false):
					if node.is_visible_in_tree():
						var rect: Rect2 = node.get_global_rect()
						if rect.end.x > main.size.x + 1:
							for large in main.get_node("%DataContent").find_children("*", "Control", true, false):
								if large.get_combined_minimum_size().x > 500:
									print("LARGE ", large.name, " ", large.get_class(), " ", large.get_combined_minimum_size())
							var ancestor: Node = node
							while ancestor is Control:
								print("LAYOUT ", ancestor.name, " ", ancestor.size, " min ", ancestor.get_combined_minimum_size())
								ancestor = ancestor.get_parent()
						assert(rect.position.x >= -1 and rect.end.x <= main.size.x + 1, "%s rect=%s main=%s parent_min=%s overflows at %s / %s" % [node.name, rect, main.size, node.get_parent().get_combined_minimum_size(), window_size, languages[locale]])
				await _capture("%s-%sx%s-page%s" % [languages[locale], window_size.x, window_size.y, page_index])
				if window_size == Vector2i(1000, 700):
					var scroller = main.tabs.get_tab_control(page_index)
					scroller.scroll_vertical = 100000
					await _settle()
					await _capture("%s-minimum-page%s-bottom" % [languages[locale], page_index])
					if page_index == 4:
						page.coefficients_summary.select_all()
						await _capture(languages[locale] + "-copy")
						page.coefficients_summary.deselect()
					scroller.scroll_vertical = 0
			about.show_panel()
			await _settle()
			assert(Rect2(Vector2.ZERO, main.size).encloses(about.get_global_rect()), "About %s outside %s" % [about.get_global_rect(), main.size])
			await _capture("%s-%sx%s-about" % [languages[locale], window_size.x, window_size.y])
			# This panel is not a modal Window: controls outside it remain active.
			main.tabs.current_tab = 0
			main.language_option.grab_focus()
			about.close_panel()
			assert(root.gui_get_focus_owner() == main.language_option)
			assert(main._build_config() == original_config, "Config changed: %s -> %s" % [original_config, main._build_config()])
	main._on_language_selected(1)
	main.tabs.current_tab = 3
	await _settle()
	for control in [main.data_summary_label, main.best_result_label, main.warnings_text,
		main.data_check_ui.summary_label, main.interpretation_ui.baseline_label,
		main.permutation_ui.status_label, main.result_coefficients_ui.detail_label,
		main.prediction_page.result_summary, main.prediction_page.explain_summary,
		main.prediction_page.coefficients_outputs]:
		assert(control is RichTextLabel and control.selection_enabled and control.context_menu_enabled)
		assert(control.shortcut_keys_enabled and not control.scroll_active)
		assert(control.mouse_force_pass_scroll_events)
	assert(main.get_node("%ResultsHeading") is Label)
	assert(main.get_node("%ResultsHeading").tooltip_text.is_empty())
	# Current visible text is copied as plain Unicode; hidden old content is omitted.
	main.best_result_label.text = "Alpha βeta 结果\nScore 0.73"
	assert(main._copy_text(main.best_result_label) == "Alpha βeta 结果\nScore 0.73")
	main.best_result_label.select_all()
	assert(main.best_result_label.get_selected_text() == main.best_result_label.text)
	var tree: Tree = main.metrics_tree
	tree.clear()
	tree.columns = 2
	tree.column_titles_visible = true
	tree.set_column_title(0, "Metric")
	tree.set_column_title(1, "Value")
	var row := tree.create_item(tree.create_item())
	row.set_text(0, "R²")
	row.set_text(1, "0.73")
	assert(main._copy_text(tree) == "Metric\tValue\nR²\t0.73")
	main.best_result_label.hide()
	assert(main._copy_section_text([main.best_result_label, tree]) == main._copy_text(tree))
	assert(not main.copy_buttons[main.best_result_label].visible)
	main.best_result_label.show()
	assert(main.copy_buttons[main.best_result_label].visible)
	var bindings := tree.gui_input.get_connections().size()
	main._configure_readable_controls(main)
	main._configure_readable_controls(main)
	assert(tree.gui_input.get_connections().size() == bindings)
	assert(not tree.mouse_force_pass_scroll_events)
	# Real clipboard checks run only with a display; headless CI checks payloads.
	if DisplayServer.get_name() != "headless":
		main.copy_buttons[main.best_result_label].pressed.emit()
		assert(DisplayServer.clipboard_get() == main.best_result_label.text)
		main.copy_buttons[tree].pressed.emit()
		assert(DisplayServer.clipboard_get() == "Metric\tValue\nR²\t0.73")
		print("PSYML_READING_CLIPBOARD_OK")
		root.mode = Window.MODE_FULLSCREEN
		await _settle()
		assert(main.get_node("Background").size.is_equal_approx(root.get_visible_rect().size))
		await _capture("fullscreen")
		root.mode = Window.MODE_WINDOWED
		await _settle()
		print("PSYML_READING_FULLSCREEN_OK")
	print("PSYML_READING_ACCESS_OK")
	quit(0)


func _capture(label: String) -> void:
	var directory := OS.get_environment("PSYML_SCREENSHOT_DIR")
	if directory.is_empty() or DisplayServer.get_name() == "headless":
		return
	DirAccess.make_dir_recursive_absolute(directory)
	await RenderingServer.frame_post_draw
	assert(root.get_texture().get_image().save_png(directory.path_join(label + ".png")) == OK)
