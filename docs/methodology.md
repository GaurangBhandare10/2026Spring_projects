# Methodology

## Data Integration
We merge four components:

1. GTFS stops with Census geocoder lookups to assign each station complex to a Census tract.
2. GTFS schedules to estimate weekday peak-hour service frequency by station complex.
3. MTA ridership data to create station-level ridership averages and a 2020-based ridership ratio.
4. ACS income and race tables to define tract median income, income quartiles, and minority-majority status.

## Variable Construction
### Station-Level Variables
- `station_complex_id`
- `tract_geoid`
- `median_household_income`
- `income_quartile`
- `minority_majority`
- `peak_service_trips`
- `avg_daily_ridership`
- `weekday_avg_ridership`
- `weekend_avg_ridership`
- `ridership_ratio`

### Line-Level Variables
- `line_id`
- `avg_weekly_delays`
- `ridership_weighted_income`
- `share_low_income_stations`

## Statistical Plan
### H1: Service Frequency and Income
Test: partial correlation between tract median income and peak-hour service frequency while controlling for average daily ridership.

Implementation:
- Regress income on ridership.
- Regress service frequency on ridership.
- Correlate the residuals.

Why this works:
It isolates the association between income and scheduled service after removing the part explained by ridership volume.

### H2: Delay Rate and Income
Test: Spearman correlation between line-level ridership-weighted income and average weekly delay incidents.

Why Spearman:
It is more robust than Pearson when monotonic relationships may exist without strict linearity.

### H3: Weekday vs Weekend Ridership Gap
Test: Mann-Whitney U test comparing station-level weekday-to-weekend ridership ratios for low-income versus high-income areas, plus a bootstrapped 95 percent confidence interval for the difference in medians.

### H4: Shuttle Case Study
Test 1: two-sample t-test comparing monthly delay counts between the Rockaway Park shuttle and the 42nd Street shuttle.

Test 2: descriptive comparison of annual ridership ratio values with 95 percent confidence intervals.

## Limitations
- Station geography is assigned using the Census tract returned for the station coordinate, not the full rider catchment area.
- Delay data may be line-level rather than station-specific.
- Service frequency from GTFS is scheduled service, not necessarily delivered service.
- The ridership ratio uses 2020 as the within-period baseline, so it compares each station-year to that same station's 2020 level rather than to a pre-pandemic 2019 value.

## Recommended Figures
1. Map of stations colored by tract income quartile
2. Scatterplot of income versus peak service frequency
3. Scatterplot of line income score versus average weekly delay rate
4. Boxplot of weekday-to-weekend ridership ratio by income group
5. Shuttle comparison chart for monthly delays and annual ridership ratio
