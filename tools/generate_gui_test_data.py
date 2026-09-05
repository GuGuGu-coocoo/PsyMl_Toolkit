"""Small, deterministic, entirely synthetic datasets for GUI acceptance checks."""

from pathlib import Path

import numpy as np
import pandas as pd


def main():
    root = Path(__file__).resolve().parents[1] / "examples" / "synthetic"
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260905)
    score = rng.normal(size=48)
    base = pd.DataFrame(
        {
            "score": score.round(4),
            "category": np.tile(["A", "B", "A", "B"], 12),
            "participant": np.repeat([f"g{i:02}" for i in range(12)], 4),
            "target": np.tile([0, 1, 0, 1], 12),
            "admin_note": [None] * 48,
        }
    )
    # Administrative missingness is intentional and must not exclude selected-feature rows.
    base.to_csv(root / "classification.csv", index=False)
    base.assign(target=(2.5 * score + rng.normal(scale=0.5, size=48)).round(4)).to_csv(
        root / "regression.csv", index=False
    )
    base.iloc[:8].to_csv(root / "two_groups.csv", index=False)


if __name__ == "__main__":
    main()
