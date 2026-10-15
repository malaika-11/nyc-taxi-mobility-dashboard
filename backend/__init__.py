import sqlite3
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
DB_PATH = ROOT / "database" / "taxi.db"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path="",
)

def query_database(sql, parameters=()):
    if not DB_PATH.exists():
       raise FileNotFoundError(
           "Database not found. Run database/build_dba.py first."
       )

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]

    finally:
        connection.close()

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "project": "NYC Taxi Mobility Data Explorer",
        "database_exists": DB_PATH.exists(),
    })

@app.route("/api/hourly-demand")
def hourly_demand():
    rows = query_database("""
         SELECT hour, pickup_count
         FROM hourly_demand
         ORDER BY hour
    """)
    return jsonify(rows)

@app.route("/api/weekday-demand")
def weekday_demand():
    rows = query_database("""
         SELECT day_of_week, pickup_count
         FROM weekday_demand
    """)

    order = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday" , "Saturday" , "Sunday" ,
    ]
    positions = {day: index for index, day in enumerate(order)}
    rows.sort(key=lambda row: positions.get(row["day_of_week"], 99))
    return jsonify(rows)

@app.route("/api/weekday-average")
def weekday_average():
    rows = query_database("""
         SELECT day_of_week, pickup_count, day_count, average_pickups
    FROM weekday_average
    """)
    return jsonify(rows)

@app.route("/api/weekday-weekend-demand")
def weekday_weekend_demand():
    rows = query_database("""
         SELECT period, pickup_count
         FROM period_demand
    """)
    return jsonify(rows)

@app.route("/api/daily-demand")
def daily_demand():
    rows = query_database("""
         SELECT date, pickup_count
         FROM daily_demand
         ORDER BY date
    """)
    return jsonify(rows)

@app.route("/api/summary")

def summary():
    hourly = query_database("""
         SELECT hour, pickup_count
         FROM hourly_demand
    """)
    weekdays = query_database("""
         SELECT day_of_week, pickup_count
         FROM weekday_demand
    """)
    daily = query_database("""
         SELECT SUM(pickup_count) AS total
         FROM daily_demand
    """)

    if not hourly or not weekdays or not daily:
        return jsonify({"error": "Demand data is missing"}), 500

    # Manual linear scan: 0(n) time and 0(1) auxiliary space.
    busiest_hour = hourly[0]
    quietest_hour = hourly[0] 

    for row in hourly[1:]:
        if row["pickup_count"] > busiest_hour["pickup_count"]:
            busiest_hour = row
        if row["pickup_count"] < quietest_hour["pickup_count"]:
            quietest_hour = row

    busiest_day = weekdays[0]
    quietest_day = weekdays[0]

    for row in weekdays[1:]:
        if row["pickup_count"] > busiest_day["pickup_count"]:
            busiest_day = row
        if row["pickup_count"] < quietest_day["pickup_count"]:
            quietest_day = row

    return jsonify({
        "total_pickups": daily[0]["total"],
        "busiest_hour": busiest_hour["hour"],
        "busiest_hour_count": busiest_hour["pickup_count"],
        "quietest_hour": quietest_hour["hour"],
        "quietest_hour_count": quietest_hour["pickup_count"],
        "busiest_day": busiest_day["day_of_week"],
        "busiest_day_count": busiest_day["pickup_count"],
        "quietest_day": quietest_day["day_of_week"],
        "quietest_day_count": quietest_day["pickup_count"],
    })

@app.errorhandler(FileNotFoundError)
def handle_missing_data(error):
    return jsonify({"error": str(error)}), 503

if __name__ == "__main__":
    app.run(debug=True, port=5000)