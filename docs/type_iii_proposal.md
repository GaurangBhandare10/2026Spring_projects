# Type III Proposal Alignment

## Proposed Title
Does NYC's Subway System Serve All Neighborhoods Equally? Linking MTA Service Quality to Census Demographics

## Problem That Motivates the Project
Public transit is supposed to be a shared public good, but riders may not experience it equally. In New York City, the subway has one operator and one fare system, yet neighborhoods differ sharply in income, race, and dependence on transit. That raises a public-interest question: do lower-income and minority-majority neighborhoods receive worse service outcomes than wealthier neighborhoods?

This question came first. The data sources were chosen afterward to test it.

## Why The Project Is Original
This is not a one-dataset project. It combines published data from different sources and links them in a way that allows a new analysis.

The project joins:

1. MTA operational data on ridership and delays
2. MTA GTFS schedule and stop-location data
3. U.S. Census ACS tract-level income and race data
4. NYC tract boundary geometry for the spatial join

None of these sources alone can answer the research question. The originality comes from building a station-to-tract linkage and then testing whether service quality varies with neighborhood demographics.

## Two Different Sources Requirement
The assignment requires linking datasets from different published sources. This project satisfies that requirement clearly:

- MTA data is one source family, describing transit operations.
- U.S. Census ACS is a different source family, describing neighborhood demographics.

The analysis depends on combining them. Without Census data, we cannot classify neighborhoods by income or race. Without MTA data, we cannot measure service frequency, delays, or ridership patterns over time.

## Hypotheses
### H1: Service Frequency and Neighborhood Income
Stations in low-income Census tracts receive fewer scheduled peak-hour trips than stations in high-income tracts, even after controlling for average daily ridership.

### H2: Delay Rate and Neighborhood Income
Lines with lower ridership-weighted neighborhood income scores show higher average weekly delay rates over `2020-2024`.

### H3: Weekday vs. Weekend Ridership Gap Across Income
The ridership gap between low-income and high-income station areas is smaller on weekends than on weekdays across `2022-2024`.

### H4: Shuttle Delay Rate and Ridership Ratio
The Rockaway Park shuttle will show a higher average weekly delay rate and a lower ridership ratio over `2020-2024` than the 42nd Street shuttle.

## Definitions
- Service frequency: scheduled subway trips per hour at a station complex, measured from GTFS static schedules.
- Delay rate: delay incidents per week on a subway line.
- Ridership ratio: average daily riders at a station in a given year divided by average daily riders at that same station in 2020.
- Low-income station: a station whose Census tract falls in the bottom quartile of NYC tract median household income.
- High-income station: a station whose Census tract falls in the top quartile.
- Peak hours: weekdays from `7:00-9:00 AM` and `5:00-7:00 PM`.

## Data Sources
1. MTA Subway Hourly Ridership
2. MTA Subway Delays / Service Delivered
3. MTA GTFS static feed
4. 2022 ACS tract-level income and race tables
5. NYC Census tract shapefiles or GeoJSON

## Planned Method
1. Map each subway station complex to the Census tract it falls in.
2. Use ACS data to assign income and demographic characteristics to that tract.
3. Use GTFS schedules to compute peak-hour service frequency.
4. Use MTA ridership data to compute station-level average riders and 2020-based ridership ratios.
5. Use MTA delay data to compute line-level delay measures.
6. Test the four hypotheses using the planned non-causal statistical methods.

## Why The Question Matters
If lower-income neighborhoods depend more heavily on transit but receive worse service outcomes, that is an important equity issue in a major public system. The project is relevant to transportation policy, urban inequality, and public accountability.

## Limits And Cautions
- The project tests associations, not causation.
- Stations are linked to the tract they sit in, which may not fully represent all riders' origins.
- GTFS measures scheduled service, not necessarily delivered service.
- Delay data may be available at the line level rather than the station level.

## Short Submission Version
This project meets the Type III requirement because it links multiple published datasets from different sources to answer an original question. We combine MTA ridership, delay, and schedule data with Census tract-level income and race data, using a spatial join between subway stations and Census tracts. The resulting linked dataset lets us test whether lower-income neighborhoods receive worse subway service outcomes than wealthier neighborhoods, which cannot be determined from any one dataset alone.
