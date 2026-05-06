# Data Dictionary

## Remote Inputs

### MTA Ridership API
Endpoint:
- `https://data.ny.gov/resource/wujg-7c2s.json`

Expected fields:
- station or station complex identifier
- timestamp or date
- ridership count
- optional day type or weekday/weekend indicator

### MTA Delays API
Endpoint:
- `https://data.ny.gov/resource/jue7-ix4a.json`

Expected fields:
- line identifier
- date or week
- delay incident count

### ACS Income API
Endpoint pattern:
- `https://api.census.gov/data/2022/acs/acs5`

Expected fields:
- tract identifiers: `state`, `county`, `tract`
- `B19013_001E`

### ACS Race API
Endpoint pattern:
- `https://api.census.gov/data/2022/acs/acs5`

Expected fields:
- tract identifiers: `state`, `county`, `tract`
- `B02001_001E`
- `B02001_002E`

### Census Geocoder API
Endpoint:
- `https://geocoding.geo.census.gov/geocoder/geographies/coordinates`

Used to convert GTFS station coordinates into tract GEOIDs.

### GTFS Static Feed
Feed:
- `https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip`

Expected files inside the zip:
- `stops.txt`
- `trips.txt`
- `stop_times.txt`
- `calendar.txt`

Required GTFS columns:
- `stop_id`
- `stop_name`
- `stop_lat`
- `stop_lon`
- `parent_station`
- `trip_id`
- `route_id`
- `service_id`
- `departure_time`

## Processed Outputs

### `data/processed/station_tract_crosswalk.csv`
- `station_id`
- `station_name`
- `parent_station`
- `tract_geoid`

### `data/processed/station_peak_service_frequency.csv`
- `parent_station`
- `peak_service_trips`

### `data/processed/station_ridership_summary.csv`
- `station_complex_id`
- `year`
- `day_type`
- `avg_daily_ridership`
- `ridership_ratio`

### `data/processed/line_delay_summary.csv`
- `line_id`
- `week_start`
- `weekly_delays`
- `month`
- `monthly_delays`

### `data/processed/tract_demographics.csv`
- `tract_geoid`
- `median_household_income`
- `income_quartile`
- `minority_majority`

### `data/processed/station_analysis_table.csv`
- station-level merged analysis table for H1 and H3

### `data/processed/line_analysis_table.csv`
- line-level merged analysis table for H2 and H4
