import sqlite3
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"

#the app will use the firts database file it finds
DB_CANDIDATES = [
    ROOT / "outputs" / "taxi.db",
    ROOT /"database" / "taxi.db",
]

DB_PATH = next((path for path in DB_CANDIDATES if path.exists()), DB_CANDIDATES[0])

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path="",
)

WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

#SQL that turns pickup_dow into a weekday name
DAY_NAME = """ CASE pickup_dow
    WHEN 0 THEN 'Monday' WHEN 1 THEN 'Tuesday' WHEN 2 THEN 'Wednesday' WHEN 3 THEN 'Thursday' WHEN 4 THEN 'Friday' WHEN 5 THEN 'Saturday'
    ELSE 'Sunday' END"""


def connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "database not found. Put taxi.db in the database/ or outputs/ folder."
        )
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

@lru_cache(maxsize=None)
def run_query(sql):
    """Run the query once and remember the answer"""
    connection = connect()
    try:
        rows = connection.execute(sql).fetchall()
        return tuple(tuple(row) for row in rows), tuple(rows[0].keys()) if rows else ()
    finally:
        connection.close()

def query_database(sql):
    data, keys = run_query(sql)
    return [dict(zip(keys, row)) for row in data]

def table_exists(name):
    connection = connect()
    try:
        found = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        return found is not None
    finally:
        connection.close()

def demand_rows(summary_table, summary_sql, trip_sql):
    #use the summary table if the batabase has one, if not use trip table
    if table_exists(summary_table):
        return query_database(summary_sql)
    return query_database(trip_sql)

def get_hourly():
    return demand_rows(
        "hourly_demand",
        "SELECT hour, pickup_count FROM hourly_demand ORDER BY hour",
        """ SELECT pickup_hour AS hour, COUNT(*) AS pickup_count FROM trip GROUP BY pickup_hour ORDER BY pickup_hour""",
    )   

def get_weekdays():
    rows = demand_rows(
        "weekday_demand",
        "SELECT day_of_week, pickup_count FROM weekday_demand",
        f""" SELECT {DAY_NAME} AS day_of_week, COUNT(*) AS pickup_count FROM trip GROUP BY pickup_dow""",

    ) 
    return sort_by_weekday(rows)

def get_daily():
    return demand_rows(
        "daily_demand",
        "SELECT date, pickup_count FROM daily_demand ORDER BY date",
        """ SELECT date(pickup_datetime) AS date, COUNT(*) AS pickup_count FROM trip GROUP BY date(pickup_datetime) ORDER BY date""",

    )

def sort_by_weekday(rows):
    positions = {day: index for index, day in enumerate(WEEKDAYS)}
    return sorted(rows, key=lambda row: positions.get(row["day_of_week"], 99))

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "project": "NYC Taxi Mobility Data Explorer",
        "database_exists": DB_PATH.exists(),
        "database_file": DB_PATH.name,
        
    })

@app.route("/api/hourly-demand")
def hourly_demand():
    return jsonify(get_hourly())

@app.route("/api/weekday-demand")
def weekday_demand():
    return jsonify(get_weekdays())

@app.route("/api/weekday-average")
def weekday_average():
    rows = demand_rows(
        "weekday_average",
        """ SELECT day_of_week, pickup_count, day_count, average_pickups FROM weekday_average""",
        f""" WITH daily AS (
             SELECT pickup_dow, date(pickup_datetime) AS day, COUNT(*) AS n FROM trip GROUP BY pickup_dow, date(pickup_datetime))
             SELECT {DAY_NAME} AS day_of_week, SUM(n) AS pickup_count, COUNT(*) AS day_count, ROUND(1.0* SUM(n) / COUNT(*), 1) AS average_pickups FROM daily GROUP BY pickup_dow""",

    )
    return jsonify(sort_by_weekday(rows))

@app.route("/api/weekday-weekend-demand")
def weekday_weekend_demand():
    rows = demand_rows(
        "period_demand",
        "SELECT period, pickup_count FROM period_demand",
        """ SELECT CASE WHEN pickup_dow >= 5 THEN 'Weekend' ELSE 'Weekday' END AS period, COUNT(*) AS pickup_count FROM trip GROUP BY 1""",
    )
    return jsonify(rows)

@app.route("/api/daily-demand")
def daily_demand():
    return jsonify(get_daily())

@app.route("/api/summary")
def summary():
    hourly = get_hourly()
    weekdays = get_weekdays()
    daily = get_daily()

    if not hourly or not weekdays or not daily:
        return jsonify({ "error": "Demand data is missing"}), 500

    total = 0
    for row in daily:
        total += row["pickup_count"]

    busiest_hour = hourly[0]
    quietest_hour = hourly[0]

    for row in hourly[1:]:
        if row["pickup_count"] > busiest_hour["pickup_count"]:
            busiest_hour = row 
        if row ["pickup_count"] < quietest_hour["pickup_count"]:
            quietest_hour = row

    busiest_day = weekdays[0]
    quietest_day = weekdays[0]

    for row in weekdays [1:]:
        if row["pickup_count"] > busiest_day["pickup_count"]:
            busiest_day = row

        if row["pickup_count"] < quietest_day["pickup_count"]:
            quietest_day = row

    return jsonify({
        "total_pickups": total,
        "busiest_hour": busiest_hour["hour"],
        "busiest_hour_count": busiest_hour["pickup_count"],
        "quietest_hour": quietest_hour["hour"],
        "quietest_hour_count": quietest_hour["pickup_count"],
        "busiest_day": busiest_day["day_of_week"],
        "busiest_day_count": busiest_day["pickup_count"],
        "quietest_day": quietest_day["day_of_week"],
        "quietest_day_count": quietest_day["pickup_count"],

    })                    

@app.errorhandler (FileNotFoundError)
def handle_missing_data(error):
    return jsonify({"error": str(error)}), 503

@app.errorhandler (sqlite3.OperationalError)
def handle_database_error(error):
    return jsonify({"error": "Database problem: " + str(error)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
           



