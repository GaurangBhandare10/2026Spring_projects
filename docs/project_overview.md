# Project Overview

## Core Question
Does subway service quality vary systematically with neighborhood income and race in New York City?

## Motivation
The MTA is one system with a single fare structure, but riders do not necessarily experience it equally. Our project tests whether stations and lines serving lower-income neighborhoods receive worse service outcomes than stations and lines serving wealthier neighborhoods.

This framing is descriptive and inferential, not causal. We test whether service quality and neighborhood demographics are associated after constructing consistent station-level and line-level measures.

## Contribution
This project combines:
- MTA ridership data
- MTA delay data
- GTFS station and schedule data
- Census tract-level income and race data

The contribution is the station-to-tract linkage. That linkage allows us to compare service outcomes to neighborhood characteristics at a much finer geographic scale than borough-level summaries.

This is the feature that makes the project Type III in the sense described by the assignment: it meaningfully links published data from different sources to answer a question neither source could answer on its own.

## Units of Analysis
- Station complex for service frequency, ridership, and tract demographics
- Subway line for line-level delay analysis
- Shuttle line case study for the 42nd Street and Rockaway Park shuttles

## Operational Definitions
- Service frequency: count of scheduled departures during weekday peak windows from GTFS.
- Delay rate: average weekly delay incidents on a subway line.
- Ridership ratio: station-year average daily ridership divided by that station's 2020 baseline.
- Minority-majority tract: tract where more than 50 percent of residents identify as non-white in ACS race counts.
- Income groups: bottom quartile and top quartile of NYC tract median household income.

## Hypotheses
### H1
Stations in low-income Census tracts receive fewer scheduled peak-hour trips than stations in high-income tracts, even after controlling for average daily ridership.

### H2
Lines with lower ridership-weighted neighborhood income scores show higher average weekly delay rates over `2020-2024`.

### H3
The ridership gap between low-income and high-income station areas is smaller on weekends than on weekdays across `2022-2024`.

### H4
The Rockaway Park shuttle will show a higher average weekly delay rate and a lower ridership ratio over `2020-2024` than the 42nd Street shuttle.

## Interpretation Guardrails
- A statistically significant relationship does not prove discrimination or causal intent.
- A null result does not prove equality of service.
- The shuttle comparison is a structured case study, not a causal experiment.

## Deliverables
- Cleaned station-to-tract crosswalk
- Station-level analysis table
- Line-level analysis table
- Hypothesis test outputs
- Figures and summary tables for the final report
