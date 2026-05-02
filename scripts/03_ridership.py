"""Create station-level ridership summaries and recovery ratios."""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import ANALYSIS_END, ANALYSIS_START, OUTPUT_FILES, RIDERSHIP_BASELINE_YEAR
from subway_equity.io import ensure_project_dirs, filter_to_datetime_window, first_existing, normalize_columns
from subway_equity.metrics import compute_ridership_ratio
from subway_equity.remote import fetch_ridership_daily_aggregates


def main() -> None:
    """Aggregate daily ridership into station/year/day-type summaries."""

    ensure_project_dirs()

    print("Fetching aggregated daily ridership from the MTA Socrata API...", flush=True)
    ridership = normalize_columns(fetch_ridership_daily_aggregates())
    print(f"Fetched {len(ridership):,} daily ridership rows. Building station-year summaries...", flush=True)

    station_col = first_existing(ridership, ["station_complex_id", "complex_id", "station_id", "station"])
    rider_col = first_existing(ridership, ["daily_ridership", "ridership", "riders", "estimated_ridership"])
    timestamp_col = first_existing(ridership, ["service_date", "transit_timestamp", "timestamp", "date"])
    ridership = filter_to_datetime_window(ridership, timestamp_col, ANALYSIS_START, ANALYSIS_END)
    print(
        f"Retained {len(ridership):,} ridership rows within {ANALYSIS_START} to {ANALYSIS_END}.",
        flush=True,
    )

    ridership[rider_col] = pd.to_numeric(ridership[rider_col], errors="coerce")
    ridership["date"] = ridership[timestamp_col].dt.date
    ridership["year"] = ridership[timestamp_col].dt.year
    ridership["day_type"] = ridership[timestamp_col].dt.dayofweek.map(lambda d: "weekend" if d >= 5 else "weekday")

    summary = (
        ridership.groupby([station_col, "year", "day_type"], as_index=False)[rider_col]
        .mean()
        .rename(columns={station_col: "station_complex_id", rider_col: "avg_daily_ridership"})
    )
    print(f"Built {len(summary):,} station/year/day-type summary rows.", flush=True)

    summary["ridership_ratio"] = compute_ridership_ratio(
        summary,
        station_col="station_complex_id",
        year_col="year",
        riders_col="avg_daily_ridership",
        baseline_year=RIDERSHIP_BASELINE_YEAR,
    )

    summary.to_csv(OUTPUT_FILES["ridership_summary"], index=False)
    print(
        f"Wrote ridership summary to {OUTPUT_FILES['ridership_summary']} "
        f"using {RIDERSHIP_BASELINE_YEAR} as the baseline year for ridership_ratio.",
        flush=True,
    )


if __name__ == "__main__":
    main()
