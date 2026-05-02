# 🚇 NYC Subway Equity Analysis

## 1. Problem Statement  
Does New York City’s subway system provide equal service quality across neighborhoods, or do lower-income and minority-majority areas receive systematically worse service?

This project evaluates equity in public transit by linking subway service metrics with neighborhood demographic characteristics.

---

## 2. Research Question  
Do stations serving lower-income and minority-majority Census tracts experience:

- Lower service frequency?  
- Higher delay rates?  
- Slower ridership recovery post-2020?  

---

## 3. Project Type Justification (Type III)  
This is a **Type III project** because it integrates multiple independent datasets:

| Data Source | Description |
|------------|------------|
| MTA Operational Data | Ridership, delays, schedules |
| GTFS Static Feed | Station locations and scheduled service |
| U.S. Census ACS | Income and race (tract-level) |
| Census Geocoder | Maps stations → Census tracts |

**Key Contribution:**  
The project creates a **station-to-neighborhood linkage**, enabling equity analysis that cannot be performed using any single dataset.

---

## 4. Data Description  

### 4.1 Sources  
- MTA Subway Hourly Ridership (2020–2024) | https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-Beginning-February-2022/wujg-7c2s  
- MTA Delay / Service Data (2020–2024)    | https://data.ny.gov/Transportation/MTA-Subway-Service-Delivered-Beginning-2020/jue7-ix4a
- 2022 American Community Survey (ACS)    | https://data.census.gov
- MTA GTFS Static Feed                    | https://api.mta.info/#/subwayRealTimeFeeds 

### 4.2 Unit of Analysis  
- **Station-level** (primary)  
- **Line-level** (for delay aggregation)  

### 4.3 Key Variables  

| Variable | Description |
|----------|------------|
| Service Frequency | Scheduled trips per hour (peak) |
| Delay Rate | Weekly delay incidents per line |
| Ridership Ratio | Riders (year) / Riders (2020 baseline) |
| Income Quartile | Based on Census tract median income |

---

## 5. Methodology  

### 5.1 Data Integration  
- Use GTFS coordinates to identify station locations  
- Map stations to Census tracts using Census Geocoder  
- Merge datasets into a unified analysis table  

### 5.2 Feature Construction  
- Compute peak-hour service frequency from GTFS schedules  
- Aggregate delays at line level  
- Normalize ridership using 2020 baseline  

### 5.3 Analytical Approach  
- Comparative statistical analysis (non-causal)  
- Group comparisons across income quartiles  
- Control for ridership where relevant  

---

## 6. Hypotheses  

### H1: Service Frequency and Income  
Low-income stations receive fewer scheduled peak-hour trips than high-income stations, controlling for ridership.

### H2: Delay Rate and Income  
Lines serving lower-income neighborhoods have higher average weekly delay rates.

### H3: Weekday vs Weekend Ridership Gap  
Income-based ridership gaps are smaller on weekends than weekdays (2022–2024).

### H4: Shuttle Case Study  
The Rockaway Park Shuttle will exhibit:
- Higher delay rates  
- Lower ridership recovery  

Compared to the 42nd Street Shuttle.

---

## 7. Evaluation Strategy  

- Compare means across income groups  
- Conduct statistical tests (e.g., t-tests, regression where applicable)  
- Visualize distributions and trends  
- Interpret results in context of equity (not causality)  

---

## 8. Reproducibility  

### 8.1 Setup  

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 8.2 Run Pipeline  

```bash
python scripts/01_station_crosswalk.py
python scripts/02_service_frequency.py
python scripts/03_ridership.py
python scripts/04_delays.py
python scripts/05_census.py
python scripts/06_build_analysis_table.py
python scripts/07_run_hypothesis_tests.py
python scripts/08_visualization.py
```

### 8.3 Data Access  
- Data is fetched via APIs (no manual downloads required)  
- Cached locally in: `data/interim/remote_cache/`  

Optional:  
```bash
export SOCRATA_APP_TOKEN=your_token_here
```

---

## 9. Repository Structure  

```
.
├── README.md
├── requirements.txt
├── data/
├── docs/
├── notebooks/
├── results/
├── scripts/
└── src/
```

---

## 10. Results (To Be Added)  
- Figures: Service frequency, delays, ridership comparisons  
- Tables: Hypothesis test results  
- Key findings summary  

---

## 11. Limitations  

- Observational analysis (no causal inference)  
- Census tract ≠ exact subway catchment area  
- Delay data aggregated at line level, not station level  
- Potential API inconsistencies or missing data  

---

## 12. Ethical Considerations  

- Avoid overinterpreting correlations as causation  
- Ensure fair representation of communities  
- Use data responsibly in discussions of inequality  
---

## 14. Team  
- Avni Wadhwani  
- Gaurang Bhandare  
