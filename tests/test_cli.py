import json
import os
import subprocess
import sys

import pandas as pd

from psyml.cli import main


def test_cli_creates_reproducible_output(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output"
    pd.DataFrame({"feature": list(range(20)), "target": [0, 1] * 10}).to_csv(
        input_path, index=False
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "psyml",
            "--input",
            str(input_path),
            "--task",
            "classification",
            "--target",
            "target",
            "--model",
            "random_forest",
            "--output",
            str(output_path),
            "--param",
            "n_estimators=10",
        ],
    )

    main()

    assert "accuracy" in json.loads(capsys.readouterr().out)
    assert (output_path / "metrics.csv").is_file()


def test_preview_preserves_unicode_with_ascii_console(tmp_path):
    input_path = tmp_path / "unicode.csv"
    input_path.write_text("量表,类别\n1,甲\n2,乙\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii"
    result = subprocess.run(
        [sys.executable, "-m", "psyml", "preview", "--input", str(input_path),
         "--include-sample"],
        env=environment, capture_output=True, check=True,
    )
    payload = json.loads(result.stdout.decode("ascii"))
    decoded = json.dumps(payload, ensure_ascii=False)
    assert "量表" in decoded and "类别" in decoded
    assert "甲" in decoded and "乙" in decoded
