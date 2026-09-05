"""Entry point for the bundled scientific runtime."""

import multiprocessing
import os

if __name__ == "__main__":
    multiprocessing.freeze_support()
    os.environ.setdefault("MPLBACKEND", "Agg")
    from psyml.cli import entrypoint

    entrypoint()
