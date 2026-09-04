import json
import sys

import pandas as pd

from psyml.cli import main


def test_cli_creates_reproducible_output(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output"
    pd.DataFrame(
        {"feature": list(range(20)), "target": [0, 1] * 10}
    ).to_csv(input_path, index=False)
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
