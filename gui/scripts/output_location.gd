extends RefCounted
## One shared result root for page 2 (training) and page 4 (prediction/SHAP/coefficients).
##
## Page 4 never infers a training folder from the model file and never falls back
## to the hidden `user://` application-data folder. Every operation resolves the
## page-2 result root (`main.output_edit`) when it starts, freezes that path for
## its whole lifetime and writes into a unique new run subdirectory of
## `prediction/`, `explanation/` or `coefficients/`.

const PREDICTION := "prediction"
const EXPLANATION := "explanation"
const COEFFICIENTS := "coefficients"

const STAGING_PREFIXES := {
	EXPLANATION: ".psyml-explanation-staging-",
	COEFFICIENTS: ".psyml-coefficients-staging-",
}

const RUN_FOLDER_ATTEMPTS := 1000


static func shared_root(main) -> Dictionary:
	# The result root is one setting for both pages; an empty or relative value
	# is refused instead of being replaced by a hidden default.
	var text := ""
	if main != null and main.output_edit != null:
		text = main.output_edit.text.strip_edges()
	if text.is_empty() or not text.is_absolute_path():
		return {"path": "", "error": "PREDICTION_OUTPUT_REQUIRED"}
	return {"path": text, "error": ""}


static func create_run_directory(root: String, family: String) -> Dictionary:
	# Freeze `<root>/<family>/run_<timestamp>_<usec>`: the name is checked to be
	# new so two operations in the same millisecond still get separate folders
	# and no existing artifact can be overwritten.
	var family_root := root.path_join(family)
	if _is_file(root) or _is_file(family_root):
		return {"path": "", "root": family_root, "error": "OUTPUT_NOT_WRITABLE"}
	if not _ensure_directory(family_root):
		return {"path": "", "root": family_root, "error": "OUTPUT_NOT_WRITABLE"}
	for attempt in range(RUN_FOLDER_ATTEMPTS):
		var candidate := family_root.path_join(_run_name(attempt))
		if DirAccess.dir_exists_absolute(candidate) or FileAccess.file_exists(candidate):
			continue
		if not _ensure_directory(candidate):
			return {"path": "", "root": family_root, "error": "OUTPUT_NOT_WRITABLE"}
		return {"path": candidate, "root": family_root, "error": ""}
	return {"path": "", "root": family_root, "error": "OUTPUT_NOT_WRITABLE"}


static func cleanup_staging(family_root: String, family: String) -> void:
	# Remove only this tool's own incomplete staging folders, left behind when a
	# cancelled or killed process skipped its own cleanup. Run folders and their
	# completed artifacts are never touched.
	var prefix := str(STAGING_PREFIXES.get(family, ""))
	if prefix.is_empty() or not DirAccess.dir_exists_absolute(family_root):
		return
	var directory := DirAccess.open(family_root)
	if directory == null:
		return
	for name in directory.get_directories():
		var path := family_root.path_join(name)
		if name.begins_with(prefix):
			DirAccess.remove_absolute(path)
			continue
		_remove_staging_children(path, prefix)


static func _remove_staging_children(directory_path: String, prefix: String) -> void:
	var directory := DirAccess.open(directory_path)
	if directory == null:
		return
	for name in directory.get_directories():
		if name.begins_with(prefix):
			DirAccess.remove_absolute(directory_path.path_join(name))


static func _run_name(attempt: int) -> String:
	var stamp := Time.get_datetime_string_from_system().replace(":", "-")
	var name := "run_%s_%d" % [stamp, Time.get_ticks_usec()]
	if attempt > 0:
		name += "_%d" % attempt
	return name


static func _ensure_directory(path: String) -> bool:
	if DirAccess.dir_exists_absolute(path):
		return true
	DirAccess.make_dir_recursive_absolute(path)
	return DirAccess.dir_exists_absolute(path)


static func _is_file(path: String) -> bool:
	# A file in the way of a directory is reported before any engine-level
	# mkdir error can be printed for an expected user-facing failure.
	return FileAccess.file_exists(path) and not DirAccess.dir_exists_absolute(path)
