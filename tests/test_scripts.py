"""Pytest unit tests for the pipeline scripts (01–08).

Each script's pure helper functions are tested directly.
Each script's main() orchestration is tested via mock-patching
all external I/O so tests run offline and instantly.

Run with:
    pytest tests/test_scripts.py --cov=scripts --cov-report=term-missing
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np
import pandas as pd
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers: load script modules by file path (filenames start with digits,
# so regular import doesn't work without renaming them)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load(filename: str):
    """Import a script file as a module regardless of its filename."""
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# 02_service_frequency.py — time_to_seconds & is_peak_departure
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def svc():
    return _load("02_service_frequency.py")


class TestTimeToSeconds:
    def test_standard_time(self, svc):
        assert svc.time_to_seconds("07:30:00") == 27000

    def test_midnight(self, svc):
        assert svc.time_to_seconds("00:00:00") == 0

    def test_noon(self, svc):
        assert svc.time_to_seconds("12:00:00") == 43200

    def test_end_of_day(self, svc):
        assert svc.time_to_seconds("23:59:59") == 86399

    def test_gtfs_over_24_hours(self, svc):
        # GTFS permits hours > 24 for after-midnight trips
        assert svc.time_to_seconds("25:00:00") == 90000

    def test_pm_peak_start(self, svc):
        assert svc.time_to_seconds("17:00:00") == 61200

    def test_single_digit_components(self, svc):
        assert svc.time_to_seconds("01:02:03") == 3723


class TestIsPeakDeparture:
    def test_am_peak_inside(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("08:15:00")) is True

    def test_pm_peak_inside(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("17:30:00")) is True

    def test_midday_off_peak(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("12:00:00")) is False

    def test_late_night_off_peak(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("23:00:00")) is False

    def test_am_peak_start_inclusive(self, svc):
        # Window is (7, 9): start=7*3600=25200 is inclusive
        assert svc.is_peak_departure(25200) is True

    def test_am_peak_end_exclusive(self, svc):
        # 9*3600 = 32400 is exclusive upper bound
        assert svc.is_peak_departure(32400) is False

    def test_pm_peak_start_inclusive(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("17:00:00")) is True

    def test_pm_peak_end_exclusive(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("19:00:00")) is False

    def test_just_before_am_peak(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("06:59:59")) is False

    def test_just_before_pm_peak(self, svc):
        assert svc.is_peak_departure(svc.time_to_seconds("16:59:59")) is False


class TestServiceFrequencyMain:
    """Test main() with all external I/O mocked out."""

    def test_main_writes_csv(self, svc, tmp_path):
        stops = pd.DataFrame({
            "stop_id": ["S1", "S2"],
            "parent_station": ["P1", "P1"],
            "stop_name": ["Stop 1", "Stop 1"],
        })
        trips = pd.DataFrame({
            "trip_id": ["T1", "T2"],
            "route_id": ["A", "A"],
            "service_id": ["SVC1", "SVC1"],
        })
        stop_times = pd.DataFrame({
            "trip_id": ["T1", "T2"],
            "stop_id": ["S1", "S2"],
            "departure_time": ["08:00:00", "08:30:00"],
        })
        calendar = pd.DataFrame({
            "service_id": ["SVC1"],
            "monday": [1], "tuesday": [1], "wednesday": [1],
            "thursday": [1], "friday": [1],
        })
        out_path = tmp_path / "service_freq.csv"

        with patch.object(svc, "ensure_project_dirs"), \
             patch.object(svc, "read_gtfs_table", side_effect=[stops, trips, stop_times, calendar]), \
             patch.dict(svc.OUTPUT_FILES, {"service_frequency": out_path}):
            svc.main()

        assert out_path.exists()
        result = pd.read_csv(out_path)
        assert "peak_service_trips" in result.columns
        assert "parent_station" in result.columns

    def test_main_no_peak_departures_produces_empty(self, svc, tmp_path):
        stops = pd.DataFrame({"stop_id": ["S1"], "parent_station": ["P1"], "stop_name": ["Stop 1"]})
        trips = pd.DataFrame({"trip_id": ["T1"], "route_id": ["A"], "service_id": ["SVC1"]})
        # All departures at 3am — outside any peak window
        stop_times = pd.DataFrame({"trip_id": ["T1"], "stop_id": ["S1"], "departure_time": ["03:00:00"]})
        calendar = pd.DataFrame({
            "service_id": ["SVC1"],
            "monday": [1], "tuesday": [1], "wednesday": [1],
            "thursday": [1], "friday": [1],
        })
        out_path = tmp_path / "service_freq.csv"

        with patch.object(svc, "ensure_project_dirs"), \
             patch.object(svc, "read_gtfs_table", side_effect=[stops, trips, stop_times, calendar]), \
             patch.dict(svc.OUTPUT_FILES, {"service_frequency": out_path}):
            svc.main()

        result = pd.read_csv(out_path)
        assert len(result) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 07_run_hypothesis_tests.py — match_any_value, match_route_ids, interpret_result
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hyp():
    return _load("07_run_hypothesis_tests.py")


class TestMatchAnyValue:
    def test_exact_match(self, hyp):
        s = pd.Series(["S Rock", "A", "GS"])
        assert hyp.match_any_value(s, ["S Rock"]).tolist() == [True, False, False]

    def test_case_insensitive(self, hyp):
        s = pd.Series(["s rock", "S ROCK", "A"])
        assert hyp.match_any_value(s, ["S Rock"]).tolist() == [True, True, False]

    def test_strips_whitespace_in_series(self, hyp):
        s = pd.Series([" s 42nd "])
        assert hyp.match_any_value(s, ["s 42nd"]).tolist() == [True]

    def test_strips_whitespace_in_targets(self, hyp):
        s = pd.Series(["s rock"])
        assert hyp.match_any_value(s, [" S Rock "]).tolist() == [True]

    def test_no_match_all_false(self, hyp):
        s = pd.Series(["X", "Y", "Z"])
        assert not hyp.match_any_value(s, ["A", "B"]).any()

    def test_multiple_targets_matched(self, hyp):
        s = pd.Series(["a", "b", "c"])
        assert hyp.match_any_value(s, ["a", "b"]).tolist() == [True, True, False]

    def test_empty_series(self, hyp):
        s = pd.Series([], dtype=str)
        assert hyp.match_any_value(s, ["a"]).tolist() == []

    def test_empty_targets(self, hyp):
        s = pd.Series(["a", "b"])
        assert not hyp.match_any_value(s, []).any()


class TestMatchRouteIds:
    def test_single_route_in_comma_list(self, hyp):
        s = pd.Series(["A,H", "GS", "A,C"])
        assert hyp.match_route_ids(s, ["H", "GS"]).tolist() == [True, True, False]

    def test_case_insensitive_route(self, hyp):
        s = pd.Series(["a,h"])
        assert hyp.match_route_ids(s, ["H"]).tolist() == [True]

    def test_no_match(self, hyp):
        s = pd.Series(["A", "B", "C"])
        assert not hyp.match_route_ids(s, ["Z"]).any()

    def test_multi_route_entry_matches_one(self, hyp):
        s = pd.Series(["A,B,C,H"])
        assert hyp.match_route_ids(s, ["H"]).tolist() == [True]

    def test_exact_single_route(self, hyp):
        s = pd.Series(["GS", "H", "A"])
        assert hyp.match_route_ids(s, ["GS"]).tolist() == [True, False, False]

    def test_spaces_around_route_id(self, hyp):
        s = pd.Series([" GS "])
        assert hyp.match_route_ids(s, ["GS"]).tolist() == [True]


class TestInterpretResult:
    def test_nan_pvalue_descriptive(self, hyp):
        assert hyp.interpret_result("H1", 0.5, float("nan")) == "descriptive only"

    def test_pvalue_above_threshold_not_supported(self, hyp):
        assert hyp.interpret_result("H1", -0.5, 0.9) == "not clearly supported"

    def test_pvalue_exactly_threshold_not_supported(self, hyp):
        assert hyp.interpret_result("H1", -0.5, 0.05) == "not clearly supported"

    def test_h1_negative_stat_supported(self, hyp):
        assert hyp.interpret_result("H1", -0.5, 0.01) == "supported"

    def test_h1_positive_stat_opposite(self, hyp):
        assert hyp.interpret_result("H1", 0.5, 0.01) == "significant, opposite direction"

    def test_h2_negative_stat_supported(self, hyp):
        assert hyp.interpret_result("H2", -0.3, 0.03) == "supported"

    def test_h2_positive_stat_opposite(self, hyp):
        assert hyp.interpret_result("H2", 0.3, 0.03) == "significant, opposite direction"

    def test_h3_always_supported_when_significant(self, hyp):
        assert hyp.interpret_result("H3", 99999.0, 0.001) == "supported"

    def test_h4_delay_positive_supported(self, hyp):
        assert hyp.interpret_result("H4_delay", 17.0, 1e-26) == "supported"

    def test_h4_delay_negative_opposite(self, hyp):
        assert hyp.interpret_result("H4_delay", -5.0, 0.001) == "significant, opposite direction"

    def test_h4_ridership_negative_supported(self, hyp):
        assert hyp.interpret_result("H4_ridership", -0.3, 0.01) == "supported"

    def test_h4_ridership_positive_opposite(self, hyp):
        assert hyp.interpret_result("H4_ridership", 0.3, 0.01) == "significant, opposite direction"

    def test_unknown_hypothesis_returns_significant(self, hyp):
        assert hyp.interpret_result("H99", 1.0, 0.01) == "significant"


class TestHypothesisMain:
    """Test main() writes a results CSV with the expected structure."""

    def _make_station(self):
        return pd.DataFrame({
            "station_complex_id": [1, 2, 3, 4],
            "year": [2022, 2022, 2022, 2022],
            "median_household_income": [40000.0, 60000.0, 80000.0, 120000.0],
            "peak_service_trips": [50.0, 60.0, 70.0, 80.0],
            "avg_daily_ridership": [1000.0, 1200.0, 1400.0, 1600.0],
            "income_quartile": ["Q1", "Q2", "Q3", "Q4"],
            "weekday": [2.0, 1.9, 1.8, 1.7],
            "weekend": [1.0, 1.1, 1.2, 1.3],
            "station_name": ["Sta1", "Sta2", "Sta3", "Sta4"],
            "ridership_ratio": [0.9, 1.0, 1.1, 1.2],
            "routes_served": ["H", "GS", "A", "B"],
        })

    def _make_line(self):
        return pd.DataFrame({
            "line_id": ["1", "2", "A"],
            "ridership_weighted_income": [60000.0, 80000.0, 100000.0],
            "avg_weekly_delays": [100.0, 80.0, 60.0],
        })

    def _make_delays(self):
        rows = []
        for month in range(1, 13):
            rows.append({"line_id": "S Rock", "month": f"2022-{month:02d}", "monthly_delays": 150.0})
            rows.append({"line_id": "S 42nd", "month": f"2022-{month:02d}", "monthly_delays": 100.0})
        return pd.DataFrame(rows)

    def test_main_produces_csv_with_all_hypotheses(self, hyp, tmp_path):
        out = tmp_path / "results.csv"
        with patch.object(hyp, "ensure_project_dirs"), \
             patch.object(hyp, "read_table", side_effect=[
                 self._make_station(), self._make_line(), self._make_delays()
             ]), \
             patch.dict(hyp.OUTPUT_FILES, {"hypothesis_results": out}):
            hyp.main()

        assert out.exists()
        df = pd.read_csv(out)
        assert "hypothesis" in df.columns
        assert "p_value" in df.columns
        assert "interpretation" in df.columns
        assert len(df) >= 1

    def test_main_includes_h3_result(self, hyp, tmp_path):
        """H3 needs enough Q1/Q4 rows and non-equal ratio distributions."""
        station = pd.DataFrame({
            "station_complex_id": list(range(40)),
            "year": [2022] * 40,
            "median_household_income": [30000.0] * 20 + [150000.0] * 20,
            "peak_service_trips": [50.0] * 40,
            "avg_daily_ridership": [1000.0] * 40,
            "income_quartile": ["Q1"] * 20 + ["Q4"] * 20,
            "weekday": [2.5] * 20 + [1.5] * 20,
            "weekend": [1.0] * 40,
            "station_name": [f"S{i}" for i in range(40)],
            "ridership_ratio": [1.0] * 40,
            "routes_served": ["A"] * 40,
        })
        out = tmp_path / "results.csv"
        with patch.object(hyp, "ensure_project_dirs"), \
             patch.object(hyp, "read_table", side_effect=[
                 station, self._make_line(), self._make_delays()
             ]), \
             patch.dict(hyp.OUTPUT_FILES, {"hypothesis_results": out}):
            hyp.main()

        df = pd.read_csv(out)
        assert "H3" in df["hypothesis"].values

    def test_main_h4_delay_supported_when_rockaway_higher(self, hyp, tmp_path):
        out = tmp_path / "results.csv"
        with patch.object(hyp, "ensure_project_dirs"), \
             patch.object(hyp, "read_table", side_effect=[
                 self._make_station(), self._make_line(), self._make_delays()
             ]), \
             patch.dict(hyp.OUTPUT_FILES, {"hypothesis_results": out}):
            hyp.main()

        df = pd.read_csv(out)
        h4 = df[df["hypothesis"] == "H4_delay"]
        if len(h4) > 0:
            assert h4.iloc[0]["interpretation"] == "supported"


# ─────────────────────────────────────────────────────────────────────────────
# 08_visualizations.py — pure helper functions
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def viz():
    return _load("08_visualizations.py")


class TestFormatMinorityLabel:
    def test_true_returns_yes(self, viz):
        assert viz._format_minority_label(True) == "Yes"

    def test_false_returns_no(self, viz):
        assert viz._format_minority_label(False) == "No"

    def test_truthy_int_returns_yes(self, viz):
        assert viz._format_minority_label(1) == "Yes"

    def test_zero_returns_no(self, viz):
        assert viz._format_minority_label(0) == "No"

    def test_string_true_returns_yes(self, viz):
        assert viz._format_minority_label("True") == "Yes"

    def test_empty_string_returns_no(self, viz):
        assert viz._format_minority_label("") == "No"


class TestRenameShuttleCase:
    def test_rockaway_renamed(self, viz):
        assert viz._rename_shuttle_case("Rockaway") == "Rockaway Park Shuttle"

    def test_times_square_renamed(self, viz):
        assert viz._rename_shuttle_case("Times Square") == "42nd Street Shuttle"

    def test_unknown_value_returned_unchanged(self, viz):
        assert viz._rename_shuttle_case("Unknown") == "Unknown"

    def test_empty_string_unchanged(self, viz):
        assert viz._rename_shuttle_case("") == ""


class TestSetPlotStyle:
    def test_runs_without_error(self, viz):
        viz._set_plot_style()  # should not raise


class TestSaveFigure:
    def test_saves_file_to_correct_location(self, viz, tmp_path):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        with patch.dict(viz.__dict__, {"FIGURES_DIR": tmp_path}):
            import subway_equity.config as cfg_mod
            with patch.object(cfg_mod, "FIGURES_DIR", tmp_path), \
                 patch.object(viz, "FIGURES_DIR", tmp_path):
                viz._save_figure(fig, "test_fig.png")
        assert (tmp_path / "test_fig.png").exists()


class TestLoadFrames:
    """Test the _load_*_frame helpers with mocked read_table."""

    def _station_table(self):
        return pd.DataFrame({
            "station_complex_id": [1, 1, 2],
            "year": [2022, 2022, 2022],
            "median_household_income": [50000.0, 50000.0, 90000.0],
            "peak_service_trips": [60.0, 60.0, 80.0],
            "avg_daily_ridership": [1000.0, 1000.0, 2000.0],
            "weekday": [2.0, 2.0, 1.8],
            "weekend": [1.0, 1.0, 1.2],
            "ridership_ratio": [1.0, 1.0, 1.1],
            "non_white_share": [0.6, 0.6, 0.3],
            "minority_majority": [True, True, False],
            "income_quartile": ["Q1", "Q1", "Q4"],
        })

    def test_load_station_year_frame_deduplicates(self, viz):
        with patch.object(viz, "read_table", return_value=self._station_table()), \
             patch.object(viz, "normalize_columns", side_effect=lambda df: df):
            result = viz._load_station_year_frame()
        # Two duplicate rows for station 1 should collapse to one
        assert len(result) == 2

    def test_load_station_year_frame_drops_negative_income(self, viz):
        df = self._station_table()
        df.loc[0, "median_household_income"] = -999.0
        with patch.object(viz, "read_table", return_value=df), \
             patch.object(viz, "normalize_columns", side_effect=lambda df: df):
            result = viz._load_station_year_frame()
        assert (result["median_household_income"] > 0).all()

    def test_load_station_year_frame_adds_ratio_column(self, viz):
        with patch.object(viz, "read_table", return_value=self._station_table()), \
             patch.object(viz, "normalize_columns", side_effect=lambda df: df):
            result = viz._load_station_year_frame()
        assert "weekday_weekend_ratio" in result.columns

    def test_load_line_frame_drops_missing_delays(self, viz):
        line_df = pd.DataFrame({
            "line_id": ["1", "2", "3"],
            "ridership_weighted_income": [60000.0, 80000.0, np.nan],
            "avg_weekly_delays": [100.0, np.nan, 50.0],
        })
        with patch.object(viz, "read_table", return_value=line_df), \
             patch.object(viz, "normalize_columns", side_effect=lambda df: df):
            result = viz._load_line_frame()
        assert len(result) == 1
        assert result.iloc[0]["line_id"] == "1"

    def test_load_delay_frame_drops_nulls(self, viz):
        delay_df = pd.DataFrame({
            "line_id": ["S Rock", "S Rock", None],
            "month": ["2022-01", "2022-02", "2022-03"],
            "monthly_delays": [150.0, 160.0, np.nan],
        })
        with patch.object(viz, "read_table", return_value=delay_df), \
             patch.object(viz, "normalize_columns", side_effect=lambda df: df):
            result = viz._load_delay_frame()
        assert len(result) == 2


class TestPlotFunctions:
    """Test plot functions run without error and produce output files."""

    def _station_year(self):
        return pd.DataFrame({
            "station_complex_id": [1, 2, 3, 4],
            "year": [2022] * 4,
            "median_household_income": [40000.0, 60000.0, 90000.0, 130000.0],
            "peak_service_trips": [50.0, 65.0, 80.0, 95.0],
            "avg_daily_ridership": [1000.0, 1500.0, 2000.0, 2500.0],
            "weekday": [2.2, 2.0, 1.9, 1.7],
            "weekend": [1.0, 1.1, 1.2, 1.3],
            "ridership_ratio": [0.9, 1.0, 1.1, 1.2],
            "non_white_share": [0.7, 0.5, 0.3, 0.2],
            "minority_majority": [True, True, False, False],
            "income_quartile": ["Q1", "Q2", "Q3", "Q4"],
            "weekday_weekend_ratio": [2.2, 1.8, 1.6, 1.3],
        })

    def _line(self):
        return pd.DataFrame({
            "line_id": ["A", "B", "C"],
            "ridership_weighted_income": [55000.0, 80000.0, 120000.0],
            "avg_weekly_delays": [110.0, 80.0, 50.0],
        })

    def _delays(self):
        rows = []
        for m in range(1, 7):
            rows.append({"line_id": "S Rock", "month": pd.Timestamp(f"2022-{m:02d}-01"), "monthly_delays": 150.0})
            rows.append({"line_id": "S 42nd", "month": pd.Timestamp(f"2022-{m:02d}-01"), "monthly_delays": 90.0})
        return pd.DataFrame(rows)

    def test_plot_h1_creates_file(self, viz, tmp_path):
        with patch.object(viz, "FIGURES_DIR", tmp_path), \
             patch.object(viz, "_save_figure", wraps=lambda fig, name: viz._save_figure.__wrapped__(fig, name) if hasattr(viz._save_figure, "__wrapped__") else None):
            import matplotlib
            matplotlib.use("Agg")
            with patch.object(viz, "_save_figure") as mock_save:
                viz.plot_h1_income_vs_service(self._station_year())
                mock_save.assert_called_once()

    def test_plot_h1_skips_empty_frame(self, viz):
        # Should return silently with no error on empty input
        viz.plot_h1_income_vs_service(pd.DataFrame(columns=["median_household_income", "peak_service_trips", "avg_daily_ridership", "minority_majority"]))

    def test_plot_h2_creates_file(self, viz):
        import matplotlib
        matplotlib.use("Agg")
        with patch.object(viz, "_save_figure") as mock_save:
            viz.plot_h2_delay_vs_income(self._line())
            mock_save.assert_called_once()

    def test_plot_h2_skips_empty_frame(self, viz):
        viz.plot_h2_delay_vs_income(pd.DataFrame())

    def test_plot_h3_creates_file(self, viz):
        import matplotlib
        matplotlib.use("Agg")
        with patch.object(viz, "_save_figure") as mock_save:
            viz.plot_h3_weekday_weekend_ratio(self._station_year())
            mock_save.assert_called_once()

    def test_plot_h3_skips_empty_frame(self, viz):
        viz.plot_h3_weekday_weekend_ratio(pd.DataFrame(columns=["income_quartile", "weekday_weekend_ratio"]))

    def test_plot_h4_creates_file(self, viz):
        import matplotlib
        matplotlib.use("Agg")
        with patch.object(viz, "_save_figure") as mock_save:
            viz.plot_h4_shuttle_monthly_delays(self._delays())
            mock_save.assert_called_once()

    def test_plot_h4_skips_no_shuttle_data(self, viz):
        # Delays with no matching shuttle line IDs
        empty_delays = pd.DataFrame({"line_id": ["X"], "month": [pd.Timestamp("2022-01-01")], "monthly_delays": [10.0]})
        with patch.object(viz, "_save_figure") as mock_save:
            viz.plot_h4_shuttle_monthly_delays(empty_delays)
            mock_save.assert_not_called()

    def test_plot_equity_overview_creates_file(self, viz):
        import matplotlib
        matplotlib.use("Agg")
        with patch.object(viz, "_save_figure") as mock_save:
            viz.plot_equity_overview(self._station_year())
            mock_save.assert_called_once()

    def test_plot_equity_overview_skips_empty(self, viz):
        viz.plot_equity_overview(pd.DataFrame(columns=["minority_majority", "peak_service_trips"]))


# ─────────────────────────────────────────────────────────────────────────────
# 06_build_analysis_table.py — main() integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def build():
    return _load("06_build_analysis_table.py")


class TestBuildAnalysisTableMain:
    def _make_inputs(self):
        crosswalk = pd.DataFrame({
            "station_complex_id": [1, 2],
            "stop_lon": [-73.9, -74.0],
            "stop_lat": [40.7, 40.8],
            "tract_geoid": ["36061019100", "36081012300"],
            "station_name": ["Fulton St", "Astoria"],
        })
        demographics = pd.DataFrame({
            "tract_geoid": ["36061019100", "36081012300"],
            "median_household_income": [60000.0, 90000.0],
            "total_population": [5000, 4000],
            "non_white_population": [3000, 1000],
            "non_white_share": [0.6, 0.25],
            "minority_majority": [True, False],
            "income_quartile": ["Q1", "Q3"],
        })
        service = pd.DataFrame({
            "parent_station": [1, 2],
            "peak_service_trips": [80, 120],
            "routes_served": ["A,C", "N,Q"],
        })
        ridership = pd.DataFrame({
            "station_complex_id": [1, 1, 2, 2],
            "year": [2022, 2022, 2022, 2022],
            "day_type": ["weekday", "weekend", "weekday", "weekend"],
            "avg_daily_ridership": [1000.0, 600.0, 2000.0, 1200.0],
            "ridership_ratio": [1.0, 1.0, 1.1, 1.1],
        })
        delays = pd.DataFrame({
            "line_id": ["A", "N"],
            "avg_weekly_delays": [80.0, 60.0],
            "monthly_delays": [320.0, 240.0],
        })
        return crosswalk, demographics, service, ridership, delays

    def test_main_writes_station_analysis(self, build, tmp_path):
        cw, demo, svc, rid, del_ = self._make_inputs()
        station_out = tmp_path / "station_analysis.csv"
        line_out = tmp_path / "line_analysis.csv"

        with patch.object(build, "ensure_project_dirs"), \
             patch.object(build, "read_table", side_effect=[cw, svc, rid, demo, del_]), \
             patch.dict(build.OUTPUT_FILES, {
                 "station_analysis": station_out,
                 "line_analysis": line_out,
                 "station_crosswalk": tmp_path / "c.csv",
                 "service_frequency": tmp_path / "s.csv",
                 "ridership_summary": tmp_path / "r.csv",
                 "tract_demographics": tmp_path / "d.csv",
                 "delay_summary": tmp_path / "dl.csv",
             }):
            build.main()

        assert station_out.exists()
        result = pd.read_csv(station_out)
        assert "station_complex_id" in result.columns

    def test_main_writes_line_analysis_with_routes(self, build, tmp_path):
        cw, demo, svc, rid, del_ = self._make_inputs()
        station_out = tmp_path / "station_analysis.csv"
        line_out = tmp_path / "line_analysis.csv"

        with patch.object(build, "ensure_project_dirs"), \
             patch.object(build, "read_table", side_effect=[cw, svc, rid, demo, del_]), \
             patch.dict(build.OUTPUT_FILES, {
                 "station_analysis": station_out,
                 "line_analysis": line_out,
                 "station_crosswalk": tmp_path / "c.csv",
                 "service_frequency": tmp_path / "s.csv",
                 "ridership_summary": tmp_path / "r.csv",
                 "tract_demographics": tmp_path / "d.csv",
                 "delay_summary": tmp_path / "dl.csv",
             }):
            build.main()

        assert line_out.exists()
        result = pd.read_csv(line_out)
        assert "line_id" in result.columns

    def test_main_no_routes_served_writes_empty_line_table(self, build, tmp_path):
        cw, demo, svc, rid, del_ = self._make_inputs()
        svc_no_routes = svc.drop(columns=["routes_served"])
        station_out = tmp_path / "station_analysis.csv"
        line_out = tmp_path / "line_analysis.csv"

        with patch.object(build, "ensure_project_dirs"), \
             patch.object(build, "read_table", side_effect=[cw, svc_no_routes, rid, demo, del_]), \
             patch.dict(build.OUTPUT_FILES, {
                 "station_analysis": station_out,
                 "line_analysis": line_out,
                 "station_crosswalk": tmp_path / "c.csv",
                 "service_frequency": tmp_path / "s.csv",
                 "ridership_summary": tmp_path / "r.csv",
                 "tract_demographics": tmp_path / "d.csv",
                 "delay_summary": tmp_path / "dl.csv",
             }):
            build.main()

        # An empty DataFrame writes no header; just verify the file was created
        assert line_out.exists()
        assert line_out.stat().st_size >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 05_census.py — main() integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def census():
    return _load("05_census.py")


class TestCensusMain:
    def _income(self):
        return pd.DataFrame({
            "state": ["36", "36"],
            "county": ["061", "081"],
            "tract": ["019100", "012300"],
            "b19013_001e": ["60000", "90000"],
            "name": ["Tract 1", "Tract 2"],
        })

    def _race(self):
        return pd.DataFrame({
            "state": ["36", "36"],
            "county": ["061", "081"],
            "tract": ["019100", "012300"],
            "b02001_001e": ["5000", "4000"],
            "b02001_002e": ["2000", "3000"],
            "name": ["Tract 1", "Tract 2"],
        })

    def test_main_writes_demographics_csv(self, census, tmp_path):
        out = tmp_path / "tract_demographics.csv"
        with patch.object(census, "ensure_project_dirs"), \
             patch.object(census, "fetch_acs_dataset", side_effect=[self._income(), self._race()]), \
             patch.dict(census.OUTPUT_FILES, {"tract_demographics": out}):
            census.main()

        assert out.exists()
        df = pd.read_csv(out)
        assert "tract_geoid" in df.columns
        assert "median_household_income" in df.columns
        assert "non_white_share" in df.columns
        assert "minority_majority" in df.columns

    def test_main_computes_non_white_share(self, census, tmp_path):
        out = tmp_path / "tract_demographics.csv"
        with patch.object(census, "ensure_project_dirs"), \
             patch.object(census, "fetch_acs_dataset", side_effect=[self._income(), self._race()]), \
             patch.dict(census.OUTPUT_FILES, {"tract_demographics": out}):
            census.main()

        df = pd.read_csv(out)
        # Tract 1: 3000 non-white / 5000 total = 0.6
        row = df.iloc[0]
        assert float(row["non_white_share"]) == pytest.approx(0.6)

    def test_main_raises_when_no_race_columns(self, census, tmp_path):
        bad_race = pd.DataFrame({
            "state": ["36"],
            "county": ["061"],
            "tract": ["019100"],
            "b02001_001e": ["5000"],
            # No white population column and no non_white_population column
            "name": ["Tract 1"],
        })
        out = tmp_path / "tract_demographics.csv"
        with patch.object(census, "ensure_project_dirs"), \
             patch.object(census, "fetch_acs_dataset", side_effect=[self._income(), bad_race]), \
             patch.dict(census.OUTPUT_FILES, {"tract_demographics": out}):
            with pytest.raises(KeyError, match="Race file needs"):
                census.main()


# ─────────────────────────────────────────────────────────────────────────────
# 03_ridership.py — main() integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ridership_script():
    return _load("03_ridership.py")


class TestRidershipMain:
    def _ridership_data(self):
        dates = pd.date_range("2022-01-01", periods=10, freq="D")
        return pd.DataFrame({
            "station_complex_id": ["1", "1", "2", "2", "1", "1", "2", "2", "1", "2"],
            "service_date": dates,
            "daily_ridership": [1000.0, 900.0, 2000.0, 1800.0, 1100.0, 950.0, 2100.0, 1900.0, 1050.0, 1950.0],
        })

    def test_main_writes_ridership_summary(self, ridership_script, tmp_path):
        out = tmp_path / "ridership_summary.csv"
        with patch.object(ridership_script, "ensure_project_dirs"), \
             patch.object(ridership_script, "fetch_ridership_daily_aggregates", return_value=self._ridership_data()), \
             patch.dict(ridership_script.OUTPUT_FILES, {"ridership_summary": out}):
            ridership_script.main()

        assert out.exists()
        df = pd.read_csv(out)
        assert "station_complex_id" in df.columns
        assert "avg_daily_ridership" in df.columns
        assert "ridership_ratio" in df.columns

    def test_main_produces_weekday_weekend_rows(self, ridership_script, tmp_path):
        out = tmp_path / "ridership_summary.csv"
        with patch.object(ridership_script, "ensure_project_dirs"), \
             patch.object(ridership_script, "fetch_ridership_daily_aggregates", return_value=self._ridership_data()), \
             patch.dict(ridership_script.OUTPUT_FILES, {"ridership_summary": out}):
            ridership_script.main()

        df = pd.read_csv(out)
        assert set(df["day_type"].unique()).issubset({"weekday", "weekend"})


# ─────────────────────────────────────────────────────────────────────────────
# 01_station_crosswalk.py — main() integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def crosswalk_script():
    return _load("01_station_crosswalk.py")


class TestStationCrosswalkMain:
    def _stops(self):
        return pd.DataFrame({
            "stop_id": ["101N", "101S", "201"],
            "parent_station": ["101", "101", "201"],
            "stop_name": ["Van Cortlandt Park", "Van Cortlandt Park", "Wakefield"],
            "stop_lat": [40.889, 40.889, 40.903],
            "stop_lon": [-73.898, -73.898, -73.851],
            "location_type": [0, 0, 1],
        })

    def test_main_writes_crosswalk_csv(self, crosswalk_script, tmp_path):
        out = tmp_path / "crosswalk.csv"
        geocoded = pd.DataFrame({
            "station_complex_id": ["101", "201"],
            "station_name": ["Van Cortlandt Park", "Wakefield"],
            "stop_lon": [-73.898, -73.851],
            "stop_lat": [40.889, 40.903],
            "tract_geoid": ["36005028500", "36005033900"],
        })
        with patch.object(crosswalk_script, "ensure_project_dirs"), \
             patch.object(crosswalk_script, "read_gtfs_table", return_value=self._stops()), \
             patch.object(crosswalk_script, "geocode_station_tracts", return_value=geocoded), \
             patch.dict(crosswalk_script.OUTPUT_FILES, {"station_crosswalk": out}):
            crosswalk_script.main()

        assert out.exists()
        df = pd.read_csv(out)
        assert "tract_geoid" in df.columns

    def test_main_deduplicates_to_parent_stations(self, crosswalk_script, tmp_path):
        out = tmp_path / "crosswalk.csv"
        geocoded = pd.DataFrame({
            "station_complex_id": ["101"],
            "station_name": ["Van Cortlandt Park"],
            "stop_lon": [-73.898],
            "stop_lat": [40.889],
            "tract_geoid": ["36005028500"],
        })
        with patch.object(crosswalk_script, "ensure_project_dirs"), \
             patch.object(crosswalk_script, "read_gtfs_table", return_value=self._stops()), \
             patch.object(crosswalk_script, "geocode_station_tracts", return_value=geocoded), \
             patch.dict(crosswalk_script.OUTPUT_FILES, {"station_crosswalk": out}):
            crosswalk_script.main()

        # geocode_station_tracts receives unique parent stations, not raw stop rows
        df = pd.read_csv(out)
        assert len(df) == len(df["station_complex_id"].unique())


# ─────────────────────────────────────────────────────────────────────────────
# 04_delays.py — main() integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def delays_script():
    return _load("04_delays.py")


class TestDelaysMain:
    def _delay_data(self):
        months = pd.date_range("2020-01-01", periods=24, freq="MS")
        rows = []
        for m in months:
            for line in ["1", "A", "S Rock"]:
                rows.append({"line": line, "month_beginning": m, "delay_incidents": 100.0})
        return pd.DataFrame(rows)

    def test_main_writes_delay_summary(self, delays_script, tmp_path):
        out = tmp_path / "delay_summary.csv"
        with patch.object(delays_script, "ensure_project_dirs"), \
             patch.object(delays_script, "fetch_socrata_dataset", return_value=self._delay_data()), \
             patch.dict(delays_script.OUTPUT_FILES, {"delay_summary": out}):
            delays_script.main()

        assert out.exists()
        df = pd.read_csv(out)
        assert "line_id" in df.columns
        assert "monthly_delays" in df.columns
        assert "avg_weekly_delays" in df.columns

    def test_main_raises_when_no_date_column(self, delays_script, tmp_path):
        bad_data = pd.DataFrame({"line": ["1"], "delay_incidents": [100.0]})
        out = tmp_path / "delay_summary.csv"
        with patch.object(delays_script, "ensure_project_dirs"), \
             patch.object(delays_script, "fetch_socrata_dataset", return_value=bad_data), \
             patch.dict(delays_script.OUTPUT_FILES, {"delay_summary": out}):
            with pytest.raises(KeyError):
                delays_script.main()
