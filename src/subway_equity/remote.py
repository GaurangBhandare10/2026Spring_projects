
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from time import monotonic
from time import sleep
from zipfile import ZipFile

import pandas as pd
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout

try:
    from subway_equity.config import (
        ACS_CONFIG,
        ANALYSIS_END,
        ANALYSIS_START,
        CACHE_DIR,
        CENSUS_GEOCODER_CONFIG,
        GTFS_CONFIG,
        NYC_COUNTIES,
        SOCRATA_DATASETS,
    )
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from subway_equity.config import (
        ACS_CONFIG,
        ANALYSIS_END,
        ANALYSIS_START,
        CACHE_DIR,
        CENSUS_GEOCODER_CONFIG,
        GTFS_CONFIG,
        NYC_COUNTIES,
        SOCRATA_DATASETS,
    )


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "nyc-subway-equity-analysis/1.0"})
    app_token = os.getenv("SOCRATA_APP_TOKEN")
    if app_token:
        session.headers["X-App-Token"] = app_token
    return session


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def _pickle_cache_path(name: str) -> Path:
    path = _cache_path(name)
    if path.suffix == ".parquet":
        return path.with_suffix(".pkl")
    return path.with_name(f"{path.name}.pkl")


def _raise_for_status(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(
            f"Request failed with status {response.status_code} for {response.url}\n{response.text[:500]}"
        ) from exc


def _get_json_with_retries(
    session: requests.Session,
    url: str,
    *,
    params: dict,
    timeout: tuple[int, int] = (30, 300),
    max_attempts: int = 4,
) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            _raise_for_status(response)
            return response.json()
        except (ReadTimeout, RequestsConnectionError) as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            wait_seconds = 2 ** (attempt - 1)
            print(
                f"Request attempt {attempt}/{max_attempts} timed out for {url}. "
                f"Retrying in {wait_seconds}s...",
                flush=True,
            )
            sleep(wait_seconds)
    raise last_error if last_error is not None else RuntimeError("Unknown request failure")


def _read_frame_cache(cache_name: str) -> pd.DataFrame | None:
    path = _cache_path(cache_name)
    pickle_path = _pickle_cache_path(cache_name)
    if path.exists():
        try:
            return pd.read_parquet(path)
        except ImportError:
            if pickle_path.exists():
                return pd.read_pickle(pickle_path)
            raise
    if pickle_path.exists():
        return pd.read_pickle(pickle_path)
    return None


def _write_frame_cache(df: pd.DataFrame, cache_name: str) -> pd.DataFrame:
    path = _cache_path(cache_name)
    pickle_path = _pickle_cache_path(cache_name)
    try:
        df.to_parquet(path, index=False)
    except ImportError:
        df.to_pickle(pickle_path)
    return df


def fetch_socrata_dataset(name: str, force_refresh: bool = False, batch_size: int = 50000) -> pd.DataFrame:
    config = SOCRATA_DATASETS[name]
    if not force_refresh:
        cached = _read_frame_cache(config["cache_name"])
        if cached is not None:
            print(f"Loaded cached Socrata dataset '{name}' with {len(cached):,} rows.", flush=True)
            return cached

    session = build_session()
    dataset_ids = [config["dataset_id"], *config.get("fallback_dataset_ids", [])]
    last_error: Exception | None = None

    for dataset_id in dataset_ids:
        url = f"https://data.ny.gov/resource/{dataset_id}.json"

        print(f"Counting rows for Socrata dataset '{name}' using dataset id '{dataset_id}'...", flush=True)
        count_params = {"$select": "count(*)"}
        if config["where"]:
            count_params["$where"] = config["where"]

        try:
            count_payload = _get_json_with_retries(session, url, params=count_params)
            total_rows = int(count_payload[0]["count"]) if count_payload else 0
        except requests.HTTPError as exc:
            last_error = exc
            if "dataset.missing" in str(exc) and dataset_id != dataset_ids[-1]:
                print(f"Dataset id '{dataset_id}' was not found. Trying the next candidate...", flush=True)
                continue
            raise

        print(
            f"Socrata dataset '{name}' has {total_rows:,} rows to fetch in batches of {batch_size:,}.",
            flush=True,
        )

        frames: list[pd.DataFrame] = []
        total_batches = max(1, (total_rows + batch_size - 1) // batch_size)
        start_time = monotonic()
        for offset in range(0, total_rows, batch_size):
            batch_number = (offset // batch_size) + 1
            params = {"$limit": batch_size, "$offset": offset, "$order": ":id"}
            if config["where"]:
                params["$where"] = config["where"]
            payload = _get_json_with_retries(session, url, params=params)
            if not payload:
                break
            frames.append(pd.DataFrame(payload))
            fetched_rows = sum(len(frame) for frame in frames)
            elapsed = monotonic() - start_time
            print(
                f"Fetched batch {batch_number:,}/{total_batches:,} for '{name}' "
                f"({fetched_rows:,}/{total_rows:,} rows) in {elapsed:.1f}s.",
                flush=True,
            )

        if not frames:
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True)
        print(f"Caching Socrata dataset '{name}' with {len(result):,} rows.", flush=True)
        return _write_frame_cache(result, config["cache_name"])

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Unable to fetch Socrata dataset '{name}'.")


def fetch_socrata_aggregated_dataset(
    name: str,
    *,
    select: str,
    group: str,
    order: str,
    force_refresh: bool = False,
    batch_size: int = 50000,
    extra_where: str | None = None,
    cache_name_override: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    config = SOCRATA_DATASETS[name]
    cache_name = cache_name_override or config["cache_name"]
    if use_cache and not force_refresh:
        cached = _read_frame_cache(cache_name)
        if cached is not None:
            print(f"Loaded cached aggregated Socrata dataset '{name}' with {len(cached):,} rows.", flush=True)
            return cached

    session = build_session()
    url = f"https://data.ny.gov/resource/{config['dataset_id']}.json"

    print(f"Fetching aggregated Socrata dataset '{name}'...", flush=True)
    frames: list[pd.DataFrame] = []
    offset = 0
    batch_number = 0
    start_time = monotonic()

    while True:
        batch_number += 1
        params = {
            "$select": select,
            "$group": group,
            "$order": order,
            "$limit": batch_size,
            "$offset": offset,
        }
        where_clauses = [clause for clause in [config["where"], extra_where] if clause]
        if where_clauses:
            params["$where"] = " AND ".join(f"({clause})" for clause in where_clauses)

        payload = _get_json_with_retries(session, url, params=params)
        if not payload:
            break

        frame = pd.DataFrame(payload)
        frames.append(frame)
        fetched_rows = sum(len(item) for item in frames)
        elapsed = monotonic() - start_time
        print(
            f"Fetched aggregated batch {batch_number:,} for '{name}' "
            f"({fetched_rows:,} rows) in {elapsed:.1f}s.",
            flush=True,
        )

        if len(frame) < batch_size:
            break
        offset += batch_size

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    if use_cache:
        print(f"Caching aggregated Socrata dataset '{name}' with {len(result):,} rows.", flush=True)
        return _write_frame_cache(result, cache_name)
    return result


def _monthly_windows(start: str, end: str) -> list[tuple[str, str]]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    starts = pd.date_range(start=start_ts.normalize(), end=end_ts.normalize(), freq="MS")
    windows: list[tuple[str, str]] = []
    for month_start in starts:
        month_end = min(month_start + pd.offsets.MonthEnd(1) + pd.Timedelta(hours=23, minutes=45), end_ts)
        windows.append(
            (
                month_start.strftime("%Y-%m-%dT%H:%M:%S"),
                month_end.strftime("%Y-%m-%dT%H:%M:%S"),
            )
        )
    return windows


def fetch_ridership_daily_aggregates(force_refresh: bool = False, batch_size: int = 50000) -> pd.DataFrame:
    config = SOCRATA_DATASETS["ridership"]
    if not force_refresh:
        cached = _read_frame_cache(config["cache_name"])
        if cached is not None:
            print(f"Loaded cached aggregated Socrata dataset 'ridership' with {len(cached):,} rows.", flush=True)
            return cached

    month_windows = _monthly_windows(ANALYSIS_START, ANALYSIS_END)
    frames: list[pd.DataFrame] = []
    start_time = monotonic()
    for idx, (month_start, month_end) in enumerate(month_windows, start=1):
        print(
            f"Fetching aggregated ridership for window {idx}/{len(month_windows)}: "
            f"{month_start} to {month_end}",
            flush=True,
        )
        frame = fetch_socrata_aggregated_dataset(
            "ridership",
            select=(
                "station_complex_id, "
                "date_trunc_ymd(transit_timestamp) as service_date, "
                "sum(ridership) as daily_ridership"
            ),
            group="station_complex_id, service_date",
            order="service_date, station_complex_id",
            force_refresh=True,
            batch_size=batch_size,
            extra_where=f"transit_timestamp BETWEEN '{month_start}' AND '{month_end}'",
            use_cache=False,
        )
        frames.append(frame)
        fetched_rows = sum(len(item) for item in frames)
        elapsed = monotonic() - start_time
        print(
            f"Finished window {idx}/{len(month_windows)} with {len(frame):,} rows "
            f"({fetched_rows:,} total so far) in {elapsed:.1f}s.",
            flush=True,
        )

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True).drop_duplicates()
    print(f"Caching aggregated Socrata dataset 'ridership' with {len(result):,} rows.", flush=True)
    return _write_frame_cache(result, config["cache_name"])


def download_gtfs_archive(force_refresh: bool = False) -> Path:
    cache_path = _cache_path(GTFS_CONFIG["cache_name"])
    if cache_path.exists() and not force_refresh:
        return cache_path

    session = build_session()
    response = session.get(GTFS_CONFIG["subway_url"], timeout=120)
    _raise_for_status(response)
    cache_path.write_bytes(response.content)
    return cache_path


def read_gtfs_table(filename: str, force_refresh: bool = False, **kwargs) -> pd.DataFrame:
    archive_path = download_gtfs_archive(force_refresh=force_refresh)
    with ZipFile(archive_path) as zip_file:
        members = {Path(member).name: member for member in zip_file.namelist() if not member.endswith("/")}
        if filename not in members:
            raise FileNotFoundError(f"`{filename}` was not found inside {archive_path}")
        with zip_file.open(members[filename]) as handle:
            return pd.read_csv(handle, **kwargs)


def _fetch_census_rows(kind: str, county: str) -> pd.DataFrame:
    if kind == "income":
        variables = ACS_CONFIG["income_variables"]
    elif kind == "race":
        variables = ACS_CONFIG["race_variables"]
    else:
        raise ValueError(f"Unsupported ACS kind: {kind}")

    session = build_session()
    response = session.get(
        f"https://api.census.gov/data/{ACS_CONFIG['year']}/acs/{ACS_CONFIG['dataset']}",
        params={
            "get": ",".join(["NAME", *variables]),
            "for": "tract:*",
            "in": f"state:36 county:{county}",
        },
        timeout=120,
    )
    _raise_for_status(response)
    rows = response.json()
    return pd.DataFrame(rows[1:], columns=rows[0])


def fetch_acs_dataset(kind: str, force_refresh: bool = False) -> pd.DataFrame:
    cache_name = f"acs_{kind}_{ACS_CONFIG['year']}_nyc.parquet"
    if not force_refresh:
        cached = _read_frame_cache(cache_name)
        if cached is not None:
            return cached

    frames = [_fetch_census_rows(kind, county) for county in NYC_COUNTIES]
    return _write_frame_cache(pd.concat(frames, ignore_index=True), cache_name)


def _extract_tract_geoid(payload: dict) -> str | None:
    geographies = payload.get("result", {}).get("geographies", {})
    for key, values in geographies.items():
        if "tract" in key.lower() and values:
            return values[0].get("GEOID")
    return None


def geocode_station_tracts(
    stations: pd.DataFrame,
    *,
    station_id_col: str,
    station_name_col: str,
    lon_col: str,
    lat_col: str,
    force_refresh: bool = False,
) -> pd.DataFrame:
    cache_name = "station_tract_geocoder_cache.parquet"
    cached = None if force_refresh else _read_frame_cache(cache_name)
    completed_ids: set[str] = set()
    records: list[dict] = []
    if cached is not None and not cached.empty:
        records = cached.to_dict("records")
        completed_ids = set(cached["station_complex_id"].astype(str))
        print(f"Loaded {len(records):,} cached station-to-tract mappings.", flush=True)

    session = build_session()
    total = len(stations)
    start_time = monotonic()
    for idx, row in enumerate(stations.itertuples(index=False), start=1):
        station_id = str(getattr(row, station_id_col))
        if station_id in completed_ids:
            if idx % 50 == 0 or idx == total:
                print(f"Checked {idx:,}/{total:,} stations; cache already covers these rows.", flush=True)
            continue

        response = session.get(
            "https://geocoding.geo.census.gov/geocoder/geographies/coordinates",
            params={
                "x": getattr(row, lon_col),
                "y": getattr(row, lat_col),
                "benchmark": CENSUS_GEOCODER_CONFIG["benchmark"],
                "vintage": CENSUS_GEOCODER_CONFIG["vintage"],
                "format": "json",
            },
            timeout=120,
        )
        _raise_for_status(response)
        payload = response.json()
        records.append(
            {
                "station_complex_id": station_id,
                "station_name": getattr(row, station_name_col),
                "stop_lon": getattr(row, lon_col),
                "stop_lat": getattr(row, lat_col),
                "tract_geoid": _extract_tract_geoid(payload),
            }
        )
        completed_ids.add(station_id)

        if idx % 25 == 0 or idx == total:
            elapsed = monotonic() - start_time
            print(
                f"Geocoded {len(completed_ids):,}/{total:,} stations in {elapsed:.1f}s.",
                flush=True,
            )
            _write_frame_cache(pd.DataFrame(records), cache_name)
        sleep(0.02)

    return _write_frame_cache(pd.DataFrame(records), cache_name)
