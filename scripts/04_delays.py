"""Summarize line-level subway delays over the project analysis window."""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import ANALYSIS_END, ANALYSIS_START, OUTPUT_FILES
from subway_equity.io import ensure_project_dirs, filter_to_datetime_window, first_existing, normalize_columns
from subway_equity.remote import fetch_socrata_dataset


def main() -> None:
    """Build monthly and average weekly delay metrics for each line."""

    ensure_project_dirs()

    delays = normalize_columns(fetch_socrata_dataset("delays"))

    line_col = first_existing(delays, ["line", "route", "route_id", "subway_line", "train_line"])
    count_col = first_existing(
        delays,
        [
            "delay_incidents",
            "delays",
            "count",
            "incident_count",
            "incidents",
            "delay_causing_incidents",
            "incident_total",
        ],
    )

    candidate_date_cols = ["date", "service_date", "week_start", "period_start", "month", "month_beginning"]
    date_col = next((col for col in candidate_date_cols if col in delays.columns), None)
    if date_col is None:
        raise KeyError(
            "Could not find a date-like column in the delays dataset. "
            f"Available columns include: {sorted(delays.columns.tolist())[:20]}"
        )

    delays[count_col] = pd.to_numeric(delays[count_col], errors="coerce").fillna(0)
    delays = filter_to_datetime_window(delays, date_col, ANALYSIS_START, ANALYSIS_END)
    print(f"Retained {len(delays):,} delay rows within {ANALYSIS_START} to {ANALYSIS_END}.", flush=True)

    if date_col in ["month", "month_beginning"]:
        # When the source is already monthly, convert those totals into an
        # approximate weekly rate so line comparisons stay on a common scale.
        delays["month_start"] = delays[date_col].dt.to_period("M").dt.to_timestamp()
        monthly = (
            delays.groupby([line_col, "month_start"], as_index=False)[count_col]
            .sum()
            .rename(columns={line_col: "line_id", count_col: "monthly_delays"})
        )
        monthly["days_in_month"] = monthly["month_start"].dt.days_in_month
        monthly["weekly_delays"] = monthly["monthly_delays"] / (monthly["days_in_month"] / 7.0)
        monthly["month"] = monthly["month_start"].dt.to_period("M").astype(str)
        avg_weekly = (
            monthly.groupby("line_id", as_index=False)["weekly_delays"]
            .mean()
            .rename(columns={"weekly_delays": "avg_weekly_delays"})
        )
        monthly = monthly[["line_id", "month", "monthly_delays"]]
    else:
        delays["week_start"] = delays[date_col] - pd.to_timedelta(delays[date_col].dt.dayofweek, unit="D")
        delays["month"] = delays[date_col].dt.to_period("M").astype(str)

        weekly = (
            delays.groupby([line_col, "week_start"], as_index=False)[count_col]
            .sum()
            .rename(columns={line_col: "line_id", count_col: "weekly_delays"})
        )
        avg_weekly = (
            weekly.groupby("line_id", as_index=False)["weekly_delays"]
            .mean()
            .rename(columns={"weekly_delays": "avg_weekly_delays"})
        )
        monthly = (
            delays.groupby([line_col, "month"], as_index=False)[count_col]
            .sum()
            .rename(columns={line_col: "line_id", count_col: "monthly_delays"})
        )

    summary = monthly.merge(avg_weekly, on="line_id", how="left")
    summary.to_csv(OUTPUT_FILES["delay_summary"], index=False)
    print(f"Wrote delay summary to {OUTPUT_FILES['delay_summary']}")


if __name__ == "__main__":
    main()
