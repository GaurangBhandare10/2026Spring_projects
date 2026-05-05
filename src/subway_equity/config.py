"""Central configuration values shared across the subway equity pipeline."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"
CACHE_DIR = INTERIM_DIR / "remote_cache"

RAW_FILES = {
    "ridership": RAW_DIR / "mta_hourly_ridership.csv",
    "delays": RAW_DIR / "mta_delays.csv",
    "income": RAW_DIR / "acs_income.csv",
    "race": RAW_DIR / "acs_race.csv",
    "tracts": RAW_DIR / "nyc_tracts.geojson",
    "gtfs_stops": RAW_DIR / "stops.txt",
    "gtfs_trips": RAW_DIR / "trips.txt",
    "gtfs_stop_times": RAW_DIR / "stop_times.txt",
    "gtfs_calendar": RAW_DIR / "calendar.txt",
}

OUTPUT_FILES = {
    "station_crosswalk": PROCESSED_DIR / "station_tract_crosswalk.csv",
    "service_frequency": PROCESSED_DIR / "station_peak_service_frequency.csv",
    "ridership_summary": PROCESSED_DIR / "station_ridership_summary.csv",
    "delay_summary": PROCESSED_DIR / "line_delay_summary.csv",
    "tract_demographics": PROCESSED_DIR / "tract_demographics.csv",
    "station_analysis": PROCESSED_DIR / "station_analysis_table.csv",
    "line_analysis": PROCESSED_DIR / "line_analysis_table.csv",
    "hypothesis_results": TABLES_DIR / "hypothesis_results.csv",
}

RIDERSHIP_BASELINE_YEAR = 2020
ANALYSIS_YEARS = [2020, 2021, 2022, 2023, 2024]
PEAK_WINDOWS = [(7, 9), (17, 19)]
ANALYSIS_START = "2020-01-01T00:00:00"
ANALYSIS_END = "2024-12-31T23:45:00"
NYC_COUNTIES = ["005", "047", "061", "081", "085"]

SOCRATA_DATASETS = {
    "ridership": {
        "dataset_id": "wujg-7c2s",
        "where": "transit_timestamp BETWEEN '2020-01-01T00:00:00' AND '2024-12-31T23:45:00'",
        "cache_name": "mta_hourly_ridership_daily_2020_2024.parquet",
    },
    "delays": {
        "dataset_id": "5298-hm4w",
        "fallback_dataset_ids": ["g937-7k7c"],
        "where": None,
        "cache_name": "mta_subway_delays.parquet",
    },
}

ACS_CONFIG = {
    "dataset": "acs5",
    "year": 2022,
    "income_variables": ["B19013_001E"],
    "race_variables": ["B02001_001E", "B02001_002E"],
}

GTFS_CONFIG = {
    "subway_url": "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip",
    "cache_name": "gtfs_subway.zip",
}

CENSUS_GEOCODER_CONFIG = {
    "benchmark": "Public_AR_Current",
    "vintage": "Current_Current",
}

SHUTTLE_CASE_STUDY = {
    "rockaway": {
        "delay_line_ids": ["S Rock"],
        "route_ids": ["H"],
        "station_names": [
            "Broad Channel",
            "Beach 90 St",
            "Beach 98 St",
            "Beach 105 St",
            "Rockaway Park-Beach 116 St",
        ],
    },
    "times_square": {
        "delay_line_ids": ["S 42nd"],
        "route_ids": ["GS"],
        "station_names": [
            "Times Sq-42 St",
            "Grand Central-42 St",
        ],
    },
}
