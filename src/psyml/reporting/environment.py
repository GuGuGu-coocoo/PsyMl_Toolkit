"""Best-effort, explicit runtime and source/build identities for reproducibility."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from threadpoolctl import threadpool_info

THREAD_VARIABLES = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS",
    "OMP_DYNAMIC", "MKL_DYNAMIC",
)


def _digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "unknown"


def source_identity() -> dict:
    """Never guess a commit from an unrelated working-directory repository."""
    identity = {
        "kind": "unknown", "commit": "unknown", "working_tree_modified": "unknown",
        "lock_sha256": "unknown", "build_manifest_sha256": "unknown",
    }
    root = Path(__file__).resolve().parents[3]
    if (root / "pyproject.toml").is_file() and (root / "src/psyml/runner.py").is_file():
        identity["kind"] = "source_checkout"
        if (root / "uv.lock").is_file():
            identity["lock_sha256"] = _digest(root / "uv.lock")
        try:
            repository_root = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], cwd=root, text=True,
                stderr=subprocess.DEVNULL, timeout=5,
            ).strip()
            if Path(repository_root).resolve() != root:
                return identity
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True,
                stderr=subprocess.DEVNULL, timeout=5,
            ).strip()
            dirty = subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=normal"],
                cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=5,
            ).strip()
            identity.update(commit=commit, working_tree_modified=bool(dirty))
        except (OSError, subprocess.SubprocessError):
            pass
    if getattr(sys, "frozen", False):
        identity["kind"] = "frozen_build"
        # Native bundles keep BUILD.json above core and macOS Resources.
        for parent in list(Path(sys.executable).resolve().parents)[:6]:
            path = parent / "BUILD.json"
            if path.is_file():
                try:
                    build = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(build, dict):
                    continue
                identity.update(
                    commit=build.get("commit", "unknown"),
                    working_tree_modified=build.get("working_tree_modified", "unknown"),
                    lock_sha256=build.get("lock_sha256", "unknown"),
                    build_manifest_sha256=_digest(path),
                    build_label=build.get("label", "unknown"),
                    build_platform=build.get("platform", "unknown"),
                )
                break
    return identity


def numerical_environment() -> dict:
    """Capture loaded BLAS/OpenMP runtimes and effective pool thread counts."""
    try:
        pools = threadpool_info()
        # Keep backend identity without disclosing installation/user paths.
        for pool in pools:
            if "filepath" in pool:
                pool["library_filename"] = Path(pool.pop("filepath")).name
        status = "available" if pools else "unknown"
    except Exception as error:  # noqa: BLE001 - optional metadata must not lose a run
        pools = []
        status = f"unavailable: {type(error).__name__}"
    return {
        "status": status,
        "threadpools": pools,
        "thread_environment": {key: os.environ.get(key, "unset") for key in THREAD_VARIABLES},
    }
