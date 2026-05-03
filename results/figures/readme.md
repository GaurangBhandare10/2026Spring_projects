# 📊 Visualization Gallery & Interpretation

This directory contains the visual evidence for the NYC Subway Equity Analysis. These charts turn complex statistical models into intuitive narratives regarding transit access and reliability.

## 📈 Summary of Key Figures

### 1. Station Peak Service vs. Neighborhood Income
**File:** `h1_income_vs_peak_service.png`
* **What it shows:** A scatter plot comparing neighborhood median household income (X-axis) against the number of scheduled peak-hour trips (Y-axis).
* **Key Legend:** * **Colors:** Brown = Minority-Majority tracts; Teal = Non-Minority-Majority.
    * **Size:** Average daily ridership.
* **Takeaway:** A positive trend line indicates that wealthier neighborhoods generally receive higher service frequency, supporting **H1**.

### 2. Line Delay Burden vs. Ridership-Weighted Income
**File:** `h2_delay_vs_income.png`
* **What it shows:** A line-level analysis comparing a subway line's delay frequency against the weighted income of its ridership.
* **Takeaway:** The downward-sloping regression line suggests that lines serving lower-income populations experience a higher "delay burden," supporting **H2**.

### 3. Weekday-to-Weekend Ridership Ratio
**File:** `h3_weekday_weekend_ratio.png`
* **What it shows:** Box plots comparing the ratio of weekday to weekend ridership across four income quartiles (Q1 = Lowest, Q4 = Highest).
* **Takeaway:** Lower-income neighborhoods (Q1) show a significantly higher weekday-to-weekend ratio (Median: 1.87), indicating a higher dependency on the subway for weekday work commutes (**H3**).

### 4. Shuttle Case Study: Rockaway vs. 42nd Street
**File:** `h4_shuttle_monthly_delays.png`
* **What it shows:** A longitudinal time-series (2020–2024) comparing monthly delay incidents for two shuttle services.
* **Takeaway:** The Rockaway Park Shuttle (serving lower-income/minority areas) consistently records significantly higher delays (Mean: 43.0) than the 42nd Street Shuttle (Mean: 8.5), providing a "smoking gun" for geographic inequity (**H4**).

### 5. Peak Service Distribution by Minority Status
**File:** `equity_overview_minority_majority_service.png`
* **What it shows:** A distribution analysis of peak trips segmented by Minority-Majority tract status.
* **Takeaway:** Minority-majority tracts have a much lower median service frequency (87.5 trips) compared to non-minority-majority tracts (132.0 trips), reinforcing the racial equity dimension of the study.

---
