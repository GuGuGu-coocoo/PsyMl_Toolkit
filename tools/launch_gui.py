"""Launch the Godot client with the active PsyML Python environment."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    configured = os.environ.get("PSYML_GODOT")
    godot = configured or shutil.which("godot") or shutil.which("Godot")
    if godot is None:
        raise SystemExit(
            "Godot 4.7.2 was not found. Install Godot or set PSYML_GODOT to its executable."
        )
    environment = os.environ.copy()
    environment["PSYML_PYTHON"] = sys.executable
    completed = subprocess.run(
        [godot, "--path", str(root / "gui")],
        check=False,
        env=environment,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
