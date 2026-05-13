# 🚇 NYC Subway Equity Analysis

## Overview

This project investigates whether New York City's subway system delivers equitable service across neighborhoods that differ by income and racial composition. We integrate four independent data sources — MTA operational records, GTFS schedules, MTA delay statistics, and U.S. Census ACS tract-level demographics — to test four targeted hypotheses about service frequency, delay burden, ridership recovery, and a shuttle-line case study.

**Bottom line:** Low-income neighborhoods do not receive systematically fewer peak-hour trips (H1 not supported), and wealthier lines are not reliably less delayed (H2 not supported). However, the weekday–weekend ridership gap is demonstrably larger in low-income stations than in high-income ones (H3 supported), and the Rockaway Park Shuttle experiences dramatically more delays than the 42nd Street Shuttle despite comparable service structures (H4 supported).

---

## Important Note
Please refer to the project documentation and README for a better understanding of the project workflow, assumptions, and analysis methodology. We have included detailed explanations to make the project easier to follow and reproduce.

---

## 1. Problem Statement

Does New York City's subway system provide equal service quality across neighborhoods, or do lower-income and minority-majority areas receive systematically worse service?

This project evaluates equity in public transit by linking subway service metrics with neighborhood demographic characteristics drawn from the American Community Survey.

---

## 2. Research Questions

Do stations serving lower-income and minority-majority Census tracts experience:

- Lower service frequency during peak commute hours?
- Higher delay rates on the lines that serve them?
- Slower ridership recovery relative to 2020 baseline levels?

---

## 3. Project Type Justification (Type III)

This is a **Type III project** because it integrates multiple independent datasets from different sources:

| Data Source | Description |
|------------|------------|
| MTA Subway Hourly Ridership | Station-level ridership by hour, 2020–2024 |
| MTA Subway Service Delivered / Delays | Monthly delay incidents per line, 2020–2024 |
| MTA GTFS Static Feed | Scheduled trips, stops, and route geometry |
| U.S. Census ACS 2022 | Tract-level median income and racial composition |
| Census Geocoder API | Converts station coordinates to Census tract GEOIDs |

**Key Contribution:** The project builds a **station-to-Census-tract crosswalk** that does not exist in any single dataset, enabling the equity comparisons at the core of all four hypotheses.

---

## 4. Data Sources

| Source | URL |
|--------|-----|
| MTA Subway Hourly Ridership (2020–2024) | https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-Beginning-February-2022/wujg-7c2s |
| MTA Subway Service Delivered (2020–2024) | https://data.ny.gov/Transportation/MTA-Subway-Service-Delivered-Beginning-2020/jue7-ix4a |
| 2022 American Community Survey (ACS 5-yr) | https://data.census.gov |
| MTA GTFS Static Feed | https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip |

---

## 5. Hypotheses and Results

### H1 — Service Frequency and Neighborhood Income

**Hypothesis:** Stations in low-income Census tracts receive fewer scheduled peak-hour trips than stations in high-income tracts, even after controlling for ridership.

**Test:** Partial correlation between tract median income and peak-hour service frequency, controlling for average daily ridership.

**Result:** Partial r = 0.039, p = 0.355 (n = 580). **Not clearly supported.** The small positive correlation suggests that if anything, higher-income areas have marginally more service, but the effect is not statistically significant. Service frequency appears to be driven primarily by ridership demand rather than neighborhood income.

---

### H2 — Delay Rate and Neighborhood Income

**Hypothesis:** Lines whose stations are predominantly in low-income tracts show a higher average weekly delay rate than lines in high-income tracts.

**Test:** Spearman correlation between ridership-weighted income score and average weekly delay incidents per line.

**Result:** Spearman ρ = 0.198, p = 0.416 (n = 19 lines). **Not clearly supported.** There is a weak positive correlation (wealthier lines slightly more delayed), but it is not statistically significant given the small number of lines and the noisiness of aggregated delay data.

---

### H3 — Weekday vs. Weekend Ridership Gap Across Income

**Hypothesis:** The ridership gap between low- and high-income station areas is smaller on weekends than on weekdays.

**Test:** Mann-Whitney U test comparing weekday-to-weekend ridership ratios between Q1 (low income) and Q4 (high income) stations.

**Result:** U = 101,416, p = 3.2 × 10⁻⁸ (n = 820), bootstrapped 95% CI for median difference: [0.087, 0.275]. **Supported.** Low-income stations have a significantly higher weekday-to-weekend ridership ratio than high-income stations, consistent with the hypothesis that lower-income commuters depend more on weekday transit while higher-income riders show more uniform usage across the week.

---

### H4 — Shuttle Delay Rate and Ridership Recovery

**Hypothesis:** The Rockaway Park S Shuttle shows a higher delay rate and lower ridership recovery than the 42nd Street S Shuttle over 2020–2024.

**Test (delays):** Two-sample Welch t-test on monthly delay counts.

**Result (delays):** t = 17.0, p = 1.8 × 10⁻²⁶ (n = 116 months combined), bootstrapped 95% CI for mean difference: [30.7, 38.6]. **Supported.** The Rockaway Park Shuttle averages roughly 34 more delay incidents per month than the 42nd Street Shuttle — a large and highly significant gap that cannot plausibly be attributed to chance.

**Result (ridership):** The ridership comparison is reported descriptively (mean difference in ridership ratio with a bootstrapped CI); no formal p-value is reported because the number of station-year observations is small.

---

## 6. Methodology Summary

1. **Station crosswalk:** GTFS stop coordinates are geocoded to Census tract GEOIDs via the Census Geocoder API.
2. **Service frequency:** Weekday peak-hour trips (7–9 am, 5–7 pm) are counted per station complex from GTFS `stop_times.txt`.
3. **Ridership:** Daily ridership is aggregated to station/year/day-type cells from the MTA Hourly Ridership Socrata API; a ridership ratio is computed using 2020 as the baseline year.
4. **Delays:** Monthly delay incident totals are fetched from the MTA Socrata API and converted to average weekly rates per line.
5. **Census demographics:** Tract-level median household income and racial composition are fetched from the Census API and used to assign income quartiles and minority-majority status.
6. **Analysis tables:** All five datasets are merged into a station-level and a line-level analysis table.
7. **Hypothesis tests:** Statistical tests are run automatically by `07_run_hypothesis_tests.py`; results are exported to `results/hypothesis_results.csv`.
8. **Visualizations:** Publication-ready PNG figures are generated by `08_visualizations.py`.

---

## 7. Limitations

- Observational analysis only — no causal inference is claimed.
- Census tract catchment areas do not perfectly match subway ridership catchments.
- Delay data is aggregated at the line level, not the station level.
- Ridership data begins in February 2022 for some stations, creating an incomplete 2020–2021 baseline for some comparisons.
- The number of distinct subway lines (n = 19) is small for a correlation analysis (H2).

---

## 8. Ethical Considerations

- Results are reported as correlations, not causal claims, to avoid overstating evidence of deliberate inequity.
- All data sources are publicly available government records.
- No individual-level data is used; the analysis is entirely at the station and Census-tract level.

---

## 9. Reproducibility

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the full pipeline

```bash
python scripts/01_station_crosswalk.py
python scripts/02_service_frequency.py
python scripts/03_ridership.py
python scripts/04_delays.py
python scripts/05_census.py
python scripts/06_build_analysis_table.py
python scripts/07_run_hypothesis_tests.py
python scripts/08_visualizations.py
```
---

#### Expected runtimes (first run vs. subsequent runs)

Every script that hits an external API caches its result locally in
`data/interim/remote_cache/`. After the first run, all scripts finish in
seconds. **First-run times depend on your internet connection** and whether
you have a Socrata app token set (see below).

| Script | What it fetches | First run | Subsequent runs |
|--------|----------------|-----------|-----------------|
| `01_station_crosswalk.py` | Census Geocoder — one HTTP call per station (~490 stations, 20 ms polite delay each) | 2 – 5 min | < 5 s |
| `02_service_frequency.py` | MTA GTFS ZIP archive (~10–50 MB) | 1 – 3 min | < 5 s |
| `03_ridership.py` | MTA Socrata ridership API — **60 aggregated monthly queries** (Jan 2020 → Dec 2024); server-side GROUP BY returns ~15 000 rows per call, so each month fits in one request | 3 – 15 min | < 10 s |
| `04_delays.py` | MTA Socrata delays dataset (single fetch) | 2 – 5 min | < 5 s |
| `05_census.py` | Census ACS API — 10 calls (5 NYC counties × income + race) | < 2 min | < 5 s |
| `06_build_analysis_table.py` | No network — merges local CSVs only | < 10 s | < 10 s |
| `07_run_hypothesis_tests.py` | No network — statistical tests + bootstrapping (n=5 000) | < 30 s | < 30 s |
| `08_visualizations.py` | No network — generates PNG figures from local tables | < 15 s | < 15 s |

> **Total first run: roughly 10 – 30 minutes** depending on Socrata server
> load and your connection speed. Scripts 06–08 are instant on every run.

---

### Run tests with coverage

```bash
pytest tests/ --cov=src/subway_equity --cov-report=term-missing
```

### Optional: set a Socrata API token to avoid rate-limiting

```bash
export SOCRATA_APP_TOKEN=your_token_here   # Windows: set SOCRATA_APP_TOKEN=your_token_here
```

Data is fetched automatically via APIs on first run and cached locally in `data/interim/remote_cache/`. Subsequent runs use the cache.

---

## 10. Repository Structure

```
.
├── README.md
├── requirements.txt
├── pytest.ini
├── data/
│   ├── cache/
│   ├── interim/
│   │   └── remote_cache/        ← API response cache (auto-populated)
│   └── processed/
│       ├── line_analysis_table.csv
│       ├── line_delay_summary.csv
│       ├── station_analysis_table.csv
│       ├── station_peak_service_frequency.csv
│       ├── station_ridership_summary.csv
│       ├── station_tract_crosswalk.csv
│       ├── tract_demographics.csv
│       └── readme.md
├── docs/
│   ├── data_dictionary.md
│   ├── methodology.md
│   ├── project_overview.md
│   ├── report_outline.md
│   └── type_iii_proposal.md
├── results/
│   ├── hypothesis_results.csv
│   ├── readme.md
│   └── figures/
│       ├── 01_h1_income_vs_peak_service.png
│       ├── 02_h2_delay_vs_income.png
│       ├── 03_h3_weekday_weekend_ratio.png
│       ├── 04_h4_shuttle_monthly_delays.png
│       └── 05_equity_overview_minority_majority_service.png
├── scripts/
│   ├── 01_station_crosswalk.py
│   ├── 02_service_frequency.py
│   ├── 03_ridership.py
│   ├── 04_delays.py
│   ├── 05_census.py
│   ├── 06_build_analysis_table.py
│   ├── 07_run_hypothesis_tests.py
│   ├── 08_visualizations.py
│   └── readme.md
├── src/
│   └── subway_equity/
│       ├── __init__.py
│       ├── config.py
│       ├── io.py
│       ├── metrics.py
│       ├── remote.py
│       └── readme.md
└── tests/
    ├── conftest.py
    ├── test_scripts.py
    └── test_subway_equity.py
```

---

## 11. Results Summary Table

| Hypothesis | Test | Statistic | p-value | n | 95% CI | Interpretation |
|------------|------|-----------|---------|---|--------|----------------|
| H1: Income → Service Frequency | Partial correlation | r = 0.039 | 0.355 | 580 stations | [−0.000, 0.074] | Not clearly supported |
| H2: Income → Delay Rate | Spearman correlation | ρ = 0.198 | 0.416 | 19 lines | [−0.284, 0.625] | Not clearly supported |
| H3: Weekday vs. Weekend Gap | Mann-Whitney U | U = 101,416 | 3.2×10⁻⁸ | 820 stations | [0.087, 0.275] | **Supported** |
| H4 (delays): Shuttle comparison | Welch t-test | t = 17.0 | 1.8×10⁻²⁶ | 116 months | [30.7, 38.6] | **Supported** |

---

## Acknowledgements

This project was developed with assistance from the following resources:

- [pandas — Reshaping and pivot tables](https://pandas.pydata.org/pandas-docs/stable/user_guide/reshaping.html) — used in `06_build_analysis_table.py` for `pivot_table` and `explode`
- [GeeksforGeeks — pandas.pivot_table()](https://www.geeksforgeeks.org/python/python-pandas-pivot_table/) — reference for reshaping ridership data from long to wide format
- [pandas — Series.between()](https://pandas.pydata.org/docs/reference/api/pandas.Series.between.html) — used in `io.py` for datetime window filtering
- [GeeksforGeeks — Working with datetime in pandas](https://www.geeksforgeeks.org/python/working-with-datetime-in-pandas-dataframe/) — reference for `pd.to_datetime` and `pd.Timestamp` in `filter_to_datetime_window`
- [U.S. Census Bureau — Data API User Guide](https://www.census.gov/data/developers/guidance/api-user-guide.html) — used in `05_census.py` for ACS income and race data queries
- [GeoPandas Documentation](https://geopandas.org/en/stable/docs.html) — used in `io.py` for reading raw geospatial station files
- [GeeksforGeeks — pandas `cut()` and `qcut()`](https://www.geeksforgeeks.org/python/how-to-use-pandas-cut-and-qcut/) — reference for `pd.qcut` used in `assign_income_quartiles`
- [Practical Business Python — Binning with qcut and cut](https://pbpython.com/pandas-qcut-cut.html) — additional reference for quartile binning of tract income
- [GeeksforGeeks — OLS using statsmodels](https://www.geeksforgeeks.org/data-science/ordinary-least-squares-ols-using-statsmodels/) — reference for `sm.OLS`, `add_constant`, and `.resid` used in `partial_correlation`
- [statsmodels — OLS example notebook](https://www.statsmodels.org/dev/examples/notebooks/generated/ols.html) — official reference for residual extraction in `partial_correlation`
- [GeeksforGeeks — Bootstrap Method](https://www.geeksforgeeks.org/maths/bootstrap-method/) — reference for the resampling loop in all four bootstrap confidence interval functions
- [GeeksforGeeks — Confidence Intervals in Python](https://www.geeksforgeeks.org/python/how-to-plot-a-confidence-interval-in-python/) — reference for `np.quantile([0.025, 0.975])` pattern used across bootstrap functions
- [ChatGPT (OpenAI)](https://chatgpt.com/share/69fc15ee-750c-83ea-91b7-1116dfabe903) — consulted for debugging and implementation guidance during development
- [ChatGPT (OpenAI)](https://chatgpt.com/share/69fd41bd-8b0c-83ea-95e5-64192048c3c3) — consulted for debugging and implementation guidance during development
- https://chatgpt.com/share/6a044433-1f60-83ea-9479-4f701b432e90 - consulted for debugging and implementation guidance during development
- [scipy — pearsonr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) — used in H1 bootstrap correlation interval
- [scipy — spearmanr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html) — used in H2 bootstrap correlation interval
- [scipy — mannwhitneyu](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html) — used for H3 weekday vs weekend ridership gap test
- [scipy — ttest_ind (Welch's t-test)](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html) — used for H4 shuttle delay comparison
- [Seaborn Documentation](https://seaborn.pydata.org/) — used throughout `08_visualizations.py` for all hypothesis figures
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/en/latest/) — used for measuring test coverage across `subway_equity/` and `scripts/`

---

## 12. Team
- Gaurang Bhandare
- Avni Wadhwani
