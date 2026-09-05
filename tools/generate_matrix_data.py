"""Generate tiny, reproducible synthetic tables for format and parameter checks."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import xlwt

FORMATS = ("csv", "tsv", "xlsx", "xls", "sav", "dta", "xpt", "parquet")
FEATURES = ["signal", "noise", "category"]


def make_frame(task="classification", classes=2):
    rng = np.random.default_rng(20260905)
    labels = np.tile(np.arange(classes), 48 // classes)
    signal = rng.normal(size=48) + labels * 0.6
    frame = pd.DataFrame({
        "signal": signal.round(5),
        "noise": rng.normal(size=48).round(5),
        "category": np.tile(["site_a", "site_b", "site_c", "site_a"], 12),
        "participant": np.repeat([f"g{i:02}" for i in range(8)], 6),
        "target": labels.astype(float) if task == "classification" else (
            2 * signal + rng.normal(scale=0.2, size=48)
        ).round(5),
        "admin_note": np.full(48, np.nan),
    })
    frame.loc[[1, 17], "signal"] = np.nan
    frame.loc[[6, 30], "category"] = np.nan
    return frame


def write_frame(frame, path):
    suffix = path.suffix.lower()[1:]
    if suffix in {"csv", "tsv"}:
        frame.to_csv(path, sep="\t" if suffix == "tsv" else ",", index=False)
    elif suffix == "xlsx":
        frame.to_excel(path, index=False)
    elif suffix == "xls":
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet("data")
        for col, name in enumerate(frame.columns):
            sheet.write(0, col, name)
        for row, values in enumerate(frame.itertuples(index=False, name=None), start=1):
            for col, value in enumerate(values):
                if not pd.isna(value):
                    sheet.write(row, col, value)
        workbook.save(str(path))
    elif suffix == "parquet":
        frame.to_parquet(path, index=False)
    else:
        # Statistical file writers represent missing strings as empty strings.
        statistical = frame.copy()
        for column in statistical.select_dtypes(exclude="number"):
            statistical[column] = statistical[column].fillna("")
        {"sav": pyreadstat.write_sav, "dta": pyreadstat.write_dta,
         "xpt": pyreadstat.write_xport}[suffix](statistical, path)


def generate(root):
    root.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, task, classes in [("binary", "classification", 2),
                                ("multiclass", "classification", 3),
                                ("regression", "regression", 2)]:
        frame = make_frame(task, classes)
        for suffix in FORMATS:
            path = root / f"{name}.{suffix}"
            write_frame(frame, path)
            config = {
                "schema_version": "1.0",
                "task": task, "input_path": path.name, "target_column": "target",
                "feature_columns": FEATURES, "group_column": "participant",
                "model_name": "decision_tree", "model_params": {"max_depth": 3},
                "validation_strategy": "group_k_fold", "n_splits": 2,
                "inner_splits": 2, "figure_types": [],
                "output_dir": f"results/{name}_{suffix}",
            }
            config_path = root / f"{name}_{suffix}_config.json"
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            manifest.append({"file": path.name, "config": config_path.name,
                             "task": task, "rows": len(frame), "bytes": path.stat().st_size})
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=(
        Path(__file__).resolve().parents[1] / "examples/synthetic/matrix"
    ))
    args = parser.parse_args()
    items = generate(args.output_dir)
    print(f"Generated {len(items)} synthetic tables (48 rows each) in {args.output_dir}")
