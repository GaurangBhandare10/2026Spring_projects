"""Prepare tract-level ACS income and race measures for station linkage."""
""" To pull tract income and race data - https://api.census.gov/data/2022/acs/acs5.html """

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES
from subway_equity.io import ensure_project_dirs, first_existing, normalize_columns
from subway_equity.metrics import assign_income_quartiles
from subway_equity.remote import fetch_acs_dataset


def main() -> None:
    """Fetch ACS tract data and derive the project demographic indicators."""

    ensure_project_dirs()

    income = normalize_columns(fetch_acs_dataset("income"))
    race = normalize_columns(fetch_acs_dataset("race"))

    if {"state", "county", "tract"}.issubset(income.columns):
        income["tract_geoid"] = income["state"] + income["county"] + income["tract"]
    if {"state", "county", "tract"}.issubset(race.columns):
        race["tract_geoid"] = race["state"] + race["county"] + race["tract"]

    geoid_col_income = first_existing(income, ["tract_geoid", "geoid"])
    geoid_col_race = first_existing(race, ["tract_geoid", "geoid"])
    income_col = first_existing(income, ["median_household_income", "median_income", "b19013_001e"])
    total_col = first_existing(race, ["total_population", "total", "b02001_001e"])

    race_cols = [col for col in race.columns if col.startswith("b02001_")]
    white_col = next((col for col in race_cols if col.endswith("002e")), None)
    non_white_col = next((col for col in ["non_white_population", "nonwhite_population"] if col in race.columns), None)

    demo = income[[geoid_col_income, income_col]].rename(
        columns={geoid_col_income: "tract_geoid", income_col: "median_household_income"}
    )
    race_subset = race[[geoid_col_race, total_col]].rename(
        columns={geoid_col_race: "tract_geoid", total_col: "total_population"}
    )
    race_subset["total_population"] = pd.to_numeric(race_subset["total_population"], errors="coerce")

    if non_white_col is not None:
        race_subset["non_white_population"] = pd.to_numeric(race[non_white_col], errors="coerce")
    elif white_col is not None:
        # ACS race tables often provide total and white population directly,
        # so non-white population can be derived when a dedicated column is
        # not returned by the API response.
        white_population = pd.to_numeric(race[white_col], errors="coerce")
        race_subset["non_white_population"] = race_subset["total_population"] - white_population
    else:
        raise KeyError("Race file needs either non-white population or enough ACS race columns to derive it.")

    demographics = demo.merge(race_subset, on="tract_geoid", how="left")
    demographics["median_household_income"] = pd.to_numeric(
        demographics["median_household_income"], errors="coerce"
    )
    demographics["total_population"] = pd.to_numeric(demographics["total_population"], errors="coerce")
    demographics["non_white_population"] = pd.to_numeric(demographics["non_white_population"], errors="coerce")
    demographics["non_white_share"] = demographics["non_white_population"] / demographics["total_population"]
    demographics["minority_majority"] = demographics["non_white_share"] > 0.5
    demographics["income_quartile"] = assign_income_quartiles(demographics, "median_household_income")

    demographics.to_csv(OUTPUT_FILES["tract_demographics"], index=False)
    print(f"Wrote tract demographics to {OUTPUT_FILES['tract_demographics']}")


if __name__ == "__main__":
    main()
