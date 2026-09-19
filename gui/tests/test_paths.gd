extends RefCounted
## Project-local temporary root for GUI test runs.
##
## Godot's OS.get_temp_dir() ignores TMPDIR on macOS and returns the per-user
## system temp folder, which would scatter test artefacts outside the repository
## and make them unreadable in restricted environments. Prefer PSYML_TEST_TMP
## when set, otherwise use <project>/tmp/phase-A-worker/gui, and always create it.

static func temp_dir() -> String:
	var configured := OS.get_environment("PSYML_TEST_TMP")
	var path := configured
	if path.is_empty():
		path = ProjectSettings.globalize_path("res://../tmp/phase-A-worker/gui")
	DirAccess.make_dir_recursive_absolute(path)
	return path
