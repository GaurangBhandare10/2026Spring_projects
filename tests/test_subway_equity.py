"""Pytest unit tests for the NYC subway equity analysis package.

Run with:
    pytest tests/test_subway_equity.py --cov=subway_equity --cov-report=term-missing
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

import subway_equity.io as io_mod
import subway_equity.metrics as metrics_mod
from subway_equity.io import (
    _available_raw_files,
    _missing_raw_file_error,
    filter_to_datetime_window,
    first_existing,
    normalize_columns,
    read_raw_csv,
    read_raw_geodata,
    read_table,
    resolve_raw_path,
)
from subway_equity.metrics import (
    assign_income_quartiles,
    bootstrap_correlation_interval,
    bootstrap_mean_difference,
    bootstrap_median_difference,
    bootstrap_partial_correlation_interval,
    compute_ridership_ratio,
    partial_correlation,
    weighted_average,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_raw(tmp_path: Path):
    """Return a temporary directory acting as RAW_DIR."""
    return tmp_path


@pytest.fixture()
def simple_df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})


@pytest.fixture()
def station_df() -> pd.DataFrame:
    """Minimal station table used across hypothesis tests."""
    return pd.DataFrame({
        "station": ["A", "A", "B", "B", "C"],
        "year":    [2020, 2021, 2020, 2021, 2020],
        "riders":  [100.0, 120.0, 200.0, 180.0, 50.0],
    })


# ─────────────────────────────────────────────────────────────────────────────
# io.normalize_columns
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeColumns:
    def test_spaces_and_hyphens(self):
        df = pd.DataFrame(columns=["Stop Name", "Route-ID"])
        assert normalize_columns(df).columns.tolist() == ["stop_name", "route_id"]

    def test_already_lowercase(self):
        df = pd.DataFrame(columns=["already_lower"])
        assert normalize_columns(df).columns.tolist() == ["already_lower"]

    def test_leading_trailing_spaces(self):
        df = pd.DataFrame(columns=["  Padded  "])
        assert normalize_columns(df).columns.tolist() == ["padded"]

    def test_empty_dataframe(self):
        assert normalize_columns(pd.DataFrame()).columns.tolist() == []

    def test_mixed_case_and_special(self):
        df = pd.DataFrame(columns=["My-Column Name", "ABC"])
        result = normalize_columns(df).columns.tolist()
        assert result == ["my_column_name", "abc"]

    def test_data_values_unchanged(self):
        df = pd.DataFrame({"Col A": [1, 2, 3]})
        result = normalize_columns(df)
        assert result["col_a"].tolist() == [1, 2, 3]


# ─────────────────────────────────────────────────────────────────────────────
# io.first_existing
# ─────────────────────────────────────────────────────────────────────────────

class TestFirstExisting:
    def test_returns_first_match(self):
        df = pd.DataFrame(columns=["b", "c"])
        assert first_existing(df, ["a", "b", "c"]) == "b"

    def test_respects_order_of_options(self):
        df = pd.DataFrame(columns=["b", "c"])
        assert first_existing(df, ["c", "b"]) == "c"

    def test_exact_single_match(self):
        df = pd.DataFrame(columns=["x"])
        assert first_existing(df, ["x"]) == "x"

    def test_raises_key_error_when_none_found(self):
        df = pd.DataFrame(columns=["a", "b"])
        with pytest.raises(KeyError):
            first_existing(df, ["z", "y"])

    def test_raises_key_error_on_empty_options(self):
        df = pd.DataFrame(columns=["a"])
        with pytest.raises(KeyError):
            first_existing(df, [])


# ─────────────────────────────────────────────────────────────────────────────
# io.filter_to_datetime_window
# ─────────────────────────────────────────────────────────────────────────────

class TestFilterToDatetimeWindow:
    def test_filters_to_subset(self):
        df = pd.DataFrame({
            "date": ["2022-01-01", "2023-06-15", "2024-12-31"],
            "val": [1, 2, 3],
        })
        result = filter_to_datetime_window(df, "date", "2023-01-01", "2024-01-01")
        assert result["val"].tolist() == [2]

    def test_returns_all_rows_when_window_covers_all(self):
        df = pd.DataFrame({"date": ["2022-01-01", "2023-06-15", "2024-12-31"], "val": [1, 2, 3]})
        result = filter_to_datetime_window(df, "date", "2022-01-01", "2024-12-31")
        assert len(result) == 3

    def test_returns_empty_when_window_misses_all(self):
        df = pd.DataFrame({"date": ["2022-01-01"], "val": [1]})
        result = filter_to_datetime_window(df, "date", "2025-01-01", "2025-12-31")
        assert len(result) == 0

    def test_inclusive_on_both_endpoints(self):
        df = pd.DataFrame({"date": ["2023-03-01", "2023-03-31"], "val": [10, 20]})
        result = filter_to_datetime_window(df, "date", "2023-03-01", "2023-03-31")
        assert len(result) == 2

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"date": ["2022-01-01"], "val": [1]})
        original_dtype = df["date"].dtype
        filter_to_datetime_window(df, "date", "2022-01-01", "2023-01-01")
        assert df["date"].dtype == original_dtype

    def test_handles_already_datetime_column(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-06-01"]),
            "val": [1, 2],
        })
        result = filter_to_datetime_window(df, "date", "2023-01-01", "2023-04-01")
        assert result["val"].tolist() == [1]


# ─────────────────────────────────────────────────────────────────────────────
# io.read_table
# ─────────────────────────────────────────────────────────────────────────────

class TestReadTable:
    def test_reads_csv(self, simple_df, tmp_path):
        p = tmp_path / "data.csv"
        simple_df.to_csv(p, index=False)
        result = read_table(p)
        assert result.shape == simple_df.shape

    def test_reads_txt_as_csv(self, simple_df, tmp_path):
        p = tmp_path / "data.txt"
        simple_df.to_csv(p, index=False)
        result = read_table(p)
        assert result.shape == simple_df.shape

    def test_reads_parquet(self, simple_df, tmp_path):
        p = tmp_path / "data.parquet"
        simple_df.to_parquet(p, index=False)
        result = read_table(p)
        assert result.shape == simple_df.shape

    def test_raises_value_error_for_unsupported_extension(self, tmp_path):
        p = tmp_path / "data.xlsx"
        p.touch()
        with pytest.raises(ValueError, match="Unsupported"):
            read_table(p)

    def test_raises_value_error_for_json(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        with pytest.raises(ValueError):
            read_table(p)

    def test_csv_values_preserved(self, tmp_path):
        df = pd.DataFrame({"x": [10, 20]})
        p = tmp_path / "data.csv"
        df.to_csv(p, index=False)
        assert read_table(p)["x"].tolist() == [10, 20]


# ─────────────────────────────────────────────────────────────────────────────
# io._available_raw_files
# ─────────────────────────────────────────────────────────────────────────────

class TestAvailableRawFiles:
    def test_lists_files_excluding_gitkeep(self, tmp_raw):
        (tmp_raw / "stops.txt").write_text("data")
        (tmp_raw / ".gitkeep").write_text("")
        with patch.object(io_mod, "RAW_DIR", tmp_raw):
            result = _available_raw_files()
        assert result == ["stops.txt"]
        assert ".gitkeep" not in result

    def test_returns_empty_list_for_empty_dir(self, tmp_raw):
        with patch.object(io_mod, "RAW_DIR", tmp_raw):
            assert _available_raw_files() == []

    def test_returns_sorted_names(self, tmp_raw):
        for name in ["b.csv", "a.csv", "c.txt"]:
            (tmp_raw / name).write_text("x")
        with patch.object(io_mod, "RAW_DIR", tmp_raw):
            result = _available_raw_files()
        assert result == sorted(result)

    def test_includes_files_in_subdirectory(self, tmp_raw):
        sub = tmp_raw / "gtfs"
        sub.mkdir()
        (sub / "stops.txt").write_text("data")
        with patch.object(io_mod, "RAW_DIR", tmp_raw):
            result = _available_raw_files()
        assert any("stops.txt" in r for r in result)

    def test_gitkeep_always_excluded(self, tmp_raw):
        (tmp_raw / ".gitkeep").write_text("")
        with patch.object(io_mod, "RAW_DIR", tmp_raw):
            assert _available_raw_files() == []


# ─────────────────────────────────────────────────────────────────────────────
# io._missing_raw_file_error
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingRawFileError:
    def test_returns_file_not_found_error(self, tmp_raw):
        fake = {"stops": Path("data/raw/stops.txt")}
        with patch.object(io_mod, "RAW_FILES", fake), patch.object(io_mod, "RAW_DIR", tmp_raw):
            err = _missing_raw_file_error("stops", "stops.txt")
        assert isinstance(err, FileNotFoundError)

    def test_message_contains_key_and_filename(self, tmp_raw):
        fake = {"stops": Path("data/raw/stops.txt")}
        with patch.object(io_mod, "RAW_FILES", fake), patch.object(io_mod, "RAW_DIR", tmp_raw):
            err = _missing_raw_file_error("stops", "stops.txt")
        msg = str(err)
        assert "stops" in msg
        assert "stops.txt" in msg

    def test_message_mentions_zip_option(self, tmp_raw):
        fake = {"ridership": Path("data/raw/ridership.csv")}
        with patch.object(io_mod, "RAW_FILES", fake), patch.object(io_mod, "RAW_DIR", tmp_raw):
            err = _missing_raw_file_error("ridership", "ridership.csv")
        assert ".zip" in str(err)

    def test_message_lists_available_files(self, tmp_raw):
        (tmp_raw / "found.csv").write_text("x")
        fake = {"missing": Path("data/raw/missing.csv")}
        with patch.object(io_mod, "RAW_FILES", fake), patch.object(io_mod, "RAW_DIR", tmp_raw):
            err = _missing_raw_file_error("missing", "missing.csv")
        assert "found.csv" in str(err)


# ─────────────────────────────────────────────────────────────────────────────
# io.resolve_raw_path
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveRawPath:
    def test_returns_path_when_file_exists_directly(self, tmp_raw):
        f = tmp_raw / "stops.txt"
        f.write_text("data")
        with patch.object(io_mod, "RAW_DIR", tmp_raw), patch.object(io_mod, "RAW_FILES", {"stops": f}):
            assert resolve_raw_path("stops") == f

    def test_finds_file_in_subdirectory(self, tmp_raw):
        sub = tmp_raw / "gtfs"
        sub.mkdir()
        f = sub / "stops.txt"
        f.write_text("data")
        with patch.object(io_mod, "RAW_DIR", tmp_raw), \
             patch.object(io_mod, "RAW_FILES", {"stops": tmp_raw / "stops.txt"}):
            assert resolve_raw_path("stops") == f

    def test_raises_file_not_found_when_missing(self, tmp_raw):
        with patch.object(io_mod, "RAW_DIR", tmp_raw), \
             patch.object(io_mod, "RAW_FILES", {"stops": tmp_raw / "stops.txt"}):
            with pytest.raises(FileNotFoundError):
                resolve_raw_path("stops")


# ─────────────────────────────────────────────────────────────────────────────
# io.read_raw_csv
# ─────────────────────────────────────────────────────────────────────────────

class TestReadRawCsv:
    CSV = "col1,col2\n1,2\n3,4\n"

    def test_reads_direct_csv(self, tmp_raw):
        f = tmp_raw / "data.csv"
        f.write_text(self.CSV)
        with patch.object(io_mod, "RAW_DIR", tmp_raw), patch.object(io_mod, "RAW_FILES", {"data": f}):
            df = read_raw_csv("data")
        assert df.shape == (2, 2)

    def test_reads_csv_from_subfolder(self, tmp_raw):
        sub = tmp_raw / "sub"
        sub.mkdir()
        f = sub / "data.csv"
        f.write_text(self.CSV)
        with patch.object(io_mod, "RAW_DIR", tmp_raw), \
             patch.object(io_mod, "RAW_FILES", {"data": tmp_raw / "data.csv"}):
            df = read_raw_csv("data")
        assert df.shape == (2, 2)

    def test_reads_csv_from_zip_archive(self, tmp_raw):
        zp = tmp_raw / "archive.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("data.csv", self.CSV)
        with patch.object(io_mod, "RAW_DIR", tmp_raw), \
             patch.object(io_mod, "RAW_FILES", {"data": tmp_raw / "data.csv"}):
            df = read_raw_csv("data")
        assert df.shape == (2, 2)

    def test_raises_when_not_found(self, tmp_raw):
        with patch.object(io_mod, "RAW_DIR", tmp_raw), \
             patch.object(io_mod, "RAW_FILES", {"data": tmp_raw / "data.csv"}):
            with pytest.raises(FileNotFoundError):
                read_raw_csv("data")

    def test_passes_kwargs_to_read_csv(self, tmp_raw):
        f = tmp_raw / "data.csv"
        f.write_text(self.CSV)
        with patch.object(io_mod, "RAW_DIR", tmp_raw), patch.object(io_mod, "RAW_FILES", {"data": f}):
            df = read_raw_csv("data", nrows=1)
        assert len(df) == 1


# ─────────────────────────────────────────────────────────────────────────────
# io.read_raw_geodata
# ─────────────────────────────────────────────────────────────────────────────

class TestReadRawGeodata:
    def test_returns_geodataframe(self):
        import geopandas as gpd
        mock_gdf = gpd.GeoDataFrame({"geometry": []})
        with patch.object(io_mod, "resolve_raw_path", return_value=Path("shapes.geojson")), \
             patch("geopandas.read_file", return_value=mock_gdf):
            result = read_raw_geodata("shapes")
        assert isinstance(result, gpd.GeoDataFrame)

    def test_delegates_to_resolve_raw_path(self):
        import geopandas as gpd
        mock_gdf = gpd.GeoDataFrame({"geometry": []})
        mock_resolve = MagicMock(return_value=Path("tracts.geojson"))
        with patch.object(io_mod, "resolve_raw_path", mock_resolve), \
             patch("geopandas.read_file", return_value=mock_gdf):
            read_raw_geodata("tracts")
        mock_resolve.assert_called_once_with("tracts")


# ─────────────────────────────────────────────────────────────────────────────
# metrics.assign_income_quartiles
# ─────────────────────────────────────────────────────────────────────────────

class TestAssignIncomeQuartiles:
    def test_returns_four_labels(self):
        df = pd.DataFrame({"income": [10_000, 50_000, 100_000, 200_000]})
        result = assign_income_quartiles(df, "income")
        assert set(result.cat.categories.tolist()) == {"Q1", "Q2", "Q3", "Q4"}

    def test_lowest_income_is_q1(self):
        df = pd.DataFrame({"income": list(range(1, 101))})
        result = assign_income_quartiles(df, "income")
        assert result.iloc[0] == "Q1"

    def test_highest_income_is_q4(self):
        df = pd.DataFrame({"income": list(range(1, 101))})
        result = assign_income_quartiles(df, "income")
        assert result.iloc[-1] == "Q4"

    def test_returns_series_same_length(self):
        df = pd.DataFrame({"income": [20_000, 40_000, 80_000, 160_000, 200_000, 300_000, 400_000, 500_000]})
        result = assign_income_quartiles(df, "income")
        assert len(result) == len(df)


# ─────────────────────────────────────────────────────────────────────────────
# metrics.compute_ridership_ratio
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeRidershipRatio:
    def test_baseline_year_is_one(self, station_df):
        result = compute_ridership_ratio(station_df, "station", "year", "riders", 2020)
        baseline_rows = station_df[station_df["year"] == 2020].index
        assert result.loc[baseline_rows].tolist() == pytest.approx([1.0, 1.0, 1.0])

    def test_ratio_above_baseline(self, station_df):
        result = compute_ridership_ratio(station_df, "station", "year", "riders", 2020)
        # Station A: 120/100 = 1.2 in 2021
        a_2021 = station_df[(station_df["station"] == "A") & (station_df["year"] == 2021)].index[0]
        assert result.loc[a_2021] == pytest.approx(1.2)

    def test_ratio_below_baseline(self, station_df):
        result = compute_ridership_ratio(station_df, "station", "year", "riders", 2020)
        # Station B: 180/200 = 0.9 in 2021
        b_2021 = station_df[(station_df["station"] == "B") & (station_df["year"] == 2021)].index[0]
        assert result.loc[b_2021] == pytest.approx(0.9)

    def test_returns_series_same_length(self, station_df):
        result = compute_ridership_ratio(station_df, "station", "year", "riders", 2020)
        assert len(result) == len(station_df)

    def test_exact_values(self):
        df = pd.DataFrame({
            "station": ["A", "A", "A"],
            "year": [2020, 2021, 2022],
            "riders": [100.0, 120.0, 80.0],
        })
        result = compute_ridership_ratio(df, "station", "year", "riders", 2020)
        assert result.round(2).tolist() == [1.0, 1.2, 0.8]


# ─────────────────────────────────────────────────────────────────────────────
# metrics.partial_correlation
# ─────────────────────────────────────────────────────────────────────────────

class TestPartialCorrelation:
    def test_returns_tuple_of_two_floats(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
        control = pd.Series([1.0, 1.5, 2.0, 2.5, 3.0])
        stat, p = partial_correlation(x, y, control)
        assert isinstance(float(stat), float)
        assert isinstance(float(p), float)

    def test_perfect_correlation_after_control(self):
        rng = np.random.default_rng(0)
        control = pd.Series(rng.standard_normal(50))
        x = control * 2 + pd.Series(rng.standard_normal(50) * 0.001)
        y = control * 3 + pd.Series(rng.standard_normal(50) * 0.001)
        stat, p = partial_correlation(x, y, control)
        # After removing the shared control, correlation should be near zero
        assert abs(float(stat)) < 0.5

    def test_p_value_in_valid_range(self):
        x = pd.Series(range(20), dtype=float)
        y = pd.Series(range(20, 40), dtype=float)
        control = pd.Series([float(i % 5) for i in range(20)])
        _, p = partial_correlation(x, y, control)
        assert 0.0 <= float(p) <= 1.0

    def test_stat_in_correlation_range(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
        control = pd.Series([1.0, 1.0, 2.0, 2.0, 3.0])
        stat, _ = partial_correlation(x, y, control)
        assert -1.0 <= float(stat) <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# metrics.bootstrap_correlation_interval
# ─────────────────────────────────────────────────────────────────────────────

class TestBootstrapCorrelationInterval:
    def test_perfect_positive_correlation_ci_near_one(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
        low, high = bootstrap_correlation_interval(x, y, n_boot=200, seed=1)
        assert bool(low <= 1.0 <= high)

    def test_returns_two_finite_floats(self):
        x = pd.Series(range(10), dtype=float)
        y = pd.Series(range(10, 20), dtype=float)
        low, high = bootstrap_correlation_interval(x, y, n_boot=100, seed=42)
        assert np.isfinite(low) and np.isfinite(high)

    def test_low_less_than_high(self):
        x = pd.Series(range(20), dtype=float)
        y = pd.Series(range(20), dtype=float)
        low, high = bootstrap_correlation_interval(x, y, n_boot=200, seed=0)
        assert low <= high

    def test_spearman_method(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        y = pd.Series([1.0, 4.0, 9.0, 16.0, 25.0, 36.0, 49.0, 64.0, 81.0, 100.0])
        low, high = bootstrap_correlation_interval(x, y, method="spearman", n_boot=500, seed=3)
        assert bool(low <= 1.0 <= high) or (np.isfinite(low) and np.isfinite(high) and low <= high)

    def test_unsupported_method_raises(self):
        x = pd.Series([1.0, 2.0, 3.0])
        y = pd.Series([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="Unsupported"):
            bootstrap_correlation_interval(x, y, method="kendall", n_boot=10, seed=0)

    def test_nan_input_returns_nan(self):
        x = pd.Series([np.nan, np.nan])
        y = pd.Series([np.nan, np.nan])
        low, high = bootstrap_correlation_interval(x, y, n_boot=10, seed=0)
        assert np.isnan(low) and np.isnan(high)


# ─────────────────────────────────────────────────────────────────────────────
# metrics.bootstrap_partial_correlation_interval
# ─────────────────────────────────────────────────────────────────────────────

class TestBootstrapPartialCorrelationInterval:
    def test_returns_two_finite_values(self):
        rng = np.random.default_rng(7)
        x = pd.Series(rng.standard_normal(30))
        y = pd.Series(rng.standard_normal(30))
        ctrl = pd.Series(rng.standard_normal(30))
        low, high = bootstrap_partial_correlation_interval(x, y, ctrl, n_boot=100, seed=7)
        assert np.isfinite(low) and np.isfinite(high)

    def test_low_less_than_or_equal_high(self):
        rng = np.random.default_rng(8)
        x = pd.Series(rng.standard_normal(20))
        y = pd.Series(rng.standard_normal(20))
        ctrl = pd.Series(rng.standard_normal(20))
        low, high = bootstrap_partial_correlation_interval(x, y, ctrl, n_boot=100, seed=8)
        assert low <= high

    def test_empty_after_dropna_returns_nan(self):
        x = pd.Series([np.nan, np.nan])
        y = pd.Series([np.nan, np.nan])
        ctrl = pd.Series([np.nan, np.nan])
        low, high = bootstrap_partial_correlation_interval(x, y, ctrl, n_boot=10, seed=0)
        assert np.isnan(low) and np.isnan(high)


# ─────────────────────────────────────────────────────────────────────────────
# metrics.bootstrap_median_difference
# ─────────────────────────────────────────────────────────────────────────────

class TestBootstrapMedianDifference:
    def test_positive_difference_ci_above_zero(self):
        left = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
        right = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        low, high = bootstrap_median_difference(left, right, n_boot=500, seed=0)
        assert float(low) > 0

    def test_returns_two_finite_floats(self):
        left = pd.Series([1.0, 2.0, 3.0])
        right = pd.Series([1.0, 2.0, 3.0])
        low, high = bootstrap_median_difference(left, right, n_boot=100, seed=1)
        assert np.isfinite(low) and np.isfinite(high)

    def test_low_less_than_or_equal_high(self):
        left = pd.Series(range(20), dtype=float)
        right = pd.Series(range(10, 30), dtype=float)
        low, high = bootstrap_median_difference(left, right, n_boot=200, seed=2)
        assert low <= high


# ─────────────────────────────────────────────────────────────────────────────
# metrics.bootstrap_mean_difference
# ─────────────────────────────────────────────────────────────────────────────

class TestBootstrapMeanDifference:
    def test_clearly_positive_difference(self):
        left = pd.Series([4.0, 5.0, 6.0])
        right = pd.Series([1.0, 2.0, 3.0])
        low, high = bootstrap_mean_difference(left, right, n_boot=200, seed=1)
        assert bool(low > 0 and high > 0)

    def test_empty_left_returns_nan(self):
        low, high = bootstrap_mean_difference(pd.Series([], dtype=float), pd.Series([1.0, 2.0]), n_boot=50)
        assert np.isnan(low) and np.isnan(high)

    def test_empty_right_returns_nan(self):
        low, high = bootstrap_mean_difference(pd.Series([1.0, 2.0]), pd.Series([], dtype=float), n_boot=50)
        assert np.isnan(low) and np.isnan(high)

    def test_returns_two_finite_floats(self):
        left = pd.Series([10.0, 11.0, 12.0])
        right = pd.Series([1.0, 2.0, 3.0])
        low, high = bootstrap_mean_difference(left, right, n_boot=200, seed=5)
        assert np.isfinite(low) and np.isfinite(high)

    def test_low_less_than_high(self):
        left = pd.Series(range(20), dtype=float)
        right = pd.Series(range(10, 30), dtype=float)
        low, high = bootstrap_mean_difference(left, right, n_boot=200, seed=3)
        assert low <= high


# ─────────────────────────────────────────────────────────────────────────────
# metrics.weighted_average
# ─────────────────────────────────────────────────────────────────────────────

class TestWeightedAverage:
    def test_equal_weights_gives_mean(self):
        result = weighted_average(pd.Series([1.0, 3.0]), pd.Series([1.0, 1.0]))
        assert float(result) == pytest.approx(2.0)

    def test_unequal_weights(self):
        result = weighted_average(pd.Series([1.0, 3.0]), pd.Series([1.0, 3.0]))
        assert float(result) == pytest.approx(2.5)

    def test_ignores_nan_values(self):
        result = weighted_average(pd.Series([1.0, np.nan, 3.0]), pd.Series([1.0, 1.0, 1.0]))
        assert float(result) == pytest.approx(2.0)

    def test_ignores_nan_weights(self):
        result = weighted_average(pd.Series([1.0, 2.0, 3.0]), pd.Series([1.0, np.nan, 1.0]))
        assert float(result) == pytest.approx(2.0)

    def test_all_nan_returns_nan(self):
        result = weighted_average(pd.Series([np.nan]), pd.Series([np.nan]))
        assert np.isnan(result)

    def test_single_value(self):
        result = weighted_average(pd.Series([42.0]), pd.Series([1.0]))
        assert float(result) == pytest.approx(42.0)

    def test_zero_weight_effectively_ignored(self):
        result = weighted_average(pd.Series([100.0, 2.0]), pd.Series([0.0, 1.0]))
        assert float(result) == pytest.approx(2.0)


# ─────────────────────────────────────────────────────────────────────────────
# Script-level helper functions (from scripts/07_run_hypothesis_tests.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestMatchAnyValue:
    """Tests for the match_any_value helper in the hypothesis script."""

    @pytest.fixture(autouse=True)
    def _import(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from importlib import import_module
        # Import via importlib because the filename starts with a digit
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hyp_tests",
            Path(__file__).resolve().parents[1] / "scripts" / "07_run_hypothesis_tests.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.match_any_value = mod.match_any_value
        self.match_route_ids = mod.match_route_ids
        self.interpret_result = mod.interpret_result

    def test_exact_match(self):
        s = pd.Series(["S Rock", "A", "GS"])
        result = self.match_any_value(s, ["S Rock"])
        assert result.tolist() == [True, False, False]

    def test_case_insensitive(self):
        s = pd.Series(["s rock", "S ROCK", "A"])
        result = self.match_any_value(s, ["S Rock"])
        assert result.tolist() == [True, True, False]

    def test_strips_whitespace(self):
        s = pd.Series([" s 42nd "])
        result = self.match_any_value(s, ["s 42nd"])
        assert result.tolist() == [True]

    def test_no_match_returns_false(self):
        s = pd.Series(["X", "Y", "Z"])
        result = self.match_any_value(s, ["A", "B"])
        assert not result.any()

    def test_all_match(self):
        s = pd.Series(["a", "b"])
        result = self.match_any_value(s, ["a", "b"])
        assert result.all()


class TestMatchRouteIds:
    @pytest.fixture(autouse=True)
    def _import(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hyp_tests2",
            Path(__file__).resolve().parents[1] / "scripts" / "07_run_hypothesis_tests.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.match_route_ids = mod.match_route_ids

    def test_single_route_match(self):
        s = pd.Series(["A,H", "GS", "A,C"])
        assert self.match_route_ids(s, ["H", "GS"]).tolist() == [True, True, False]

    def test_case_insensitive_route(self):
        s = pd.Series(["a,h"])
        assert self.match_route_ids(s, ["H"]).tolist() == [True]

    def test_no_match(self):
        s = pd.Series(["A", "B", "C"])
        assert not self.match_route_ids(s, ["Z"]).any()

    def test_comma_separated_multi_route(self):
        s = pd.Series(["A,B,C,H"])
        assert self.match_route_ids(s, ["H"]).tolist() == [True]


class TestInterpretResult:
    @pytest.fixture(autouse=True)
    def _import(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hyp_tests3",
            Path(__file__).resolve().parents[1] / "scripts" / "07_run_hypothesis_tests.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.interpret_result = mod.interpret_result

    def test_nan_pvalue_is_descriptive(self):
        assert self.interpret_result("H1", 0.5, float("nan")) == "descriptive only"

    def test_high_pvalue_not_supported(self):
        assert self.interpret_result("H1", -0.5, 0.9) == "not clearly supported"

    def test_h1_negative_stat_supported(self):
        assert self.interpret_result("H1", -0.5, 0.01) == "supported"

    def test_h1_positive_stat_opposite_direction(self):
        assert self.interpret_result("H1", 0.5, 0.01) == "significant, opposite direction"

    def test_h3_always_supported_when_significant(self):
        assert self.interpret_result("H3", 999.0, 0.001) == "supported"

    def test_h4_delay_positive_stat_supported(self):
        assert self.interpret_result("H4_delay", 17.0, 1e-26) == "supported"

    def test_h4_delay_negative_stat_opposite(self):
        assert self.interpret_result("H4_delay", -5.0, 0.001) == "significant, opposite direction"

    def test_h4_ridership_negative_stat_supported(self):
        assert self.interpret_result("H4_ridership", -0.3, 0.01) == "supported"

    def test_unknown_hypothesis_returns_significant(self):
        assert self.interpret_result("H99", 1.0, 0.01) == "significant"


# ─────────────────────────────────────────────────────────────────────────────
# Script-level helpers from scripts/02_service_frequency.py
# ─────────────────────────────────────────────────────────────────────────────

class TestServiceFrequencyHelpers:
    @pytest.fixture(autouse=True)
    def _import(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "svc_freq",
            Path(__file__).resolve().parents[1] / "scripts" / "02_service_frequency.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.time_to_seconds = mod.time_to_seconds
        self.is_peak_departure = mod.is_peak_departure

    def test_time_to_seconds_standard(self):
        assert self.time_to_seconds("07:30:00") == 27000

    def test_time_to_seconds_midnight(self):
        assert self.time_to_seconds("00:00:00") == 0

    def test_time_to_seconds_noon(self):
        assert self.time_to_seconds("12:00:00") == 43200

    def test_time_to_seconds_gtfs_over_24h(self):
        # GTFS allows hours > 24 for trips past midnight
        assert self.time_to_seconds("25:00:00") == 90000

    def test_is_peak_am_window(self):
        assert self.is_peak_departure(self.time_to_seconds("08:15:00")) is True

    def test_is_peak_pm_window(self):
        assert self.is_peak_departure(self.time_to_seconds("17:30:00")) is True

    def test_not_peak_midday(self):
        assert self.is_peak_departure(self.time_to_seconds("12:00:00")) is False

    def test_not_peak_late_night(self):
        assert self.is_peak_departure(self.time_to_seconds("23:00:00")) is False

    def test_boundary_start_of_am_peak_inclusive(self):
        # 07:00 is the start of the AM window (7, 9)
        assert self.is_peak_departure(self.time_to_seconds("07:00:00")) is True

    def test_boundary_end_of_am_peak_exclusive(self):
        # 09:00:00 = 32400 seconds, end is exclusive
        assert self.is_peak_departure(self.time_to_seconds("09:00:00")) is False


# ─────────────────────────────────────────────────────────────────────────────
# remote.py — unit tests for pure helper functions
# ─────────────────────────────────────────────────────────────────────────────

import subway_equity.remote as remote_mod
from subway_equity.remote import (
    _cache_path,
    _extract_tract_geoid,
    _monthly_windows,
    _pickle_cache_path,
    _raise_for_status,
    build_session,
)


class TestBuildSession:
    def test_returns_requests_session(self):
        import requests
        session = build_session()
        assert isinstance(session, requests.Session)

    def test_user_agent_set(self):
        session = build_session()
        assert "nyc-subway-equity-analysis" in session.headers["User-Agent"]

    def test_app_token_added_when_env_set(self, monkeypatch):
        monkeypatch.setenv("SOCRATA_APP_TOKEN", "test_token_123")
        session = build_session()
        assert session.headers.get("X-App-Token") == "test_token_123"

    def test_no_app_token_when_env_absent(self, monkeypatch):
        monkeypatch.delenv("SOCRATA_APP_TOKEN", raising=False)
        session = build_session()
        assert "X-App-Token" not in session.headers


class TestCachePath:
    def test_returns_path_under_cache_dir(self, tmp_path):
        with patch.object(remote_mod, "CACHE_DIR", tmp_path):
            result = _cache_path("test.parquet")
        assert result == tmp_path / "test.parquet"

    def test_creates_cache_dir_if_missing(self, tmp_path):
        cache = tmp_path / "new_cache"
        with patch.object(remote_mod, "CACHE_DIR", cache):
            _cache_path("file.parquet")
        assert cache.exists()


class TestPickleCachePath:
    def test_parquet_extension_becomes_pkl(self, tmp_path):
        with patch.object(remote_mod, "CACHE_DIR", tmp_path):
            result = _pickle_cache_path("data.parquet")
        assert result.suffix == ".pkl"
        assert result.stem == "data"

    def test_non_parquet_gets_pkl_appended(self, tmp_path):
        with patch.object(remote_mod, "CACHE_DIR", tmp_path):
            result = _pickle_cache_path("data.csv")
        assert result.name == "data.csv.pkl"


class TestRaiseForStatus:
    def test_does_not_raise_on_200(self):
        import requests
        resp = MagicMock(spec=requests.Response)
        resp.raise_for_status = MagicMock()
        _raise_for_status(resp)  # should not raise

    def test_wraps_http_error_with_context(self):
        import requests
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 404
        resp.url = "https://example.com"
        resp.text = "Not Found"
        resp.raise_for_status.side_effect = requests.HTTPError("404")
        with pytest.raises(requests.HTTPError, match="404"):
            _raise_for_status(resp)


class TestMonthlyWindows:
    def test_returns_list_of_tuples(self):
        windows = _monthly_windows("2023-01-01T00:00:00", "2023-03-31T23:45:00")
        assert isinstance(windows, list)
        assert all(isinstance(w, tuple) and len(w) == 2 for w in windows)

    def test_three_months_gives_three_windows(self):
        windows = _monthly_windows("2023-01-01T00:00:00", "2023-03-31T23:45:00")
        assert len(windows) == 3

    def test_single_month_gives_one_window(self):
        windows = _monthly_windows("2023-06-01T00:00:00", "2023-06-30T23:45:00")
        assert len(windows) == 1

    def test_start_precedes_end_in_each_window(self):
        windows = _monthly_windows("2022-01-01T00:00:00", "2022-06-30T23:45:00")
        for start, end in windows:
            assert start <= end

    def test_full_year_gives_twelve_windows(self):
        windows = _monthly_windows("2020-01-01T00:00:00", "2020-12-31T23:45:00")
        assert len(windows) == 12

    def test_window_strings_are_iso_format(self):
        windows = _monthly_windows("2023-01-01T00:00:00", "2023-02-28T23:45:00")
        for start, end in windows:
            # Must be parseable as timestamps
            pd.Timestamp(start)
            pd.Timestamp(end)


class TestExtractTractGeoid:
    def test_returns_geoid_from_valid_payload(self):
        payload = {
            "result": {
                "geographies": {
                    "Census Tracts": [{"GEOID": "36061019100"}]
                }
            }
        }
        assert _extract_tract_geoid(payload) == "36061019100"

    def test_returns_none_when_no_geographies(self):
        payload = {"result": {"geographies": {}}}
        assert _extract_tract_geoid(payload) is None

    def test_returns_none_when_result_missing(self):
        assert _extract_tract_geoid({}) is None

    def test_returns_none_when_tract_list_empty(self):
        payload = {"result": {"geographies": {"Census Tracts": []}}}
        assert _extract_tract_geoid(payload) is None

    def test_case_insensitive_tract_key_match(self):
        payload = {
            "result": {
                "geographies": {
                    "2020 Census Tracts": [{"GEOID": "36081123400"}]
                }
            }
        }
        assert _extract_tract_geoid(payload) == "36081123400"

    def test_ignores_non_tract_keys(self):
        payload = {
            "result": {
                "geographies": {
                    "Incorporated Places": [{"GEOID": "9999999"}],
                    "Census Tracts": [{"GEOID": "36005012300"}],
                }
            }
        }
        assert _extract_tract_geoid(payload) == "36005012300"


class TestGetJsonWithRetries:
    def test_returns_json_on_success(self):
        import requests
        from subway_equity.remote import _get_json_with_retries
        session = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = [{"count": "42"}]
        session.get.return_value = resp
        result = _get_json_with_retries(session, "https://example.com", params={})
        assert result == [{"count": "42"}]

    def test_raises_after_max_attempts_on_timeout(self):
        import requests
        from requests.exceptions import ReadTimeout
        from subway_equity.remote import _get_json_with_retries
        session = MagicMock()
        session.get.side_effect = ReadTimeout("timed out")
        with pytest.raises(ReadTimeout):
            _get_json_with_retries(session, "https://example.com", params={}, max_attempts=2)

    def test_retries_on_connection_error(self):
        import requests
        from requests.exceptions import ConnectionError as ReqConnError
        from subway_equity.remote import _get_json_with_retries
        session = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = []
        session.get.side_effect = [ReqConnError("conn"), resp]
        with patch("subway_equity.remote.sleep"):
            result = _get_json_with_retries(session, "https://example.com", params={}, max_attempts=2)
        assert result == []


class TestReadFrameCache:
    def test_returns_none_when_no_cache(self, tmp_path):
        with patch.object(remote_mod, "CACHE_DIR", tmp_path):
            from subway_equity.remote import _read_frame_cache
            result = _read_frame_cache("nonexistent.parquet")
        assert result is None

    def test_reads_parquet_when_exists(self, tmp_path):
        df = pd.DataFrame({"a": [1, 2]})
        p = tmp_path / "test.parquet"
        df.to_parquet(p, index=False)
        with patch.object(remote_mod, "CACHE_DIR", tmp_path):
            from subway_equity.remote import _read_frame_cache
            result = _read_frame_cache("test.parquet")
        assert result is not None
        assert result.shape == (2, 1)


class TestWriteFrameCache:
    def test_writes_parquet_and_returns_df(self, tmp_path):
        from subway_equity.remote import _write_frame_cache
        df = pd.DataFrame({"x": [10, 20]})
        with patch.object(remote_mod, "CACHE_DIR", tmp_path):
            result = _write_frame_cache(df, "out.parquet")
        assert result.shape == df.shape
        assert (tmp_path / "out.parquet").exists()


class TestFetchAcsDataset:
    def test_returns_cached_data_without_network(self, tmp_path):
        from subway_equity.remote import fetch_acs_dataset
        cached_df = pd.DataFrame({"NAME": ["Tract 1"], "B19013_001E": ["75000"]})
        with patch.object(remote_mod, "CACHE_DIR", tmp_path), \
             patch("subway_equity.remote._read_frame_cache", return_value=cached_df):
            result = fetch_acs_dataset("income", force_refresh=False)
        assert len(result) == 1


class TestFetchCensusRows:
    def test_raises_on_unsupported_kind(self):
        from subway_equity.remote import _fetch_census_rows
        with pytest.raises(ValueError, match="Unsupported ACS kind"):
            _fetch_census_rows("population", "061")
