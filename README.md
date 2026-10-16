# NYC Taxi Mobility Data Explorer

A full-stack dashboard for exploring New York City yellow taxi trips (January 2019). Raw TLC data is cleaned and enriched with Python, stored in a normalized SQLite database, served through a Flask API, and explored in a browser dashboard with filters, sorting, charts and trip detail views.

| | |
|---|---|
| **Video walkthrough** | `<PASTE VIDEO LINK HERE>` |
| **GitHub repository** | https://github.com/malaika-11/nyc-taxi-mobility-dashboard |
| **Team participation sheet** | https://docs.google.com/spreadsheets/d/1TfQLnFrukclGGabRTPRnTWjI8un_2a0tNHR69zOttl0/edit?usp=sharing |
| **Technical report (PDF)** | [`docs/SME_Inc_Technical_Report.pdf`](docs/SME_Inc_Technical_Report.pdf) |

---

## Contents

1. [Architecture](#1-architecture)
2. [Requirements](#2-requirements)
3. [Quick start](#3-quick-start)
4. [Building the database in detail](#4-building-the-database-in-detail)
5. [API reference](#5-api-reference)
6. [Data cleaning](#6-data-cleaning)
7. [Database design](#7-database-design)
8. [Hand-written algorithm](#8-hand-written-algorithm)
9. [Tests](#9-tests)
10. [Project structure](#10-project-structure)
11. [Troubleshooting](#11-troubleshooting)
12. [Limitations and next steps](#12-limitations-and-next-steps)

---

## 1. Architecture

```
 yellow_tripdata + taxi_zone_lookup + taxi_zones
                      |
                      v
        database/build_db.py   (clean, validate, add features, log rejects)
                      |
                      v
            database/taxi.db   (SQLite)  <--  summary_tables.sql
                      |
                      v
          backend/app.py       (Flask JSON API + serves the frontend)
                      |
                      v
   frontend/  (HTML + CSS + JavaScript + Chart.js)  ->  http://127.0.0.1:5000
```

Flask serves both the API (`/api/...`) and the dashboard (`/`), so there is **one program to start** and no cross-origin setup.

| Layer | Responsibility | Main files |
|---|---|---|
| Data processing | Read trips in chunks, validate each row, drop bad rows, compute derived features, link trips to zones | `database/build_db.py` |
| Database | Normalized schema, indexes, rejected-row logs, pre-aggregated summary tables | `database/schema.sql`, `database/summary_tables.sql` |
| Backend | JSON API for summaries, charts, filtered and paginated trips | `backend/app.py` |
| Frontend | Summary cards, charts, zone map with top-K ranking, filters, sortable trip table, detail panel | `frontend/` |

---

## 2. Requirements

- Python 3.9 or newer, with `pip`
- A modern browser (the dashboard loads Chart.js from a CDN, so it needs an internet connection)
- The `sqlite3` command-line tool (optional, there is a Python alternative below)

---

## 3. Quick start

Run everything from the **project root** unless a step says otherwise.

### Step 1: Clone and create a virtual environment

```bash
git clone https://github.com/malaika-11/nyc-taxi-mobility-dashboard.git
cd nyc-taxi-mobility-dashboard
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### Step 2: Download the trip data

The trip file is too large for GitHub, so download it and place it in `data/raw/`:

- **File:** Yellow Taxi trip records for **January 2019** (`yellow_tripdata_2019-01.csv` or `.parquet`)
- **Source:** the assignment page, or the [TLC trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)

The other two inputs are already in the repository:

| File | Location |
|---|---|
| Zone lookup (dimension table) | `database/taxi_zone_lookup.csv` |
| Zone boundaries (spatial metadata) | `data/raw/taxi_zones.zip` |

### Step 3: Build the database

Run these **from the `database/` folder**, in this order. Use the file name you downloaded in Step 2 (`.csv` or `.parquet`).

```bash
cd database

# 3a. Create tables and load the zones (a few seconds)
python build_db.py --init --lookup taxi_zone_lookup.csv --shp ../data/raw/taxi_zones.zip --db taxi.db

# 3b. Load and clean the trips (several minutes, prints one line per chunk)
python build_db.py --trips ../data/raw/yellow_tripdata_2019-01.csv --db taxi.db --start 2019-01-01 --end 2019-02-01

# 3c. Build summary tables used by the dashboard
sqlite3 taxi.db < summary_tables.sql

cd ..
```

No `sqlite3` tool (for example on Windows)? Replace 3c with:
```bash
python -c "import sqlite3; c=sqlite3.connect('taxi.db'); c.executescript(open('summary_tables.sql').read()); c.close()"
```

Wait for 3b to finish (the prompt returns) before running 3c. Each progress line looks like `loaded 190000 trips, excluded 9000, flagged 1200`.

**Check it worked.** From `database/`:
```bash
sqlite3 taxi.db "select count(*) from trip;"
```
The count should be about **7.5 million** (our build: 7,524,370 trips).

### Step 4: Start the app

From the project root:
```bash
python backend/app.py
```

Open **http://127.0.0.1:5000**. To confirm the backend can see the database, open http://127.0.0.1:5000/api/health, which should show `"database_exists": true`.

> The first request to each endpoint can take a few seconds on the full database. Results are cached afterwards.

---

## 4. Building the database in detail

- Run `build_db.py` **from inside `database/`**. Running it from the project root gives `can't open file 'build_db.py'`.
- Step 3b refuses to run on a database that already contains trips, which prevents double loading. To start over, delete the file and repeat from 3a:
  ```bash
  cd database
  rm taxi.db
  ```
- Re-run 3c after every rebuild.
- Put quotes around any file name that contains spaces or brackets.
- `--start` and `--end` define the kept pickup window (end is exclusive). The raw file contains stray December 2018 and February 2019 timestamps, which are excluded.
- `build_db.py` accepts either `.csv` (read in chunks of 200,000 rows) or `.parquet`.
- To use a different database location, set the `TAXI_DB` environment variable before starting Flask:
  ```bash
  TAXI_DB=/path/to/taxi.db python backend/app.py
  ```

---

## 5. API reference

All endpoints return JSON.

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Status and database file in use |
| `GET /api/summary` | Total trips, busiest/quietest hour and weekday, average distance and fare |
| `GET /api/hourly-demand` | Pickups for each hour of the day (24 rows) |
| `GET /api/weekday-demand` | Pickups for each weekday, Monday to Sunday |
| `GET /api/weekday-average` | Total pickups, number of such days and average pickups per day, per weekday |
| `GET /api/weekday-weekend-demand` | Pickups on weekdays vs weekends |
| `GET /api/daily-demand` | Pickups for each date |
| `GET /api/boroughs` | Borough names for the filter dropdowns |
| `GET /api/zone-demand` | GeoJSON zones with pickup count, drop-off count and average fare (feeds the map) |
| `GET /api/zones/top` | Top-K zones for `metric` = `pickup_count`, `dropoff_count` or `avg_fare` (`k` 1 to 50), ranked with the hand-written heap |
| `GET /api/trips` | Filtered, sorted, paginated trips (see below) |
| `GET /api/trips/<trip_id>` | Full details of one trip, or 404 |

### `/api/trips` query parameters

| Parameter | Meaning | Default |
|---|---|---|
| `start_date`, `end_date` | Pickup date range (`YYYY-MM-DD`) | none |
| `min_distance`, `max_distance` | Trip distance in miles | none |
| `min_fare`, `max_fare` | Metered fare in dollars | none |
| `pickup_borough`, `dropoff_borough` | Exact borough name | none |
| `sort_by` | `date`, `distance`, `fare` or `duration` | `date` |
| `sort_order` | `asc` or `desc` | `desc` |
| `page`, `limit` | Pagination (`limit` 1 to 100) | `1`, `50` |

Example:
```bash
curl "http://127.0.0.1:5000/api/trips?pickup_borough=Manhattan&min_distance=5&sort_by=fare&limit=10"
```

Sorting columns are checked against an allow-list and every filter value is passed as a bound SQL parameter, so the endpoint is not open to SQL injection.

---

## 6. Data cleaning

`build_db.py` checks every row. A row that breaks a rule is **not loaded**. It is written to `excluded_record` with its source row number and the first rule it broke.

| Reason code | Rule |
|---|---|
| `MISSING_VALUE` | A core field (times, zones, distance, fare, total) is empty |
| `OUTSIDE_DATE_RANGE` | Pickup is outside `--start` / `--end` |
| `DROPOFF_NOT_AFTER_PICKUP` | Dropoff is not after pickup |
| `TRIP_OVER_24_HOURS` | Trip lasted more than 24 hours |
| `ZERO_OR_NEGATIVE_DISTANCE` | Distance is 0 or negative |
| `IMPOSSIBLE_SPEED` | Average speed over 100 mph |
| `NEGATIVE_AMOUNT` | Negative fare, total or tip |
| `BAD_LOCATION_ID` | Zone ID outside 1 to 265 |
| `UNKNOWN_VENDOR`, `UNKNOWN_PAYMENT_TYPE`, `UNKNOWN_RATE_CODE` | Code not in the TLC data dictionary |
| `DISTANCE_OVER_LIMIT` | Distance over 100 miles |
| `FARE_OVER_LIMIT` | Fare over $500 |
| `DUPLICATE_ROW` | Same vendor, pickup, dropoff, zones, distance and total as an earlier trip |

The limits are constants at the top of `build_db.py` (`MAX_DISTANCE_MILES`, `MAX_FARE_DOLLARS`, `MAX_SPEED_MPH`).

Rows that look odd but are **kept** are recorded in `suspicious_record`: `ODD_PASSENGER_COUNT` (0 or above 6), `FAST_TRIP` (over 70 mph) and `TOTAL_BELOW_FARE`.

Counts per reason, for the report:
```bash
sqlite3 database/taxi.db "select reason_code, count(*) from excluded_record group by 1 order by 2 desc;"
sqlite3 database/taxi.db "select reason_code, count(*) from suspicious_record group by 1 order by 2 desc;"
```

### Derived features

| Feature | Formula | Why it is useful |
|---|---|---|
| `duration_min` | dropoff minus pickup, in minutes | Trip time and congestion |
| `avg_speed_mph` | distance divided by hours | Traffic by hour and zone; also catches impossible trips |
| `fare_per_mile` | fare divided by distance | Pricing efficiency across zones |
| `tip_pct` | tip divided by fare, times 100 (card payments only) | Tipping behaviour; cash tips are not recorded |
| `pickup_hour` | hour of the pickup | Demand by hour |
| `pickup_dow` | weekday of the pickup (0 = Monday) | Weekly demand patterns |

### Normalization

Timestamps are stored as `YYYY-MM-DD HH:MM:SS` text. Vendor, rate code and payment type are stored as integer keys into lookup tables. Zone shapes are converted from the shapefile's coordinate system (EPSG:2263, feet) to latitude/longitude (EPSG:4326) so a web map can draw them.

---

## 7. Database design

The schema is in [`database/schema.sql`](database/schema.sql) (structure dump: [`database/schema_dump.sql`](database/schema_dump.sql)). SQLite was chosen because the database is a single file that every team member can copy, with no server to install.

- **Lookup tables:** `borough`, `service_zone`, `zone`, `vendor`, `rate_code`, `payment_type`. Each name is stored once.
- **Map shapes:** `zone_geometry` holds one GeoJSON polygon per row, kept apart from `zone` because it is large.
- **Trips:** `trip` (movement data and derived features) and `trip_fare` (money data), one row each per trip.
- **Logs:** `excluded_record` and `suspicious_record`.
- **View:** `v_trip_full` joins trips with zone, borough and payment names. The trips API reads from it.
- **Indexes:** pickup time, pickup zone, dropoff zone, day and hour together, distance, payment type, total fare.
- **Constraints:** distance and duration above 0, fares and tips not negative, every code must exist in its lookup table.
- **Summary tables** (built by `summary_tables.sql`): `hourly_demand`, `weekday_demand`, `daily_demand`, `weekday_average`, `period_demand`. They are derived from `trip` and keep the dashboard fast. If one is missing, the backend falls back to computing the same answer from `trip`.

---

## 8. Hand-written algorithm

**Top-K zones with a binary min-heap**, written from scratch in [`backend/algorithms.py`](backend/algorithms.py) (no `heapq`, `sorted()`, `Counter` or pandas sorting). It ranks the K busiest zones by pickups, drop-offs or average fare for `/api/zones/top` and the dashboard's "Top zones" panel.

The heap keeps only the K best rows seen so far. Its root is the weakest of them, so a new row enters only if it beats the root and replaces it in O(log K). Total cost is **O(n log K) time and O(K) space**, against O(n log n) time and O(n) space for sorting everything.

Pseudo-code, complexity analysis and tests: [`docs/person1_algorithm.md`](docs/person1_algorithm.md).

---

## 9. Tests

From the project root, with the database built:

```bash
python -m unittest tests.test_demand_api tests.test_algorithms
```

The tests check the health endpoint, the home page, the demand endpoints, and the hand-written heap (compared against Python's `sorted()` on random inputs).

---

## 10. Project structure

```
nyc-taxi-mobility-dashboard/
├── backend/
│   ├── app.py                 Flask API + static file serving
│   └── algorithms.py          hand-written min-heap and top_k
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js             fetch helpers
│       ├── charts.js          Chart.js rendering
│       ├── dashboard.js       filters, table, detail panel
│       └── map.js             Leaflet zone choropleth
├── database/
│   ├── build_db.py            cleaning + loading pipeline
│   ├── schema.sql             schema, indexes, view
│   ├── schema_dump.sql        schema dump
│   ├── summary_tables.sql     pre-aggregated tables
│   └── taxi_zone_lookup.csv
├── data/
│   ├── raw/                   put the trip file here (taxi_zones.zip included)
│   └── logs/
├── scripts/                   analysis helpers
├── tests/
│   ├── test_demand_api.py
│   └── test_algorithms.py
├── docs/                      technical report, algorithm notes, CodeVibe reports
├── requirements.txt
└── README.md
```

`taxi.db`, `.venv/` and the raw trip file are not committed (see `.gitignore`).

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `can't open file '.../build_db.py'` | You are in the wrong folder. `cd database` first |
| `FileNotFoundError: yellow_tripdata_...` | Wrong file name or path. Check `ls ../data/raw` and use the exact name, including `.csv` or `.parquet` |
| `taxi.db already contains N trips` | Trips are already loaded. To rebuild, delete `taxi.db` and repeat from Step 3a |
| `Neither taxi_zones.dbf nor taxi_zones.shp could be opened` | Use `--shp ../data/raw/taxi_zones.zip` |
| Dashboard loads but has no data | `select count(*) from trip;` returns 0, or Step 3c was run before 3b finished. Reload trips, then rerun 3c |
| `Database not found` from the API | `taxi.db` is not in `database/`. Set `TAXI_DB` or build it |
| `Database problem: no such table` | Rerun Step 3c, or rebuild `taxi.db` |
| `ModuleNotFoundError: flask` (or pandas, pyproj, shapefile) | Activate the virtual environment and run `pip install -r requirements.txt` |
| Port 5000 already in use | Stop the other program, or change `port=5000` at the bottom of `backend/app.py` (on macOS, AirPlay Receiver can occupy 5000) |
| Page opens but buttons or charts do nothing | Open the browser console (F12), fix the error shown, and hard-refresh (Cmd/Ctrl+Shift+R) |
| Filtered queries feel slow | Broad filters scan millions of rows. Narrow the date range or add a borough filter |

---

## 12. Limitations and next steps

- Data covers January 2019 only.
- Pickup counts show recorded trips, not unmet demand.
- Cash tips are not recorded, so `tip_pct` covers card payments only.
- Next steps: more months of data, PostgreSQL for concurrent users, time-sliced and route-level (origin-destination) maps, zone clustering, and deployment.