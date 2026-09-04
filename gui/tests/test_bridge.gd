extends SceneTree


func _initialize() -> void:
	PsyMLI18n.install()
	for locale in PsyMLI18n.LOCALES:
		TranslationServer.set_locale(locale)
		assert(TranslationServer.translate("RUN") != "RUN")
		assert(TranslationServer.translate("LANGUAGE") != "LANGUAGE")
	var bridge := CoreBridge.new()
	root.add_child(bridge)
	var capabilities := bridge.execute_json_sync(PackedStringArray(["capabilities"]))
	assert(capabilities.get("schema_version") == "1.0")
	assert("logistic_regression" in capabilities.models.classification)
	var fixture := ProjectSettings.globalize_path("res://tests/fixtures/sample.tsv")
	var preview := bridge.execute_json_sync(
		PackedStringArray(["preview", "--input", fixture, "--include-sample", "--rows", "2"])
	)
	assert(preview.row_count == 30)
	assert(preview.columns.size() == 4)
	assert(preview.sample.size() == 2)
	print("PSYML_GODOT_BRIDGE_OK")
	quit(0)
