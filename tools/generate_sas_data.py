"""Regenerate the three synthetic SAS7BDAT fixtures; not a product export API.

Uses ReadStat's C writer embedded in the locked pyreadstat build. Some wheels
hide these symbols; --readstat-library can point to a standalone ReadStat library.
Normal tests use the checked-in files and do not need this private binding.
ReadStat warns that SAS itself may reject its output; verify with two readers.
"""

import argparse
import ctypes as ct
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyreadstat
from generate_matrix_data import FEATURES, make_frame


def write_sas7bdat(frame, path, library=None):
    if library is None:
        from pyreadstat import _readstat_writer
        library = _readstat_writer.__file__
    lib = ct.CDLL(str(library))
    ptr = ct.c_void_p
    callback_type = ct.CFUNCTYPE(ct.c_ssize_t, ptr, ct.c_size_t, ptr)
    signatures = {
        "writer_init": (ptr, []),
        "writer_free": (None, [ptr]),
        "set_data_writer": (ct.c_int, [ptr, callback_type]),
        "writer_set_file_timestamp": (ct.c_int, [ptr, ct.c_long]),
        "writer_set_file_label": (ct.c_int, [ptr, ct.c_char_p]),
        "add_variable": (ptr, [ptr, ct.c_char_p, ct.c_int, ct.c_size_t]),
        "begin_writing_sas7bdat": (ct.c_int, [ptr, ptr, ct.c_long]),
        "begin_row": (ct.c_int, [ptr]),
        "end_row": (ct.c_int, [ptr]),
        "end_writing": (ct.c_int, [ptr]),
        "insert_missing_value": (ct.c_int, [ptr, ptr]),
        "insert_double_value": (ct.c_int, [ptr, ptr, ct.c_double]),
        "insert_string_value": (ct.c_int, [ptr, ptr, ct.c_char_p]),
        "error_message": (ct.c_char_p, [ct.c_int]),
    }
    api = {}
    for name, (result, args) in signatures.items():
        try:
            function = getattr(lib, f"readstat_{name}")
        except AttributeError as error:
            raise RuntimeError("ReadStat symbols unavailable; use --readstat-library") from error
        function.restype, function.argtypes = result, args
        api[name] = function

    def check(code):
        if code:
            raise RuntimeError(api["error_message"](code).decode("utf-8"))

    # Keep the callback alive throughout writing and avoid exceptions crossing C.
    chunks = []

    @callback_type
    def collect(data, size, ctx):
        chunks.append(ct.string_at(data, size))
        return size

    writer = api["writer_init"]()
    if not writer:
        raise MemoryError("Cannot allocate ReadStat writer")
    try:
        check(api["set_data_writer"](writer, collect))
        check(api["writer_set_file_timestamp"](writer, 1788566400))
        check(api["writer_set_file_label"](writer, b"PsyML synthetic fixture; ReadStat writer"))
        variables = []
        for name in frame.columns:
            numeric = pd.api.types.is_numeric_dtype(frame[name])
            width = 0 if numeric else max(1, *(len(str(v).encode()) for v in frame[name].dropna()))
            variable = api["add_variable"](writer, name.encode(), 5 if numeric else 0, width)
            if not variable:
                raise MemoryError(f"Cannot allocate variable {name}")
            variables.append((variable, numeric))
        check(api["begin_writing_sas7bdat"](writer, None, len(frame)))
        for row in frame.itertuples(index=False, name=None):
            check(api["begin_row"](writer))
            for (variable, numeric), value in zip(variables, row, strict=True):
                if pd.isna(value):
                    check(api["insert_missing_value"](writer, variable))
                elif numeric:
                    check(api["insert_double_value"](writer, variable, float(value)))
                else:
                    check(api["insert_string_value"](writer, variable, str(value).encode()))
            check(api["end_row"](writer))
        check(api["end_writing"](writer))
    finally:
        api["writer_free"](writer)
    path.write_bytes(b"".join(chunks))


def generate(root, library=None):
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for name, task, classes in [("binary", "classification", 2),
                                ("multiclass", "classification", 3),
                                ("regression", "regression", 2)]:
        frame = make_frame(task, classes)
        path = root / f"{name}.sas7bdat"
        write_sas7bdat(frame, path, library)
        for loaded in [pyreadstat.read_sas7bdat(path)[0], pd.read_sas(path, encoding="utf-8")]:
            pd.testing.assert_frame_equal(loaded.replace("", float("nan")), frame,
                                          check_dtype=False, atol=1e-12, rtol=1e-12)
        cfg = {
            "schema_version": "1.0", "task": task, "input_path": path.name,
            "target_column": "target", "feature_columns": FEATURES,
            "group_column": "participant", "model_name": "decision_tree",
            "model_params": {"max_depth": 3}, "validation_strategy": "group_k_fold",
            "n_splits": 2, "inner_splits": 2, "figure_types": [],
            "output_dir": f"results/{name}_sas7bdat",
        }
        config_path = root / f"{name}_sas7bdat_config.json"
        config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        records.append({"file": path.name, "config": config_path.name, "task": task,
                        "rows": len(frame), "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {
        "writer": "ReadStat C API embedded in pyreadstat", "pyreadstat": pyreadstat.__version__,
        "source": "tools/generate_matrix_data.py:make_frame; seed 20260905",
        "verification": ["pyreadstat.read_sas7bdat", "pandas.read_sas"],
        "sas_application_verified": False,
        "upstream_limitation": "https://github.com/WizardMac/ReadStat#readstat-read-and-write-data-sets-from-sas-stata-and-spss",
        "files": records,
    }
    (root / "sas7bdat_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                encoding="utf-8")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=(
        Path(__file__).resolve().parents[1] / "examples/synthetic/matrix"
    ))
    parser.add_argument("--readstat-library", type=Path)
    args = parser.parse_args()
    records = generate(args.output_dir, args.readstat_library)
    print(f"Generated and independently verified {len(records)} SAS7BDAT files")
