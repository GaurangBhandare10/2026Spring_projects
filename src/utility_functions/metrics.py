"""Reusable statistical helpers for the NYC subway equity analysis."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def assign_income_quartiles(df: pd.DataFrame, income_col: str) -> pd.Series:
    """Assign quartile labels ``Q1`` through ``Q4`` based on tract income."""

    return pd.qcut(df[income_col], q=4, labels=["Q1", "Q2", "Q3", "Q4"])


def compute_ridership_ratio(
    df: pd.DataFrame,
    station_col: str,
    year_col: str,
    riders_col: str,
    baseline_year: int,
) -> pd.Series:
    """Compute station-year ridership relative to a baseline year.

    >>> frame = pd.DataFrame({
    ...     "station": ["A", "A", "A"],
    ...     "year": [2020, 2021, 2022],
    ...     "riders": [100.0, 120.0, 80.0],
    ... })
    >>> compute_ridership_ratio(frame, "station", "year", "riders", 2020).round(2).tolist()
    [1.0, 1.2, 0.8]
    """

    baseline = (
        df.loc[df[year_col] == baseline_year, [station_col, riders_col]]
        .drop_duplicates(subset=[station_col])
        .rename(columns={riders_col: "baseline_ridership"})
    )
    merged = df.merge(baseline, on=station_col, how="left")
    return merged[riders_col] / merged["baseline_ridership"]


def compute_ridership_index(
    df: pd.DataFrame,
    station_col: str,
    year_col: str,
    riders_col: str,
    baseline_year: int,
) -> pd.Series:
    """Alias for :func:`compute_ridership_ratio` retained for compatibility."""

    return compute_ridership_ratio(
        df=df,
        station_col=station_col,
        year_col=year_col,
        riders_col=riders_col,
        baseline_year=baseline_year,
    )


def partial_correlation(x: pd.Series, y: pd.Series, control: pd.Series) -> tuple[float, float]:
    """Return the Pearson correlation between residualized ``x`` and ``y``."""

    control_design = sm.add_constant(control)
    x_resid = sm.OLS(x, control_design, missing="drop").fit().resid
    y_resid = sm.OLS(y, control_design, missing="drop").fit().resid
    return stats.pearsonr(x_resid, y_resid)


def bootstrap_correlation_interval(
    x: pd.Series,
    y: pd.Series,
    *,
    method: str = "pearson",
    n_boot: int = 5000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap a 95% interval for a Pearson or Spearman correlation.

    >>> x = pd.Series([1, 2, 3, 4, 5], dtype=float)
    >>> y = pd.Series([2, 4, 6, 8, 10], dtype=float)
    >>> low, high = bootstrap_correlation_interval(x, y, n_boot=200, seed=1)
    >>> low <= 1.0 <= high
    True
    """

    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    if frame.empty:
        return (np.nan, np.nan)

    rng = np.random.default_rng(seed)
    values = frame.to_numpy()
    draws = []
    for _ in range(n_boot):
        sample = values[rng.integers(0, len(values), len(values))]
        sample_x = sample[:, 0]
        sample_y = sample[:, 1]
        if method == "pearson":
            stat = stats.pearsonr(sample_x, sample_y).statistic
        elif method == "spearman":
            stat = stats.spearmanr(sample_x, sample_y).statistic
        else:
            raise ValueError(f"Unsupported correlation method: {method}")
        draws.append(stat)
    return tuple(np.quantile(draws, [0.025, 0.975]))


def bootstrap_partial_correlation_interval(
    x: pd.Series,
    y: pd.Series,
    control: pd.Series,
    *,
    n_boot: int = 5000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap a 95% interval for a partial correlation coefficient."""

    frame = pd.DataFrame({"x": x, "y": y, "control": control}).dropna()
    if frame.empty:
        return (np.nan, np.nan)

    rng = np.random.default_rng(seed)
    values = frame.to_numpy()
    draws = []
    for _ in range(n_boot):
        sample = values[rng.integers(0, len(values), len(values))]
        sample_frame = pd.DataFrame(sample, columns=["x", "y", "control"])
        stat, _ = partial_correlation(sample_frame["x"], sample_frame["y"], sample_frame["control"])
        draws.append(stat)
    return tuple(np.quantile(draws, [0.025, 0.975]))


def bootstrap_median_difference(
    left: pd.Series,
    right: pd.Series,
    n_boot: int = 5000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap a 95% interval for the median difference ``left - right``."""

    rng = np.random.default_rng(seed)
    draws = []
    left_values = left.dropna().to_numpy()
    right_values = right.dropna().to_numpy()
    for _ in range(n_boot):
        left_sample = rng.choice(left_values, size=len(left_values), replace=True)
        right_sample = rng.choice(right_values, size=len(right_values), replace=True)
        draws.append(np.median(left_sample) - np.median(right_sample))
    return tuple(np.quantile(draws, [0.025, 0.975]))


def bootstrap_mean_difference(
    left: pd.Series,
    right: pd.Series,
    n_boot: int = 5000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap a 95% interval for the mean difference ``left - right``.

    >>> left = pd.Series([4.0, 5.0, 6.0])
    >>> right = pd.Series([1.0, 2.0, 3.0])
    >>> low, high = bootstrap_mean_difference(left, right, n_boot=200, seed=1)
    >>> low > 0 and high > 0
    True
    """

    rng = np.random.default_rng(seed)
    draws = []
    left_values = left.dropna().to_numpy()
    right_values = right.dropna().to_numpy()
    if len(left_values) == 0 or len(right_values) == 0:
        return (np.nan, np.nan)
    for _ in range(n_boot):
        left_sample = rng.choice(left_values, size=len(left_values), replace=True)
        right_sample = rng.choice(right_values, size=len(right_values), replace=True)
        draws.append(left_sample.mean() - right_sample.mean())
    return tuple(np.quantile(draws, [0.025, 0.975]))


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    """Return a weighted average while safely ignoring missing values.

    >>> weighted_average(pd.Series([1.0, 3.0]), pd.Series([1.0, 3.0]))
    2.5
    """

    valid = values.notna() & weights.notna()
    if not valid.any():
        return np.nan
    return np.average(values[valid], weights=weights[valid])
