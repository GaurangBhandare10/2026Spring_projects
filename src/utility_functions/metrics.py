import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def assign_income_quartiles(df: pd.DataFrame, income_col: str) -> pd.Series:
    """Assign quartile labels from lowest income to highest.

    >>> import pandas as pd
    >>> df = pd.DataFrame({"income": [10, 20, 30, 40]})
    >>> assign_income_quartiles(df, "income").astype(str).tolist()
    ['Q1', 'Q2', 'Q3', 'Q4']
    """
    return pd.qcut(df[income_col], q=4, labels=["Q1", "Q2", "Q3", "Q4"])


def compute_ridership_ratio(
    df: pd.DataFrame,
    station_col: str,
    year_col: str,
    riders_col: str,
    baseline_year: int,
) -> pd.Series:
    """Compare each station-year ridership value to that station's baseline year.

    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     "station": ["A", "A", "B", "B"],
    ...     "year": [2020, 2021, 2020, 2021],
    ...     "riders": [100, 150, 200, 100],
    ... })
    >>> compute_ridership_ratio(df, "station", "year", "riders", 2020).round(2).tolist()
    [1.0, 1.5, 1.0, 0.5]
    """
    baseline = (
        df.loc[df[year_col] == baseline_year, [station_col, riders_col]]
        .drop_duplicates(subset=[station_col])
        .rename(columns={riders_col: "baseline_ridership"})
    )
    merged = df.merge(baseline, on=station_col, how="left")
    return merged[riders_col] / merged["baseline_ridership"]


def partial_correlation(x: pd.Series, y: pd.Series, control: pd.Series) -> tuple[float, float]:
    """Compute the correlation between x and y after removing the control effect.

    >>> import pandas as pd
    >>> x = pd.Series([1, 2, 3, 4, 5])
    >>> y = pd.Series([2, 4, 6, 8, 10])
    >>> control = pd.Series([0, 1, 0, 1, 0])
    >>> float(round(partial_correlation(x, y, control)[0], 6))
    1.0
    """
    control_design = sm.add_constant(control)
    x_resid = sm.OLS(x, control_design, missing="drop").fit().resid
    y_resid = sm.OLS(y, control_design, missing="drop").fit().resid
    return stats.pearsonr(x_resid, y_resid)


def bootstrap_median_difference(
    left: pd.Series,
    right: pd.Series,
    n_boot: int = 5000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap a 95 percent interval for the difference in medians.

    >>> import pandas as pd
    >>> left = pd.Series([1, 2, 3, 4])
    >>> right = pd.Series([5, 6, 7, 8])
    >>> low, high = bootstrap_median_difference(left, right, n_boot=200, seed=1)
    >>> bool(low < high)
    True
    >>> bool(high < 0)
    True
    """
    rng = np.random.default_rng(seed)
    draws = []
    left_values = left.dropna().to_numpy()
    right_values = right.dropna().to_numpy()
    for _ in range(n_boot):
        left_sample = rng.choice(left_values, size=len(left_values), replace=True)
        right_sample = rng.choice(right_values, size=len(right_values), replace=True)
        draws.append(np.median(left_sample) - np.median(right_sample))
    return tuple(np.quantile(draws, [0.025, 0.975]))


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    """Compute a weighted average, ignoring missing values.

    >>> import pandas as pd
    >>> weighted_average(pd.Series([10, 20, 30]), pd.Series([1, 1, 2]))
    np.float64(22.5)
    """
    valid = values.notna() & weights.notna()
    if not valid.any():
        return np.nan
    return np.average(values[valid], weights=weights[valid])
