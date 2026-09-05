import pandas as pd
import pyreadstat
import pytest
import xlwt

from psyml.data import load_dataframe


@pytest.fixture
def research_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature_a": [1.25, 2.5, 3.75],
            "feature_b": [10.0, 20.0, 30.0],
            "target": [0.0, 1.0, 0.0],
        }
    )


def test_loads_tsv_from_unicode_path(tmp_path, research_frame):
    directory = tmp_path / "中文 路径"
    directory.mkdir()
    path = directory / "研究数据.tsv"
    research_frame.to_csv(path, sep="\t", index=False)

    loaded = load_dataframe(path)

    pd.testing.assert_frame_equal(loaded, research_frame)


@pytest.mark.parametrize("suffix", ["sav", "dta", "xpt"])
def test_loads_statistical_package_formats(tmp_path, research_frame, suffix):
    path = tmp_path / f"research.{suffix}"
    writer = {
        "sav": pyreadstat.write_sav,
        "dta": pyreadstat.write_dta,
        "xpt": pyreadstat.write_xport,
    }[suffix]
    writer(research_frame, path)

    loaded = load_dataframe(path)

    assert loaded.shape == research_frame.shape
    assert loaded.columns.tolist() == research_frame.columns.tolist()


def test_loads_parquet(tmp_path, research_frame):
    path = tmp_path / "research.parquet"
    research_frame.to_parquet(path, index=False)

    loaded = load_dataframe(path)

    pd.testing.assert_frame_equal(loaded, research_frame)


def test_loads_xlsx(tmp_path, research_frame):
    path = tmp_path / "research.xlsx"
    research_frame.to_excel(path, index=False)

    loaded = load_dataframe(path)

    pd.testing.assert_frame_equal(loaded, research_frame, check_dtype=False)


def test_loads_legacy_xls(tmp_path, research_frame):
    path = tmp_path / "research.xls"
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("data")
    for column_index, column_name in enumerate(research_frame.columns):
        sheet.write(0, column_index, column_name)
    for row_index, row in enumerate(research_frame.itertuples(index=False), start=1):
        for column_index, value in enumerate(row):
            sheet.write(row_index, column_index, float(value))
    workbook.save(str(path))

    loaded = load_dataframe(path)

    pd.testing.assert_frame_equal(loaded, research_frame, check_dtype=False)


def test_dispatches_sas7bdat_reader(tmp_path, research_frame, monkeypatch):
    path = tmp_path / "research.sas7bdat"
    path.touch()
    calls = []

    def fake_read_sas(received_path):
        calls.append(received_path)
        return research_frame, object()

    monkeypatch.setattr(pyreadstat, "read_sas7bdat", fake_read_sas)

    loaded = load_dataframe(path)

    pd.testing.assert_frame_equal(loaded, research_frame)
    assert calls == [path]


def test_malformed_supported_file_reports_format_and_name(tmp_path):
    path = tmp_path / "broken research.sav"
    path.write_text("not a SAV file", encoding="utf-8")

    with pytest.raises(ValueError, match=r"Failed to read '\.sav'.*broken research\.sav"):
        load_dataframe(path)
