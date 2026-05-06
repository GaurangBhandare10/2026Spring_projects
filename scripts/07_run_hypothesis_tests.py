"""Run the project hypothesis tests and export a compact results table."""
""" For H2 - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html 
    For H3 - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html
    For h4 - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES, SHUTTLE_CASE_STUDY
from subway_equity.io import ensure_project_dirs, normalize_columns, read_table
from subway_equity.metrics import (
    bootstrap_correlation_interval,
    bootstrap_mean_difference,
    bootstrap_median_difference,
    bootstrap_partial_correlation_interval,
    partial_correlation,
)


def match_any_value(values: pd.Series, targets: list[str]) -> pd.Series:
    """Return ``True`` where a value matches one of the target labels exactly.

    Matching is case-insensitive and ignores surrounding whitespace.

    >>> series = pd.Series(["S Rock", " s 42nd ", "A"])
    >>> match_any_value(series, ["s rock", "S 42nd"]).tolist()
    [True, True, False]
    """

    normalized_targets = {target.strip().lower() for target in targets}
    return values.astype(str).str.strip().str.lower().isin(normalized_targets)


def match_route_ids(routes: pd.Series, route_ids: list[str]) -> pd.Series:
    """Return ``True`` where a comma-separated route field contains a target.

    >>> series = pd.Series(["A,H", "GS", "A,C"])
    >>> match_route_ids(series, ["H", "GS"]).tolist()
    [True, True, False]
    """

    target_ids = {route_id.strip().upper() for route_id in route_ids}

    def has_route(value: object) -> bool:
        tokens = {token.strip().upper() for token in str(value).split(",")}
        return bool(tokens & target_ids)

    return routes.map(has_route)


def interpret_result(hypothesis: str, statistic: float, p_value: float) -> str:
    """Return a short, report-friendly interpretation label for a result."""

    if pd.isna(p_value):
        return "descriptive only"
    if p_value >= 0.05:
        return "not clearly supported"

    if hypothesis == "H1":
        return "supported" if statistic < 0 else "significant, opposite direction"
    if hypothesis == "H2":
        return "supported" if statistic < 0 else "significant, opposite direction"
    if hypothesis == "H3":
        return "supported"
    if hypothesis == "H4_delay":
        return "supported" if statistic > 0 else "significant, opposite direction"
    if hypothesis == "H4_ridership":
        return "supported" if statistic < 0 else "significant, opposite direction"
    return "significant"


def main() -> None:
    """Compute hypothesis-level statistics from processed analysis tables."""

    ensure_project_dirs()

    station = normalize_columns(read_table(OUTPUT_FILES["station_analysis"]))
    line = normalize_columns(read_table(OUTPUT_FILES["line_analysis"]))
    delays = normalize_columns(read_table(OUTPUT_FILES["delay_summary"]))

    results = []
    notes: list[str] = []

    h1_frame = station.dropna(
        subset=["median_household_income", "peak_service_trips", "avg_daily_ridership"]
    ).drop_duplicates(subset=["station_complex_id", "year"])
    if not h1_frame.empty:
        corr, p_value = partial_correlation(
            h1_frame["median_household_income"],
            h1_frame["peak_service_trips"],
            h1_frame["avg_daily_ridership"],
        )
        ci_low, ci_high = bootstrap_partial_correlation_interval(
            h1_frame["median_household_income"],
            h1_frame["peak_service_trips"],
            h1_frame["avg_daily_ridership"],
        )
        results.append(
            {
                "hypothesis": "H1",
                "test": "partial correlation",
                "statistic": corr,
                "p_value": p_value,
                "n": len(h1_frame),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "interpretation": interpret_result("H1", corr, p_value),
            }
        )

    h2_frame = line.dropna(subset=["ridership_weighted_income", "avg_weekly_delays"])
    if not h2_frame.empty:
        rho, p_value = stats.spearmanr(
            h2_frame["ridership_weighted_income"], h2_frame["avg_weekly_delays"]
        )
        ci_low, ci_high = bootstrap_correlation_interval(
            h2_frame["ridership_weighted_income"],
            h2_frame["avg_weekly_delays"],
            method="spearman",
        )
        results.append(
            {
                "hypothesis": "H2",
                "test": "spearman correlation",
                "statistic": rho,
                "p_value": p_value,
                "n": len(h2_frame),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "interpretation": interpret_result("H2", rho, p_value),
            }
        )

    h3_frame = station.dropna(subset=["weekday", "weekend", "income_quartile"]).copy()
    if not h3_frame.empty:
        h3_frame["weekday_weekend_ratio"] = h3_frame["weekday"] / h3_frame["weekend"]
        low = h3_frame.loc[h3_frame["income_quartile"] == "Q1", "weekday_weekend_ratio"]
        high = h3_frame.loc[h3_frame["income_quartile"] == "Q4", "weekday_weekend_ratio"]
        if len(low) > 0 and len(high) > 0:
            u_stat, p_value = stats.mannwhitneyu(low, high, alternative="two-sided")
            ci_low, ci_high = bootstrap_median_difference(low, high)
            results.append(
                {
                    "hypothesis": "H3",
                    "test": "mann-whitney u",
                    "statistic": u_stat,
                    "p_value": p_value,
                    "n": len(low) + len(high),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "interpretation": interpret_result("H3", u_stat, p_value),
                }
            )

    if not delays.empty:
        # Delay comparisons use monthly rows so the shuttle case study has a
        # meaningful within-line distribution for the Welch t-test.
        monthly = delays.dropna(subset=["line_id", "monthly_delays"]).drop_duplicates(
            subset=["line_id", "month"]
        )
        rockaway = monthly.loc[
            match_any_value(monthly["line_id"], SHUTTLE_CASE_STUDY["rockaway"]["delay_line_ids"]),
            "monthly_delays",
        ]
        times_square = monthly.loc[
            match_any_value(monthly["line_id"], SHUTTLE_CASE_STUDY["times_square"]["delay_line_ids"]),
            "monthly_delays",
        ]
        if len(rockaway) > 1 and len(times_square) > 1:
            t_stat, p_value = stats.ttest_ind(rockaway, times_square, equal_var=False)
            ci_low, ci_high = bootstrap_mean_difference(rockaway, times_square)
            results.append(
                {
                    "hypothesis": "H4_delay",
                    "test": "welch t-test",
                    "statistic": t_stat,
                    "p_value": p_value,
                    "n": len(rockaway) + len(times_square),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "interpretation": interpret_result("H4_delay", t_stat, p_value),
                }
            )
        else:
            notes.append(
                "Skipped H4_delay because exact shuttle delay rows were not available for both "
                f"line ids {SHUTTLE_CASE_STUDY['rockaway']['delay_line_ids']} and "
                f"{SHUTTLE_CASE_STUDY['times_square']['delay_line_ids']}."
            )

    name_col = "station_name" if "station_name" in station.columns else "stop_name"
    if {"ridership_ratio", "routes_served", name_col}.issubset(station.columns):
        # Use exact route ids plus exact station names so the shuttle case
        # study does not accidentally pull unrelated "Rockaway" or "42 St"
        # stations into the comparison.
        shuttle_station = station.dropna(subset=[name_col, "ridership_ratio", "routes_served"]).copy()
        rockaway_mask = (
            match_route_ids(shuttle_station["routes_served"], SHUTTLE_CASE_STUDY["rockaway"]["route_ids"])
            & match_any_value(shuttle_station[name_col], SHUTTLE_CASE_STUDY["rockaway"]["station_names"])
        )
        times_square_mask = (
            match_route_ids(shuttle_station["routes_served"], SHUTTLE_CASE_STUDY["times_square"]["route_ids"])
            & match_any_value(shuttle_station[name_col], SHUTTLE_CASE_STUDY["times_square"]["station_names"])
        )
        rockaway_ratio = shuttle_station.loc[
            rockaway_mask,
            "ridership_ratio",
        ]
        times_square_ratio = shuttle_station.loc[
            times_square_mask,
            "ridership_ratio",
        ]
        if len(rockaway_ratio) > 0 and len(times_square_ratio) > 0:
            mean_difference = rockaway_ratio.mean() - times_square_ratio.mean()
            ci_low, ci_high = bootstrap_mean_difference(rockaway_ratio, times_square_ratio)
            results.append(
                {
                    "hypothesis": "H4_ridership",
                    "test": "descriptive mean difference in ridership ratio",
                    "statistic": mean_difference,
                    "p_value": np.nan,
                    "n": len(rockaway_ratio) + len(times_square_ratio),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "interpretation": interpret_result("H4_ridership", mean_difference, np.nan),
                }
            )
        else:
            notes.append(
                "Skipped H4_ridership because no non-null ridership ratios were matched to the exact "
                "Rockaway (`H`) and 42nd Street (`GS`) shuttle station sets."
            )

    output = pd.DataFrame(results)
    output.to_csv(OUTPUT_FILES["hypothesis_results"], index=False)
    print(f"Wrote hypothesis results to {OUTPUT_FILES['hypothesis_results']}")
    if output.empty:
        print("No tests were run. Check processed inputs and update shuttle labels if needed.")
    for note in notes:
        print(note)


if __name__ == "__main__":
    main()
