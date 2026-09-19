extends SceneTree
## Bridge probes: path canonicalization for core-reported Windows paths,
## fragmented/Unicode/no-trailing-newline stream framing, JSON noise handling
## and the retained terminal event, plus the real capabilities/preview calls.


func _initialize() -> void:
	PsyMLI18n.install()
	for locale in PsyMLI18n.LOCALES:
		TranslationServer.set_locale(locale)
		assert(TranslationServer.translate("RUN") != "RUN")
		assert(TranslationServer.translate("LANGUAGE") != "LANGUAGE")
	TranslationServer.set_locale("zh_CN")
	_test_canonical_paths()
	_test_utf8_prefixes()
	_test_analysis_framing()
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


func _expect(condition: bool, message: String) -> void:
	if condition:
		return
	printerr("PSYML_BRIDGE_FAILURE: " + message)
	quit(1)


func _test_canonical_paths() -> void:
	# Windows pathlib reports `\` separators, Godot joins with `/`; the same
	# directory must compare equal after canonicalization on every platform.
	_expect(
		CoreBridge.canonical_path("D:\\a\\b\\run_1") == CoreBridge.canonical_path("D:/a/b/run_1"),
		"windows result directory must canonicalize to the Godot form"
	)
	_expect(
		CoreBridge.canonical_path("D:\\a\\b\\run_1\\result.json").get_base_dir()
			== CoreBridge.canonical_path("D:/a/b/run_1"),
		"windows result.json base directory must match the configured output"
	)
	_expect(
		CoreBridge.canonical_path("C:\\Users\\runner admin\\结果 目录\\result.json").get_base_dir()
			== CoreBridge.canonical_path("C:/Users/runner admin/结果 目录"),
		"windows paths with spaces and Chinese characters must canonicalize"
	)
	_expect(
		CoreBridge.canonical_path("/tmp/a/b/run_1") == "/tmp/a/b/run_1",
		"posix paths must stay unchanged"
	)


func _test_utf8_prefixes() -> void:
	var complete := "中文abc".to_utf8_buffer()
	_expect(
		CoreBridge.utf8_complete_prefix_length(complete) == complete.size(),
		"complete text must keep every byte"
	)
	_expect(CoreBridge.utf8_complete_prefix_length(PackedByteArray()) == 0, "empty buffer")
	# 中 is 3 bytes; splitting inside it must keep the partial sequence back.
	var split := complete.slice(0, 4)
	_expect(
		CoreBridge.utf8_complete_prefix_length(split) == 3,
		"partial trailing multi-byte sequence must stay buffered"
	)
	_expect(
		split.slice(0, CoreBridge.utf8_complete_prefix_length(split)).get_string_from_utf8() == "中",
		"decoded prefix must be exact"
	)
	var pending := split.slice(CoreBridge.utf8_complete_prefix_length(split))
	pending.append_array(complete.slice(4))
	_expect(pending.get_string_from_utf8() == "文abc", "buffered bytes must decode exactly")
	_expect(
		CoreBridge.parse_json_document("progress noise") == null,
		"non-JSON noise must be rejected without engine errors"
	)
	_expect(
		CoreBridge.parse_json_document('{"ok": true}').get("ok") == true,
		"valid JSON documents must still parse"
	)


func _test_analysis_framing() -> void:
	var bridge := CoreBridge.new()
	root.add_child(bridge)
	var events: Array = []
	bridge.event_received.connect(func(payload: Dictionary) -> void: events.append(payload))
	# A JSON event split mid-token is only dispatched once its line is complete.
	bridge._consume_analysis_stdout('{"schema_version": "1.0", "event": "prog')
	_expect(events.is_empty(), "partial event must not be parsed")
	bridge._consume_analysis_stdout('ress", "progress": 0.4}')
	_expect(events.is_empty(), "event without a line end must wait")
	bridge._consume_analysis_stdout("\n")
	_expect(
		events.size() == 1 and events[0].get("progress") == 0.4,
		"fragmented event must be delivered exactly once"
	)
	bridge._consume_analysis_stdout("plain progress noise\n\n")
	_expect(events.size() == 1, "noise must not be emitted as an event")
	bridge._consume_analysis_stdout(
		'{"schema_version": "1.0", "event": "completed", "result_path": "D:\\\\a\\\\b\\\\result.json"}\n'
	)
	_expect(
		bridge._saw_terminal_event and bridge._pending_terminal_event.get("event") == "completed",
		"the last completed event before exit must be retained"
	)
	_expect(events.size() == 1, "terminal events are held back until the process exits")
	bridge.queue_free()
