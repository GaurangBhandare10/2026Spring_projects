"""Input/output helpers shared across the NYC subway equity pipeline."""

from pathlib import Path

import pandas as pd

try:
    from subway_equity.config import CACHE_DIR, FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, RAW_DIR, TABLES_DIR
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from subway_equity.config import CACHE_DIR, FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, RAW_DIR, TABLES_DIR


def ensure_project_dirs() -> None:
    """Create the folders used by the pipeline if they do not exist yet."""
    for folder in [RAW_DIR, INTERIM_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR, CACHE_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make column names lowercase and easier to work with.

    >>> import pandas as pd
    >>> normalize_columns(pd.DataFrame({"Station Name": [1], "Ride-Count": [2]})).columns.tolist()
    ['station_name', 'ride_count']
    """
    renamed = {
        column: column.strip().lower().replace(" ", "_").replace("-", "_")
        for column in df.columns
    }
    return df.rename(columns=renamed)


def first_existing(df: pd.DataFrame, options: list[str]) -> str:
    """Return the first column name that exists in the dataframe.

    >>> import pandas as pd
    >>> first_existing(pd.DataFrame({"a": [1], "b": [2]}), ["x", "b", "a"])
    'b'
    """
    for name in options:
        if name in df.columns:
            return name
    raise KeyError(f"None of these columns were found: {options}")


def filter_to_datetime_window(df: pd.DataFrame, date_col: str, start: str, end: str) -> pd.DataFrame:
    """Keep only rows whose datetime falls inside the analysis window.

    >>> import pandas as pd
    >>> df = pd.DataFrame({"ts": ["2020-01-01", "2020-01-03", "2020-01-05"], "value": [1, 2, 3]})
    >>> filtered = filter_to_datetime_window(df, "ts", "2020-01-02", "2020-01-04")
    >>> filtered["value"].tolist()
    [2]
    """
    filtered = df.copy()
    filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce")
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return filtered.loc[filtered[date_col].between(start_ts, end_ts, inclusive="both")].copy()


def read_table(path: Path) -> pd.DataFrame:
    """Read one processed table from disk."""
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file type: {path}")
