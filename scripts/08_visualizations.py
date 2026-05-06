"""Generate hypothesis-aligned figures for the NYC subway equity project.

The script reads the processed analysis tables, creates a small set of
publication-ready PNG figures, and saves them into ``results/figures``.
It keeps the plotting logic separate from the data-preparation steps so the
team can rerun visuals without rebuilding the full pipeline.
"""

from pathlib import Path
import sys

import matplotlib
import pandas as pd
import seaborn as sns
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from subway_equity.config import FIGURES_DIR, OUTPUT_FILES, SHUTTLE_CASE_STUDY
from subway_equity.io import ensure_project_dirs, normalize_columns, read_table


PALETTE = {
    "accent": "#0f6cbd",
    "warm": "#c9573d",
    "gold": "#d1a52b",
    "slate": "#4a5568",
    "low_income": "#bf4e30",
    "high_income": "#2f6f7e",
    "minority_yes": "#a43d2f",
    "minority_no": "#3c6e71",
}


def _format_minority_label(value: object) -> str:
    """Return a reader-friendly label for minority-majority status.

    >>> _format_minority_label(True)
    'Yes'
    >>> _format_minority_label(False)
    'No'
    """

    return "Yes" if bool(value) else "No"


def _rename_shuttle_case(value: str) -> str:
    """Return a report-friendly shuttle label.

    >>> _rename_shuttle_case("Rockaway")
    'Rockaway Park Shuttle'
    >>> _rename_shuttle_case("Times Square")
    '42nd Street Shuttle'
    """

    label_map = {
        "Rockaway": "Rockaway Park Shuttle",
        "Times Square": "42nd Street Shuttle",
    }
    return label_map.get(value, value)


def _set_plot_style() -> None:
    """Apply a consistent visual style across all exported figures."""

    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "#fbfbf8"
    plt.rcParams["axes.edgecolor"] = "#444444"
    plt.rcParams["grid.color"] = "#d9d9d9"
    plt.rcParams["grid.linewidth"] = 0.8
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"


def _load_station_year_frame() -> pd.DataFrame:
    """Return a deduplicated station-year frame for station-level visuals.

    The station analysis table contains repeated rows for weekday and weekend
    ridership summaries. For plotting, we keep one row per station-year after
    coercing numeric columns and removing invalid ACS income placeholders.
    """

    station = normalize_columns(read_table(OUTPUT_FILES["station_analysis"]))
    station["median_household_income"] = pd.to_numeric(station["median_household_income"], errors="coerce")
    station["peak_service_trips"] = pd.to_numeric(station["peak_service_trips"], errors="coerce")
    station["avg_daily_ridership"] = pd.to_numeric(station["avg_daily_ridership"], errors="coerce")
    station["weekday"] = pd.to_numeric(station["weekday"], errors="coerce")
    station["weekend"] = pd.to_numeric(station["weekend"], errors="coerce")
    station["ridership_ratio"] = pd.to_numeric(station["ridership_ratio"], errors="coerce")
    station["non_white_share"] = pd.to_numeric(station["non_white_share"], errors="coerce")
    station["year"] = pd.to_numeric(station["year"], errors="coerce")

    # Negative ACS values are placeholders for unavailable estimates, not
    # literal household incomes, so they should not appear in the figures.
    station = station.loc[station["median_household_income"] > 0].copy()
    station_year = (
        station.sort_values(["station_complex_id", "year"])
        .drop_duplicates(subset=["station_complex_id", "year"])
        .copy()
    )
    station_year["weekday_weekend_ratio"] = station_year["weekday"] / station_year["weekend"]
    return station_year


def _load_line_frame() -> pd.DataFrame:
    """Return line-level rows with valid income and delay values only."""

    line = normalize_columns(read_table(OUTPUT_FILES["line_analysis"]))
    line["ridership_weighted_income"] = pd.to_numeric(line["ridership_weighted_income"], errors="coerce")
    line["avg_weekly_delays"] = pd.to_numeric(line["avg_weekly_delays"], errors="coerce")
    return line.loc[
        (line["ridership_weighted_income"] > 0) & line["avg_weekly_delays"].notna()
    ].drop_duplicates(subset=["line_id"]).copy()


def _load_delay_frame() -> pd.DataFrame:
    """Return monthly delay rows with parsed dates for shuttle visualizations."""

    delays = normalize_columns(read_table(OUTPUT_FILES["delay_summary"]))
    delays["monthly_delays"] = pd.to_numeric(delays["monthly_delays"], errors="coerce")
    delays["month"] = pd.to_datetime(delays["month"], errors="coerce")
    return delays.dropna(subset=["line_id", "month", "monthly_delays"]).copy()


def _save_figure(fig: plt.Figure, filename: str) -> None:
    """Save a figure to the configured figure directory and close it."""

    path = FIGURES_DIR / filename
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote figure to {path}")


def _configure_external_legend(ax: plt.Axes, *, title: str) -> None:
    """Move a legend outside the plotting area to avoid label overlap."""

    legend = ax.get_legend()
    if legend is None:
        return
    legend.set_title(title)
    legend.set_bbox_to_anchor((1.02, 1))
    legend.set_loc("upper left")
    legend.get_frame().set_alpha(0.95)


def plot_h1_income_vs_service(station_year: pd.DataFrame) -> None:
    """Plot station peak service against tract income for hypothesis H1."""

    frame = station_year.dropna(
        subset=["median_household_income", "peak_service_trips", "avg_daily_ridership", "minority_majority"]
    ).copy()
    if frame.empty:
        return

    frame["minority_majority_label"] = frame["minority_majority"].map(_format_minority_label)

    fig, ax = plt.subplots(figsize=(12.5, 7))
    sns.scatterplot(
        data=frame,
        x="median_household_income",
        y="peak_service_trips",
        hue="minority_majority_label",
        size="avg_daily_ridership",
        sizes=(40, 280),
        palette={"Yes": PALETTE["minority_yes"], "No": PALETTE["minority_no"]},
        alpha=0.78,
        ax=ax,
    )
    sns.regplot(
        data=frame,
        x="median_household_income",
        y="peak_service_trips",
        scatter=False,
        ci=None,
        color=PALETTE["slate"],
        line_kws={"linewidth": 2.5, "linestyle": "--"},
        ax=ax,
    )
    corr, p_value = stats.pearsonr(frame["median_household_income"], frame["peak_service_trips"])
    ax.set_title("Station Peak Service vs. Neighborhood Income")
    ax.set_xlabel("Median household income (tract)")
    ax.set_ylabel("Scheduled peak-hour trips")
    ax.text(
        0.98,
        0.98,
        f"Exploratory Pearson r = {corr:.2f}\nP-value = {p_value:.3f}\nPoint size = avg daily ridership",
        transform=ax.transAxes,
        va="top",
        ha="right",
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "boxstyle": "round,pad=0.4"},
    )
    _configure_external_legend(ax, title="Minority-majority / Ridership")
    fig.subplots_adjust(right=0.76)
    _save_figure(fig, "h1_income_vs_peak_service.png")


def plot_h2_delay_vs_income(line: pd.DataFrame) -> None:
    """Plot line-level delay burden against ridership-weighted income for H2."""

    if line.empty:
        return

    fig, ax = plt.subplots(figsize=(10.5, 7))
    sns.regplot(
        data=line,
        x="ridership_weighted_income",
        y="avg_weekly_delays",
        scatter_kws={"s": 110, "alpha": 0.85, "color": PALETTE["accent"]},
        line_kws={"color": PALETTE["warm"], "linewidth": 2.5},
        ci=None,
        ax=ax,
    )
    for _, row in line.iterrows():
        ax.annotate(
            str(row["line_id"]),
            (row["ridership_weighted_income"], row["avg_weekly_delays"]),
            xytext=(6, 5),
            textcoords="offset points",
            fontsize=9,
            color=PALETTE["slate"],
        )
    rho, p_value = stats.spearmanr(line["ridership_weighted_income"], line["avg_weekly_delays"])
    ax.set_title("Line Delay Burden vs. Ridership-Weighted Income")
    ax.set_xlabel("Ridership-weighted neighborhood income")
    ax.set_ylabel("Average weekly delays")
    ax.text(
        0.02,
        0.98,
        f"Spearman rho = {rho:.2f}\nP-value = {p_value:.3f}\nFiltered to lines with valid income scores",
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "boxstyle": "round,pad=0.4"},
    )
    _save_figure(fig, "h2_delay_vs_income.png")


def plot_h3_weekday_weekend_ratio(station_year: pd.DataFrame) -> None:
    """Plot weekday-to-weekend ridership ratios across income quartiles for H3."""

    frame = station_year.dropna(subset=["income_quartile", "weekday_weekend_ratio"]).copy()
    frame = frame.loc[frame["income_quartile"].isin(["Q1", "Q2", "Q3", "Q4"])]
    if frame.empty:
        return

    order = ["Q1", "Q2", "Q3", "Q4"]
    fig, ax = plt.subplots(figsize=(10.5, 7))
    sns.boxplot(
        data=frame,
        x="income_quartile",
        y="weekday_weekend_ratio",
        hue="income_quartile",
        order=order,
        hue_order=order,
        palette=[PALETTE["low_income"], "#d98b5f", "#8aa4a9", PALETTE["high_income"]],
        showfliers=False,
        width=0.6,
        dodge=False,
        legend=False,
        ax=ax,
    )
    sns.stripplot(
        data=frame.sample(min(len(frame), 450), random_state=42),
        x="income_quartile",
        y="weekday_weekend_ratio",
        order=order,
        color="#1f1f1f",
        alpha=0.25,
        size=3.5,
        ax=ax,
    )
    low = frame.loc[frame["income_quartile"] == "Q1", "weekday_weekend_ratio"]
    high = frame.loc[frame["income_quartile"] == "Q4", "weekday_weekend_ratio"]
    ax.set_title("Weekday-to-Weekend Ridership Ratio by Income Quartile")
    ax.set_xlabel("Income quartile")
    ax.set_ylabel("Weekday / weekend ridership ratio")
    ax.text(
        0.02,
        0.98,
        f"Q1 median = {low.median():.2f}\nQ4 median = {high.median():.2f}\nMedian gap = {low.median() - high.median():.2f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "boxstyle": "round,pad=0.4"},
    )
    _save_figure(fig, "h3_weekday_weekend_ratio.png")


def plot_h4_shuttle_monthly_delays(delays: pd.DataFrame) -> None:
    """Plot monthly delay counts for the shuttle case-study comparison in H4."""

    shuttle_rows = []
    for shuttle_name, config in SHUTTLE_CASE_STUDY.items():
        subset = delays.loc[delays["line_id"].isin(config["delay_line_ids"])].copy()
        if subset.empty:
            continue
        subset["shuttle_case"] = shuttle_name.replace("_", " ").title()
        shuttle_rows.append(subset)

    if not shuttle_rows:
        return

    frame = pd.concat(shuttle_rows, ignore_index=True)
    frame["shuttle_case"] = frame["shuttle_case"].map(_rename_shuttle_case)

    fig, ax = plt.subplots(figsize=(12.5, 7))
    sns.lineplot(
        data=frame,
        x="month",
        y="monthly_delays",
        hue="shuttle_case",
        palette=[PALETTE["warm"], PALETTE["accent"]],
        linewidth=2.7,
        ax=ax,
    )
    ax.set_title("Monthly Delay Counts for the Shuttle Case Study")
    ax.set_xlabel("Month")
    ax.set_ylabel("Monthly delay incidents")
    legend = ax.legend(title="Shuttle", loc="upper left", bbox_to_anchor=(1.02, 1))
    legend.get_frame().set_alpha(0.95)
    rockaway_mean = frame.loc[frame["shuttle_case"] == "Rockaway Park Shuttle", "monthly_delays"].mean()
    times_mean = frame.loc[frame["shuttle_case"] == "42nd Street Shuttle", "monthly_delays"].mean()
    ax.text(
        0.98,
        0.14,
        f"Rockaway mean = {rockaway_mean:.1f}\n42nd Street mean = {times_mean:.1f}",
        transform=ax.transAxes,
        va="bottom",
        ha="right",
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "boxstyle": "round,pad=0.4"},
    )
    fig.subplots_adjust(right=0.78)
    _save_figure(fig, "h4_shuttle_monthly_delays.png")


def plot_equity_overview(station_year: pd.DataFrame) -> None:
    """Compare peak-hour service distributions by minority-majority status."""

    frame = station_year.dropna(subset=["minority_majority", "peak_service_trips"]).copy()
    if frame.empty:
        return

    frame["minority_majority_label"] = frame["minority_majority"].map(_format_minority_label)
    fig, ax = plt.subplots(figsize=(10.5, 7))
    sns.boxplot(
        data=frame,
        x="minority_majority_label",
        y="peak_service_trips",
        hue="minority_majority_label",
        order=["No", "Yes"],
        hue_order=["No", "Yes"],
        palette={"No": PALETTE["minority_no"], "Yes": PALETTE["minority_yes"]},
        showfliers=False,
        width=0.55,
        dodge=False,
        legend=False,
        ax=ax,
    )
    sns.stripplot(
        data=frame.sample(min(len(frame), 420), random_state=42),
        x="minority_majority_label",
        y="peak_service_trips",
        order=["No", "Yes"],
        color="#1f1f1f",
        alpha=0.22,
        size=3.2,
        ax=ax,
    )
    group_medians = frame.groupby("minority_majority_label")["peak_service_trips"].median()
    ax.set_title("Peak Service Distribution by Minority-Majority Status")
    ax.set_xlabel("Minority-majority tract")
    ax.set_ylabel("Scheduled peak-hour trips")
    ax.text(
        0.02,
        0.98,
        f"Median trips (No) = {group_medians.get('No', float('nan')):.1f}\n"
        f"Median trips (Yes) = {group_medians.get('Yes', float('nan')):.1f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "boxstyle": "round,pad=0.4"},
    )
    _save_figure(fig, "equity_overview_minority_majority_service.png")


def main() -> None:
    """Build and export the full visualization set for the project report."""

    ensure_project_dirs()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    _set_plot_style()

    station_year = _load_station_year_frame()
    line = _load_line_frame()
    delays = _load_delay_frame()

    plot_h1_income_vs_service(station_year)
    plot_h2_delay_vs_income(line)
    plot_h3_weekday_weekend_ratio(station_year)
    plot_h4_shuttle_monthly_delays(delays)
    plot_equity_overview(station_year)


if __name__ == "__main__":
    main()
