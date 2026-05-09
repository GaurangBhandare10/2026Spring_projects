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

## 12. Team
- Gaurang Bhandare
- Avni Wadhwani
