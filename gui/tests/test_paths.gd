extends RefCounted
## Project-local temporary root for GUI test runs.
##
## Godot's OS.get_temp_dir() ignores TMPDIR on macOS and returns the per-user
## system temp folder, which would scatter test artefacts outside the repository
## and make them unreadable in restricted environments. Prefer PSYML_TEST_TMP
## when set, otherwise use <project>/tmp/gui-tests, and always create it.

static func temp_dir() -> String:
	var configured := OS.get_environment("PSYML_TEST_TMP")
	var path := configured
	if path.is_empty():
		path = ProjectSettings.globalize_path("res://../tmp/gui-tests")
	# globalize_path keeps the ".." segment of "res://../tmp/..."; canonicalize so
	# paths built here compare equal to simplify_path() results (CI sets no
	# PSYML_TEST_TMP, so an unresolved path made such assertions fail only on CI).
	path = path.simplify_path()
	DirAccess.make_dir_recursive_absolute(path)
	return path


static func run_deadline_msec() -> int:
	# One finite, CI-configurable wait for a real analysis run. The default
	# stays at 30s; only a slow machine may raise it, never the assertions.
	var configured := OS.get_environment("PSYML_TEST_RUN_TIMEOUT_SECONDS")
	var seconds := configured.to_float()
	if seconds <= 0.0:
		seconds = 30.0
	return Time.get_ticks_msec() + int(seconds * 1000.0)


static func log_directory() -> String:
	# The GUI runner exports this so per-group logs and failure diagnostics
	# land in the same directory before CI uploads them on failure.
	var configured := OS.get_environment("PSYML_GUI_LOG_DIR")
	if not configured.is_empty():
		DirAccess.make_dir_recursive_absolute(configured)
		return configured
	return temp_dir()
