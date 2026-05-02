## 🚀 Data Processing Pipeline

This project is executed through a sequential pipeline. Each script represents a specific stage in the data lifecycle, from initial cleaning to final hypothesis testing and visualization.

### 📜 Execution Sequence

To replicate the analysis, run the scripts in the following order:

| Step | Script | Description |
| :--- | :---: | :--- |
| **1** | `01_station_crosswalk.py` | Maps subway stations to their corresponding Census tracts (geographic join). |
| **2** | `02_service_frequency.py` | Processes MTA schedule data to calculate peak-hour trip counts per station. |
| **3** | `03_ridership.py` | Cleans and aggregates historical station ridership by day type (weekday/weekend). |
| **4** | `04_delays.py` | Processes real-time delay feeds to calculate incident burdens for each line. |
| **5** | `05_census.py` | Ingests and cleans ACS Census data for neighborhood income and demographics. |
| **6** | `06_build_analysis_table.py` | **The Merge:** Joins service, ridership, and Census data into a unified master dataset. |
| **7** | `07_run_hypothesis_tests.py` | Performs the statistical modeling (regressions and T-tests) to validate H1–H4. |
| **8** | `08_visualizations.py` | Generates the final scatter plots, box plots, and time-series charts for the report. |

---

## 📈 Pipeline Workflow

The pipeline is designed to be modular.

* **Steps 1-5:** Data Ingestion & Cleaning
* **Step 6:** Data Integration
* **Steps 7-8:** Hypothesis Testing & Visualization
