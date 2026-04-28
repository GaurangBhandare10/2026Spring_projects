from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES, SHUTTLE_LABELS
from subway_equity.io import ensure_project_dirs, normalize_columns, read_table
from subway_equity.metrics import bootstrap_median_difference, partial_correlation


def detect_shuttle(line_ids: pd.Series, keywords: list[str]) -> pd.Series:
    """Find line labels that match a shuttle keyword list.

    >>> import pandas as pd
    >>> detect_shuttle(pd.Series(["Rockaway Park S", "A", "42 St S"]), ["rockaway", "rs"]).tolist()
    [True, False, False]
    """
    pattern = "|".join(keywords)
    return line_ids.astype(str).str.lower().str.contains(pattern, na=False)


def run_h1(station: pd.DataFrame) -> dict | None:
    h1_frame = station.dropna(
        subset=["median_household_income", "peak_service_trips", "avg_daily_ridership"]
    ).drop_duplicates(subset=["station_complex_id", "year"])
    if not h1_frame.empty:
        corr, p_value = partial_correlation(
            h1_frame["median_household_income"],
            h1_frame["peak_service_trips"],
            h1_frame["avg_daily_ridership"],
        )
        return {
            "hypothesis": "H1",
            "test": "partial correlation",
            "statistic": corr,
            "p_value": p_value,
            "n": len(h1_frame),
        }
    return None


def run_h2(line: pd.DataFrame) -> dict | None:
    h2_frame = line.dropna(subset=["ridership_weighted_income", "avg_weekly_delays"])
    if not h2_frame.empty:
        rho, p_value = stats.spearmanr(
            h2_frame["ridership_weighted_income"], h2_frame["avg_weekly_delays"]
        )
        return {
            "hypothesis": "H2",
            "test": "spearman correlation",
            "statistic": rho,
            "p_value": p_value,
            "n": len(h2_frame),
        }
    return None


def run_h3(station: pd.DataFrame) -> dict | None:
    h3_frame = station.dropna(subset=["weekday", "weekend", "income_quartile"]).copy()
    if not h3_frame.empty:
        h3_frame["weekday_weekend_ratio"] = h3_frame["weekday"] / h3_frame["weekend"]
        low = h3_frame.loc[h3_frame["income_quartile"] == "Q1", "weekday_weekend_ratio"]
        high = h3_frame.loc[h3_frame["income_quartile"] == "Q4", "weekday_weekend_ratio"]
        if len(low) > 0 and len(high) > 0:
            u_stat, p_value = stats.mannwhitneyu(low, high, alternative="two-sided")
            ci_low, ci_high = bootstrap_median_difference(low, high)
            return {
                "hypothesis": "H3",
                "test": "mann-whitney u",
                "statistic": u_stat,
                "p_value": p_value,
                "n": len(low) + len(high),
                "ci_low": ci_low,
                "ci_high": ci_high,
            }
    return None


def run_h4_delay(delays: pd.DataFrame) -> dict | None:
    if not delays.empty:
        monthly = delays.dropna(subset=["line_id", "monthly_delays"]).drop_duplicates(
            subset=["line_id", "month"]
        )
        rockaway = monthly.loc[
            detect_shuttle(monthly["line_id"], SHUTTLE_LABELS["rockaway"]),
            "monthly_delays",
        ]
        times_square = monthly.loc[
            detect_shuttle(monthly["line_id"], SHUTTLE_LABELS["times_square"]),
            "monthly_delays",
        ]
        if len(rockaway) > 1 and len(times_square) > 1:
            t_stat, p_value = stats.ttest_ind(rockaway, times_square, equal_var=False)
            return {
                "hypothesis": "H4_delay",
                "test": "welch t-test",
                "statistic": t_stat,
                "p_value": p_value,
                "n": len(rockaway) + len(times_square),
            }
    return None


def run_h4_ridership(station: pd.DataFrame) -> dict | None:
    name_col = "station_name" if "station_name" in station.columns else "stop_name"
    if "ridership_ratio" in station.columns and name_col in station.columns:
        shuttle_station = station.dropna(subset=[name_col, "ridership_ratio"]).copy()
        rockaway_ratio = shuttle_station.loc[
            shuttle_station[name_col].astype(str).str.lower().str.contains("rockaway", na=False),
            "ridership_ratio",
        ]
        times_square_ratio = shuttle_station.loc[
            shuttle_station[name_col].astype(str).str.lower().str.contains("42 st|times sq|times square", na=False),
            "ridership_ratio",
        ]
        if len(rockaway_ratio) > 0 and len(times_square_ratio) > 0:
            return {
                "hypothesis": "H4_ridership",
                "test": "descriptive difference in mean ridership ratio",
                "statistic": rockaway_ratio.mean() - times_square_ratio.mean(),
                "p_value": np.nan,
                "n": len(rockaway_ratio) + len(times_square_ratio),
            }
    return None


def main() -> None:
    ensure_project_dirs()

    station = normalize_columns(read_table(OUTPUT_FILES["station_analysis"]))
    line = normalize_columns(read_table(OUTPUT_FILES["line_analysis"]))
    delays = normalize_columns(read_table(OUTPUT_FILES["delay_summary"]))

    results = [
        result
        for result in [
            run_h1(station),
            run_h2(line),
            run_h3(station),
            run_h4_delay(delays),
            run_h4_ridership(station),
        ]
        if result is not None
    ]

    output = pd.DataFrame(results)
    output.to_csv(OUTPUT_FILES["hypothesis_results"], index=False)
    print(f"Wrote hypothesis results to {OUTPUT_FILES['hypothesis_results']}")
    if output.empty:
        print("No tests were run. Check processed inputs and update shuttle labels if needed.")


if __name__ == "__main__":
    main()
