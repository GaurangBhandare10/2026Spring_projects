from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from subway_equity.config import OUTPUT_FILES
from subway_equity.io import ensure_project_dirs, first_existing, normalize_columns
from subway_equity.metrics import assign_income_quartiles
from subway_equity.remote import fetch_acs_dataset


def to_numeric_clean(series):
    """Convert Census API strings to numbers and drop negative placeholder values.

    >>> import pandas as pd
    >>> to_numeric_clean(pd.Series(["10", "-666666666", "25"])).tolist()
    [10.0, nan, 25.0]
    """
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.mask(numeric < 0)


def main() -> None:
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
    demo["median_household_income"] = to_numeric_clean(demo["median_household_income"])
    race_subset["total_population"] = to_numeric_clean(race_subset["total_population"])

    if non_white_col is not None:
        race_subset["non_white_population"] = to_numeric_clean(race[non_white_col])
    elif white_col is not None:
        white_population = to_numeric_clean(race[white_col])
        race_subset["non_white_population"] = race_subset["total_population"] - white_population
    else:
        raise KeyError("Race file needs either non-white population or enough ACS race columns to derive it.")

    demographics = demo.merge(race_subset, on="tract_geoid", how="left")
    demographics["non_white_share"] = demographics["non_white_population"] / demographics["total_population"]
    demographics["minority_majority"] = demographics["non_white_share"] > 0.5
    demographics = demographics.loc[demographics["median_household_income"].notna()].copy()
    demographics["income_quartile"] = assign_income_quartiles(demographics, "median_household_income")

    demographics.to_csv(OUTPUT_FILES["tract_demographics"], index=False)
    print(f"Wrote tract demographics to {OUTPUT_FILES['tract_demographics']}")


if __name__ == "__main__":
    main()
