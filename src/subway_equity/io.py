"""Input/output helpers shared across the NYC subway equity pipeline."""

from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd

try:
    from subway_equity.config import CACHE_DIR, FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, RAW_DIR, RAW_FILES, TABLES_DIR
except ModuleNotFoundError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from subway_equity.config import CACHE_DIR, FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, RAW_DIR, RAW_FILES, TABLES_DIR


def ensure_project_dirs() -> None:
    """Create the standard project folders if they do not already exist.

    >>> import tempfile
    >>> from pathlib import Path
    >>> from unittest.mock import patch
    >>> import subway_equity.io as _m
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     dirs = [Path(tmp) / d for d in ("raw", "interim", "processed", "figures", "tables", "cache")]
    ...     with patch.object(_m, "RAW_DIR", dirs[0]), patch.object(_m, "INTERIM_DIR", dirs[1]), patch.object(_m, "PROCESSED_DIR", dirs[2]), patch.object(_m, "FIGURES_DIR", dirs[3]), patch.object(_m, "TABLES_DIR", dirs[4]), patch.object(_m, "CACHE_DIR", dirs[5]):
    ...         ensure_project_dirs()
    ...         all(d.exists() for d in dirs)
    True
    """
    for path in [RAW_DIR, INTERIM_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR, CACHE_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to a lowercase, underscore-based style.

    >>> frame = pd.DataFrame(columns=["Stop Name", "Route-ID"])
    >>> normalize_columns(frame).columns.tolist()
    ['stop_name', 'route_id']
    >>> normalize_columns(pd.DataFrame(columns=["Already_lower"])).columns.tolist()
    ['already_lower']
    >>> normalize_columns(pd.DataFrame(columns=["  Spaces  "])).columns.tolist()
    ['spaces']
    >>> normalize_columns(pd.DataFrame()).columns.tolist()
    []
    """
    renamed = {col: col.strip().lower().replace(" ", "_").replace("-", "_") for col in df.columns}
    return df.rename(columns=renamed)


def first_existing(df: pd.DataFrame, options: list[str]) -> str:
    """Return the first column name from ``options`` that appears in ``df``.

    >>> frame = pd.DataFrame(columns=["b", "c"])
    >>> first_existing(frame, ["a", "b", "c"])
    'b'
    >>> first_existing(frame, ["c", "b"])
    'c'
    >>> first_existing(pd.DataFrame(columns=["x"]), ["x"])
    'x'
    >>> import pytest
    >>> with pytest.raises(KeyError):
    ...     first_existing(frame, ["z"])
    """
    for name in options:
        if name in df.columns:
            return name
    raise KeyError(f"None of these columns were found: {options}")


def filter_to_datetime_window(df: pd.DataFrame, date_col: str, start: str, end: str) -> pd.DataFrame:
    """Keep only rows whose datetime column falls inside the given window.

    >>> import pandas as pd
    >>> df = pd.DataFrame({"date": ["2022-01-01", "2023-06-15", "2024-12-31"], "val": [1, 2, 3]})
    >>> filter_to_datetime_window(df, "date", "2023-01-01", "2024-01-01")["val"].tolist()
    [2]
    >>> len(filter_to_datetime_window(df, "date", "2022-01-01", "2024-12-31"))
    3
    >>> len(filter_to_datetime_window(df, "date", "2025-01-01", "2025-12-31"))
    0
    >>> df2 = pd.DataFrame({"date": ["2023-03-01", "2023-03-01"], "val": [10, 20]})
    >>> filter_to_datetime_window(df2, "date", "2023-03-01", "2023-03-01")["val"].tolist()
    [10, 20]
    """
    frame = df.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    return frame.loc[frame[date_col].between(pd.Timestamp(start), pd.Timestamp(end), inclusive="both")].copy()


def read_table(path: Path) -> pd.DataFrame:
    """Read a supported tabular file based on its filename extension.

    >>> import tempfile
    >>> import pandas as pd
    >>> from pathlib import Path
    >>> df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = Path(tmp) / "test.csv"
    ...     df.to_csv(p, index=False)
    ...     read_table(p).shape
    (2, 2)
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = Path(tmp) / "test.parquet"
    ...     df.to_parquet(p, index=False)
    ...     read_table(p).shape
    (2, 2)
    >>> import pytest
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = Path(tmp) / "test.xlsx"
    ...     p.touch()
    ...     with pytest.raises(ValueError):
    ...         read_table(p)
    """
    suffix = path.suffix.lower()
    if suffix in (".csv", ".txt"):
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file type: {path}")


def _available_raw_files() -> list[str]:
    """List raw files currently present under ``data/raw``.

    >>> import tempfile
    >>> from pathlib import Path
    >>> from unittest.mock import patch
    >>> import subway_equity.io as _m
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     raw = Path(tmp)
    ...     _ = (raw / "stops.txt").write_text("data")
    ...     _ = (raw / ".gitkeep").write_text("")
    ...     with patch.object(_m, "RAW_DIR", raw):
    ...         _available_raw_files()
    ['stops.txt']
    """
    return sorted(
        str(path.relative_to(RAW_DIR))
        for path in RAW_DIR.rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    )


def _missing_raw_file_error(raw_key: str, expected_name: str) -> FileNotFoundError:
    """Build a helpful error message for a missing raw input file.

    >>> from pathlib import Path
    >>> from unittest.mock import patch
    >>> import subway_equity.io as _m
    >>> fake_files = {"stops": Path("data/raw/stops.txt")}
    >>> with patch.object(_m, "RAW_FILES", fake_files), patch.object(_m, "RAW_DIR", Path("data/raw")):
    ...     err = _missing_raw_file_error("stops", "stops.txt")
    ...     isinstance(err, FileNotFoundError)
    True
    >>> "stops" in str(err) and "stops.txt" in str(err)
    True
    """
    available = _available_raw_files()
    available_text = "\n".join(f"  - {name}" for name in available) if available else "  - none"
    return FileNotFoundError("\n".join([
        f"Missing raw input for '{raw_key}'.",
        f"Expected file: {RAW_FILES[raw_key]}",
        f"You can either place `{expected_name}` directly in `{RAW_DIR}`",
        "or put it in a subfolder under `data/raw`.",
        "For GTFS files, you can also place the original `.zip` archive in `data/raw`.",
        "Files currently found in `data/raw`:",
        available_text,
    ]))


def resolve_raw_path(raw_key: str) -> Path:
    """Resolve the expected location of a raw file, including subfolders.

    Direct file hit:

    >>> import tempfile
    >>> from pathlib import Path
    >>> from unittest.mock import patch
    >>> import subway_equity.io as _m
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     raw = Path(tmp)
    ...     f = raw / "stops.txt"
    ...     _ = f.write_text("data")
    ...     with patch.object(_m, "RAW_DIR", raw), patch.object(_m, "RAW_FILES", {"stops": f}):
    ...         resolve_raw_path("stops") == f
    True

    File found in subfolder when top-level path does not exist:

    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     raw = Path(tmp)
    ...     sub = raw / "gtfs"; sub.mkdir()
    ...     f = sub / "stops.txt"
    ...     _ = f.write_text("data")
    ...     with patch.object(_m, "RAW_DIR", raw), patch.object(_m, "RAW_FILES", {"stops": raw / "stops.txt"}):
    ...         resolve_raw_path("stops") == f
    True
    """
    expected = RAW_FILES[raw_key]
    if expected.exists():
        return expected
    matches = sorted(p for p in RAW_DIR.rglob(expected.name) if p.is_file())
    if matches:
        return matches[0]
    raise _missing_raw_file_error(raw_key, expected.name)


def read_raw_csv(raw_key: str, **kwargs) -> pd.DataFrame:
    """Read a raw CSV directly or from a ZIP archive under ``data/raw``.

    Direct file read:

    >>> import tempfile, zipfile
    >>> from pathlib import Path
    >>> from unittest.mock import patch
    >>> import pandas as pd
    >>> import subway_equity.io as _m
    >>> csv_content = "col1,col2\\n1,2\\n3,4\\n"
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     raw = Path(tmp)
    ...     f = raw / "data.csv"
    ...     _ = f.write_text(csv_content)
    ...     with patch.object(_m, "RAW_DIR", raw), patch.object(_m, "RAW_FILES", {"data": f}):
    ...         read_raw_csv("data").shape
    (2, 2)

    Read CSV from inside a ZIP archive when the bare file is absent:

    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     raw = Path(tmp)
    ...     zp = raw / "archive.zip"
    ...     with zipfile.ZipFile(zp, "w") as zf:
    ...         zf.writestr("data.csv", csv_content)
    ...     with patch.object(_m, "RAW_DIR", raw), patch.object(_m, "RAW_FILES", {"data": raw / "data.csv"}):
    ...         read_raw_csv("data").shape
    (2, 2)
    """
    expected = RAW_FILES[raw_key]
    if expected.exists():
        return pd.read_csv(expected, **kwargs)
    matches = sorted(p for p in RAW_DIR.rglob(expected.name) if p.is_file())
    if matches:
        return pd.read_csv(matches[0], **kwargs)
    for archive in sorted(p for p in RAW_DIR.rglob("*.zip") if p.is_file()):
        with ZipFile(archive) as zip_file:
            members = {Path(name).name: name for name in zip_file.namelist() if not name.endswith("/")}
            if expected.name in members:
                with zip_file.open(members[expected.name]) as handle:
                    return pd.read_csv(handle, **kwargs)
    raise _missing_raw_file_error(raw_key, expected.name)


def read_raw_geodata(raw_key: str) -> gpd.GeoDataFrame:
    """Read a raw geospatial file from the configured raw-data location.

    >>> from unittest.mock import patch
    >>> import geopandas as gpd
    >>> from pathlib import Path
    >>> import subway_equity.io as _m
    >>> mock_gdf = gpd.GeoDataFrame({"geometry": []})
    >>> with patch.object(_m, "resolve_raw_path", return_value=Path("shapes.geojson")), patch("geopandas.read_file", return_value=mock_gdf):
    ...     isinstance(read_raw_geodata("shapes"), gpd.GeoDataFrame)
    True
    """
    return gpd.read_file(resolve_raw_path(raw_key))
