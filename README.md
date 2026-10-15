# NYC Taxi Mobility Data Explorer

A full-stack application that cleans the NYC Yellow Taxi trip data (January 2019), stores it in a normalized
SQLite database, serves it through a Flask API, and shows it on a web dashboard.

•⁠  ⁠*Video walkthrough:* <<VIDEO LINK HERE>>
•⁠  ⁠*GitHub repository:* <<https://github.com/malaika-11/nyc-taxi-mobility-dashboard.git>>
.  *Team Task Sheet:* <<https://docs.google.com/spreadsheets/d/1TfQLnFrukclGGabRTPRnTWjI8un_2a0tNHR69zOttl0/edit?usp=sharing>>

## 1. What the system does

| Layer | What it does | Main files |
|---|---|---|
| Data processing | Reads the raw trip file in chunks, checks every row, removes bad rows, adds derived features, links trips to zones | ⁠ database/build_db.py ⁠ |
| Database | Normalized SQLite database with indexes, a log of removed rows and summary tables | ⁠ database/schema.sql ⁠, ⁠ database/summary_tables.sql ⁠ |
| Backend | Flask API that reads the database and returns JSON | ⁠ backend/app.py ⁠ |
| Frontend | HTML, CSS and JavaScript dashboard, served by Flask | ⁠ frontend/ ⁠ |


 yellow_tripdata + taxi_zone_lookup + taxi_zones
                     |
                     v
          build_db.py (clean, validate, add features)
                     |
                     v
     taxi.db (SQLite)  <--  summary_tables.sql
                     |
                     v
          Flask API (backend/app.py)
                     |
                     v
      Dashboard (frontend/, opened at http://127.0.0.1:5000)


## 2. Requirements

•⁠  ⁠Python 3.9 or newer
•⁠  ⁠⁠ pip ⁠
•⁠  ⁠The ⁠ sqlite3 ⁠ command line tool.

## 3. Setup

Clone the repository and go into it:


git clone <<REPO LINK>>
cd nyc-taxi-mobility-dashboard


Create and activate a virtual environment.

macOS / Linux:

python3 -m venv .venv
source .venv/bin/activate


Windows:

python -m venv .venv
.venv\Scripts\Activate.ps1


Install the packages:

pip install -r requirements.txt


## 4. Get the data

The data files are not stored in the repository because the trip file is too large for GitHub.
Download these three components (linked on the assignment page; trip data is also on the
[TLC trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)) and put them in the
⁠ database/ ⁠ folder:

| File | Notes |
|---|---|
| ⁠ yellow_tripdata_2019-01.csv ⁠ | Fact table. |
| ⁠ taxi_zone_lookup.csv ⁠ | Zone names, boroughs and service zones (dimension table). |
| ⁠ taxi_zones.shp ⁠ with ⁠ taxi_zones.shx ⁠, ⁠ taxi_zones.dbf ⁠, ⁠ taxi_zones.prj ⁠ | Zone boundaries. These four files must stay together. |

## 5. Build the database

Run these commands from the ⁠ database/ ⁠ folder, with the virtual environment active. Run them in this order.


cd database


*Step 1: create the tables and load the zones (a few seconds, prints nothing when it works)*

python build_db.py --init --lookup taxi_zone_lookup.csv --shp taxi_zones.shp --db taxi.db


*Step 2: load and clean the trips (several minutes; prints one line per chunk)*

python build_db.py --trips yellow_tripdata_2019-01.csv --db taxi.db --start 2019-01-01 --end 2019-02-01

Each line looks like ⁠ loaded 190000 trips, excluded 9000 , flagged 1200 ⁠. The prompt returns when it has finished.

*Step 3: build the summary tables used by the dashboard*

sqlite3 taxi.db < summary_tables.sql

Without the ⁠ sqlite3 ⁠ tool (for example on Windows):

python -c "import sqlite3; c=sqlite3.connect('taxi.db'); c.executescript(open('summary_tables.sql').read()); c.close()"


Notes:
•⁠  ⁠Run Step 2 only once per database. To start again, delete ⁠ taxi.db ⁠ and repeat from Step 1.
•⁠  ⁠Run Step 3 again after every rebuild of ⁠ taxi.db ⁠.
•⁠  ⁠Put quotes around any file name that has spaces or brackets.

*Check that it worked* (the two counts in the first line must match):

sqlite3 taxi.db "select 'trip', count(*) from trip union all select 'trip_fare', count(*) from trip_fare union all select 'excluded', count(*) from excluded_record union all select 'suspicious', count(*) from suspicious_record;"

Result of our final build: <<FILL IN: trip, trip_fare, excluded and suspicious counts>>.

## 6. Run the application

From the repository root (the folder that contains ⁠ backend/ ⁠ and ⁠ frontend/ ⁠):

python backend/app.py

Open *http://127.0.0.1:5000* in a browser. Flask serves the dashboard from ⁠ frontend/ ⁠ and the API from ⁠ /api/... ⁠, so
there is only one program to start. Check that the API sees the database at http://127.0.0.1:5000/api/health: it should show
⁠ "database_exists": true ⁠.

The backend looks for ⁠ taxi.db ⁠ in ⁠ outputs/ ⁠ and then in ⁠ database/ ⁠.

The first request to each endpoint can take a few seconds on the full database; answers are remembered afterwards.

### API endpoints

| Endpoint | Returns |
|---|---|
| ⁠ /api/health ⁠ | Status and which database file is used |
| ⁠ /api/hourly-demand ⁠ | Pickups for each hour of the day (24 rows) |
| ⁠ /api/weekday-demand ⁠ | Pickups for each day of the week, Monday to Sunday |
| ⁠ /api/weekday-average ⁠ | Total pickups, number of such days and average pickups per day for each weekday |
| ⁠ /api/weekday-weekend-demand ⁠ | Pickups on weekdays and weekends |
| ⁠ /api/daily-demand ⁠ | Pickups for each date in January 2019 |
| ⁠ /api/summary ⁠ | Total pickups, busiest and quietest hour and weekday |

<<ADD A ROW FOR EACH NEW ENDPOINT (filters, zones, map, trips) THE TEAM ADDS>>

Example:

curl http://127.0.0.1:5000/api/summary


## 7. Run the tests

From the repository root, with the database built:

python -m unittest teststest_demand_api

The tests check the health endpoint, the home page, and the demand endpoints.

## 8. Data cleaning

⁠ build_db.py ⁠ checks every row. A row that fails a rule is not loaded; it is written to the table ⁠ excluded_record ⁠
with its row number in the source file and the first rule it broke.

| Reason code | Rule |
|---|---|
| ⁠ MISSING_VALUE ⁠ | A core field (times, zones, distance, fare, total) is empty |
| ⁠ OUTSIDE_DATE_RANGE ⁠ | Pickup is outside the ⁠ --start ⁠ / ⁠ --end ⁠ dates (the file contains stray December and February dates) |
| ⁠ DROPOFF_NOT_AFTER_PICKUP ⁠ | Dropoff time is not after pickup time |
| ⁠ TRIP_OVER_24_HOURS ⁠ | Trip lasted more than 24 hours |
| ⁠ ZERO_OR_NEGATIVE_DISTANCE ⁠ | Distance is 0 or negative |
| ⁠ IMPOSSIBLE_SPEED ⁠ | Average speed over 100 mph |
| ⁠ NEGATIVE_AMOUNT ⁠ | Negative fare, total or tip |
| ⁠ BAD_LOCATION_ID ⁠ | Zone ID outside 1 to 265 |
| ⁠ UNKNOWN_VENDOR ⁠, ⁠ UNKNOWN_PAYMENT_TYPE ⁠, ⁠ UNKNOWN_RATE_CODE ⁠ | Code not in the TLC data dictionary |
| ⁠ DISTANCE_OVER_LIMIT ⁠ | Distance over 100 miles |
| ⁠ FARE_OVER_LIMIT ⁠ | Fare over $500 |
| ⁠ DUPLICATE_ROW ⁠ | Same vendor, pickup, dropoff, zones, distance and total as an earlier trip |

The limits are set at the top of ⁠ build_db.py ⁠ (⁠ MAX_DISTANCE_MILES ⁠, ⁠ MAX_FARE_DOLLARS ⁠, ⁠ MAX_SPEED_MPH ⁠).

Rows that look odd but are kept go to ⁠ suspicious_record ⁠: ⁠ ODD_PASSENGER_COUNT ⁠ (0 or more than 6),
⁠ FAST_TRIP ⁠ (over 70 mph) and ⁠ TOTAL_BELOW_FARE ⁠.

Counts per reason, for the report:

sqlite3 taxi.db "select reason_code, count(*) from excluded_record group by 1 order by 2 desc;"
sqlite3 taxi.db "select reason_code, count(*) from suspicious_record group by 1 order by 2 desc;"


### Derived features

| Feature | Formula | Why it is useful |
|---|---|---|
| ⁠ duration_min ⁠ | dropoff minus pickup, in minutes | Trip time and congestion |
| ⁠ avg_speed_mph ⁠ | distance divided by hours | Traffic by hour and zone; also catches impossible trips |
| ⁠ fare_per_mile ⁠ | fare divided by distance | Pricing efficiency across zones |
| ⁠ tip_pct ⁠ | tip divided by fare times 100 (card payments only) | Tipping behaviour; cash tips are not recorded |
| ⁠ pickup_hour ⁠ | hour of the pickup time | Demand by hour |
| ⁠ pickup_dow ⁠ | day of week of the pickup (0 = Monday) | Weekly demand patterns |

Timestamps are stored as ⁠ YYYY-MM-DD HH:MM:SS ⁠ text, codes are stored as integer keys to lookup tables, and the
zone shapes are converted from the shapefile's coordinate system (EPSG:2263, feet) to latitude and longitude (EPSG:4326)
so a web map can draw them.

## 9. Database design

The schema is in ⁠ database/schema.sql ⁠ (the schema file deliverable). SQLite was chosen because the whole database is one
file that every team member can copy, with no server to install.

•⁠  ⁠*Lookup tables:* ⁠ borough ⁠, ⁠ service_zone ⁠, ⁠ zone ⁠, ⁠ vendor ⁠, ⁠ rate_code ⁠, ⁠ payment_type ⁠. Each name is stored once.
•⁠  ⁠*Map shapes:* ⁠ zone_geometry ⁠ holds one GeoJSON polygon per row, kept apart from ⁠ zone ⁠ because it is large.
•⁠  ⁠*Trips:* ⁠ trip ⁠ (movement data and derived features) and ⁠ trip_fare ⁠ (money data), one row each per trip.
•⁠  ⁠*Logs:* ⁠ excluded_record ⁠ and ⁠ suspicious_record ⁠.
•⁠  ⁠*View:* ⁠ v_trip_full ⁠ joins trips with zone, borough, and payment names.
•⁠  ⁠*Indexes:* pickup time, pickup zone, dropoff zone, day and hour together, distance, payment type, total fare.
•⁠  ⁠*Constraints:* distance and duration above 0, fares and tips not negative, all codes must exist in their lookup tables.
•⁠  ⁠*Summary tables* (built by ⁠ summary_tables.sql ⁠): ⁠ hourly_demand ⁠, ⁠ weekday_demand ⁠, ⁠ daily_demand ⁠, ⁠ weekday_average ⁠,
  ⁠ period_demand ⁠. They are derived from ⁠ trip ⁠ and make the dashboard fast. The backend falls back to calculating the
  same answer from ⁠ trip ⁠ if a summary table is missing.

To create a schema dump:

sqlite3 taxi.db ".schema" > schema_dump.sql


## 10. Algorithm written by hand



## 11. Project structure

nyc-taxi-mobility-dashboard/
├── backend/
│   └── app.py
├── frontend/
│   └── index.html            (plus its CSS and JavaScript files)
├── database/
│   ├── build_db.py
│   ├── schema.sql
│   ├── summary_tables.sql
│   └── data
├── scripts/                  (analysis helpers)
├── tests/
│   └── test_demand_api.py
├── requirements.txt
└── README.md


## 12. Troubleshooting

| Problem | Fix |
|---|---|
| ⁠ zsh: no matches found: ...(1).csv ⁠ | Put the file name in quotes |
| ⁠ no such table: trip ⁠ | Step 1 did not run, or you are in the wrong folder. Delete ⁠ taxi.db ⁠ and repeat Steps 1 and 2 |
| ⁠ FileNotFoundError ⁠ for ⁠ schema.sql ⁠ | Run ⁠ build_db.py ⁠ from the ⁠ database/ ⁠ folder |
| ⁠ ModuleNotFoundError: flask ⁠ (or pandas, pyproj, shapefile) | Activate the virtual environment and run the ⁠ pip install ⁠ line from Section 3 |
| API returns ⁠ Database not found ⁠ | Put ⁠ taxi.db ⁠ in ⁠ database/ ⁠ or ⁠ outputs/ ⁠ |
| API returns ⁠ Database problem: no such table ⁠ | Run Step 3 (summary tables) or rebuild ⁠ taxi.db ⁠ |
| Port 5000 already in use | Stop the other program using it, or change ⁠ port=5000 ⁠ at the bottom of ⁠ backend/app.py ⁠ |
| Trips loaded twice | Delete ⁠ taxi.db ⁠ and start again from Step 1 |

## 13. Limitations and next steps

•⁠  ⁠The data covers January 2019 only.
•⁠  ⁠Pickup counts show recorded trips, not unmet demand.
•⁠  ⁠Possible next steps: more months, PostgreSQL for several users at once, and deployment.
