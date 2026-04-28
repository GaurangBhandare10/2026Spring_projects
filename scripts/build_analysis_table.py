from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES
from subway_equity.io import ensure_project_dirs, normalize_columns, read_table
from subway_equity.metrics import weighted_average


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    crosswalk = normalize_columns(read_table(OUTPUT_FILES["station_crosswalk"]))
    service = normalize_columns(read_table(OUTPUT_FILES["service_frequency"]))
    ridership = normalize_columns(read_table(OUTPUT_FILES["ridership_summary"]))
    demographics = normalize_columns(read_table(OUTPUT_FILES["tract_demographics"]))
    delays = normalize_columns(read_table(OUTPUT_FILES["delay_summary"]))
    return crosswalk, service, ridership, demographics, delays


def build_station_table(
    crosswalk: pd.DataFrame,
    service: pd.DataFrame,
    ridership: pd.DataFrame,
    demographics: pd.DataFrame,
) -> pd.DataFrame:
    if "station_complex_id" not in crosswalk.columns:
        crosswalk["station_complex_id"] = crosswalk.get("parent_station", crosswalk.get("stop_id"))
    station = crosswalk.merge(demographics, on="tract_geoid", how="left")
    station = station.merge(
        service.rename(columns={"parent_station": "station_complex_id"}),
        on="station_complex_id",
        how="left",
    )

    ridership_wide = (
        ridership.pivot_table(
            index=["station_complex_id", "year"],
            columns="day_type",
            values="avg_daily_ridership",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    ratio_frame = (
        ridership.loc[:, ["station_complex_id", "year", "ridership_ratio"]]
        .drop_duplicates()
    )
    ridership_wide = ridership_wide.merge(ratio_frame, on=["station_complex_id", "year"], how="left")
    ridership_wide["avg_daily_ridership"] = ridership_wide[["weekday", "weekend"]].mean(axis=1)
    return station.merge(ridership_wide, on="station_complex_id", how="left")


def summarize_line_income(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "ridership_weighted_income": weighted_average(
                frame["median_household_income"],
                frame["avg_daily_ridership"].fillna(1),
            ),
            "share_low_income_stations": (frame["income_quartile"] == "Q1").mean(),
        }
    )


def build_line_table(service: pd.DataFrame, station_analysis: pd.DataFrame, delays: pd.DataFrame) -> pd.DataFrame:
    if "routes_served" not in service.columns:
        return pd.DataFrame()

    service_key = "parent_station" if "parent_station" in service.columns else "station_complex_id"
    line_station = service[[service_key, "routes_served"]].copy()
    line_station["line_id"] = line_station["routes_served"].astype(str).str.split(",")
    line_station = line_station.explode("line_id")
    line_station = line_station.rename(columns={service_key: "station_complex_id"})
    line_station = line_station.merge(
        station_analysis[
            ["station_complex_id", "median_household_income", "avg_daily_ridership", "income_quartile"]
        ].drop_duplicates(),
        on="station_complex_id",
        how="left",
    )

    line_income = line_station.groupby("line_id").apply(summarize_line_income).reset_index()
    weekly_delay = delays[["line_id", "avg_weekly_delays"]].drop_duplicates()
    monthly_delay = (
        delays.groupby("line_id", as_index=False)["monthly_delays"]
        .mean()
        .rename(columns={"monthly_delays": "avg_monthly_delays"})
    )
    return line_income.merge(weekly_delay, on="line_id", how="left").merge(
        monthly_delay, on="line_id", how="left"
    )


def main() -> None:
    ensure_project_dirs()

    crosswalk, service, ridership, demographics, delays = load_inputs()
    station_analysis = build_station_table(crosswalk, service, ridership, demographics)
    line_analysis = build_line_table(service, station_analysis, delays)

    station_analysis.to_csv(OUTPUT_FILES["station_analysis"], index=False)
    line_analysis.to_csv(OUTPUT_FILES["line_analysis"], index=False)

    print(f"Wrote station analysis table to {OUTPUT_FILES['station_analysis']}")
    print(f"Wrote line analysis table to {OUTPUT_FILES['line_analysis']}")


if __name__ == "__main__":
    main()
