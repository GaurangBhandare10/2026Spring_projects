"""Build a station-to-Census-tract crosswalk from GTFS stop coordinates."""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES
from subway_equity.io import ensure_project_dirs, normalize_columns
from subway_equity.remote import geocode_station_tracts, read_gtfs_table


def main() -> None:
    """Geocode one representative row per station complex to a tract GEOID."""

    ensure_project_dirs()

    print("Loading GTFS stops from cached or live MTA feed...", flush=True)
    stops = normalize_columns(read_gtfs_table("stops.txt"))
    if "stop_lon" not in stops.columns or "stop_lat" not in stops.columns:
        raise KeyError("The GTFS stops feed must include stop_lon and stop_lat.")

    if "location_type" in stops.columns:
        station_rows = stops.loc[stops["location_type"].fillna(0).astype(str).isin(["1", "1.0"])].copy()
    else:
        station_rows = pd.DataFrame()

    if station_rows.empty:
        # Some GTFS feeds identify station complexes via parent_station rather
        # than dedicated location_type rows, so we fall back to one child stop
        # per complex when needed.
        station_rows = stops.copy()
        station_rows["station_complex_id"] = station_rows["parent_station"].fillna(station_rows["stop_id"])
        station_rows = (
            station_rows.sort_values(["station_complex_id", "stop_id"])
            .drop_duplicates(subset=["station_complex_id"])
            .copy()
        )
    else:
        station_rows["station_complex_id"] = station_rows["stop_id"]

    station_rows["station_name"] = station_rows.get("stop_name", station_rows["station_complex_id"])
    station_rows = station_rows[["station_complex_id", "station_name", "stop_lon", "stop_lat"]].drop_duplicates()
    print(f"Prepared {len(station_rows):,} station coordinates for Census tract lookup.", flush=True)

    crosswalk = geocode_station_tracts(
        station_rows,
        station_id_col="station_complex_id",
        station_name_col="station_name",
        lon_col="stop_lon",
        lat_col="stop_lat",
    )
    crosswalk.to_csv(OUTPUT_FILES["station_crosswalk"], index=False)
    print(f"Wrote {len(crosswalk):,} station-to-tract rows to {OUTPUT_FILES['station_crosswalk']}")


if __name__ == "__main__":
    main()
