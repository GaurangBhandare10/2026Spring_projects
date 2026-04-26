from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES, PEAK_WINDOWS
from subway_equity.io import ensure_project_dirs, normalize_columns
from subway_equity.remote import read_gtfs_table


def time_to_seconds(value: str) -> int:
    """Convert HH:MM:SS text to seconds after midnight.

    >>> time_to_seconds("01:30:15")
    5415
    """
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def is_peak_departure(seconds: int) -> bool:
    """Return True when a departure falls inside the defined peak windows.

    >>> is_peak_departure(8 * 3600)
    True
    >>> is_peak_departure(12 * 3600)
    False
    """
    for start_hour, end_hour in PEAK_WINDOWS:
        start = start_hour * 3600
        end = end_hour * 3600
        if start <= seconds < end:
            return True
    return False


def main() -> None:
    ensure_project_dirs()

    stops = normalize_columns(read_gtfs_table("stops.txt"))
    trips = normalize_columns(read_gtfs_table("trips.txt"))
    stop_times = normalize_columns(read_gtfs_table("stop_times.txt"))
    calendar = normalize_columns(read_gtfs_table("calendar.txt"))

    weekday_services = calendar.loc[
        (calendar.get("monday", 0) == 1)
        & (calendar.get("tuesday", 0) == 1)
        & (calendar.get("wednesday", 0) == 1)
        & (calendar.get("thursday", 0) == 1)
        & (calendar.get("friday", 0) == 1),
        ["service_id"],
    ]

    merged = stop_times.merge(trips[["trip_id", "route_id", "service_id"]], on="trip_id", how="left")
    merged = merged.merge(weekday_services, on="service_id", how="inner")
    merged = merged.merge(stops[["stop_id", "parent_station", "stop_name"]], on="stop_id", how="left")

    departure_col = "departure_time" if "departure_time" in merged.columns else "arrival_time"
    merged = merged.dropna(subset=[departure_col])
    merged["departure_seconds"] = merged[departure_col].astype(str).map(time_to_seconds)
    merged = merged.loc[merged["departure_seconds"].map(is_peak_departure)]

    merged["parent_station"] = merged["parent_station"].fillna(merged["stop_id"])
    frequency = (
        merged.groupby("parent_station", as_index=False)
        .agg(
            peak_service_trips=("trip_id", "nunique"),
            routes_served=("route_id", lambda x: ",".join(sorted(set(x.dropna().astype(str))))),
        )
    )

    frequency.to_csv(OUTPUT_FILES["service_frequency"], index=False)
    print(f"Wrote service frequency for {len(frequency):,} stations to {OUTPUT_FILES['service_frequency']}")


if __name__ == "__main__":
    main()
