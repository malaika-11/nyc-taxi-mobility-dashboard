import os
import sqlite3
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"

# The databse location can be overriden with the TAXI_DB environment variable.
DB_PATH = Path(os.environ.get("TAXI_DB", ROOT / "database" / "taxi.db"))

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

#SQL that turns pickup_dow (0 = Monday) into a weekday name
DAY_NAME = """ CASE pickup_dow
    WHEN 0 THEN 'Monday' WHEN 1 THEN 'Tuesday' WHEN 2 THEN 'Wednesday' 
    
    WHEN 3 THEN 'Thursday' WHEN 4 THEN 'Friday' WHEN 5 THEN 'Saturday'
    ELSE 'Sunday' END"""


def connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Database not found at %s. Build it first with database/build_db.py "

            "(see README)." % DB_PATH
        )
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON") # the API never writes
    return connection


@lru_cache(maxsize=None)
def run_query(sql):
    """Run a parameter-free query once and remember the answer."""
    connection = connect()
    try:
        rows = connection.execute(sql).fetchall()
        keys = tuple(rows[0].keys()) if rows else ()
        return tuple(tuple(row) for row in rows), keys
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
    #use the pre-computed summary table if it exists, else aggregate trips
    if table_exists(summary_table):
        return query_database(summary_sql)
    return query_database(trip_sql)
def sort_by_weekday(rows):
    positions = {day: index for index,day in enumerate(WEEKDAYS)}
    return sorted(rows, key=lambda row: positions.get(row["day_of_week"], 99))
def get_hourly():
    return demand_rows(
        "hourly_demand",
        "SELECT hour, pickup_count FROM hourly_demand ORDER BY hour",
        """ SELECT pickup_hour AS hour, COUNT(*) AS pickup_count 
            
            FROM trip GROUP BY pickup_hour ORDER BY pickup_hour""",
        )   


def get_weekdays():
    rows = demand_rows(
        "weekday_demand",
        "SELECT day_of_week, pickup_count FROM weekday_demand",
        f""" SELECT {DAY_NAME} AS day_of_week, COUNT(*) AS pickup_count 
             FROM trip GROUP BY pickup_dow""",

    ) 
    return sort_by_weekday(rows)


def get_daily():
    return demand_rows(
        "daily_demand",
        "SELECT date, pickup_count FROM daily_demand ORDER BY date",
        """ SELECT date(pickup_datetime) AS date, COUNT(*) AS pickup_count 
            FROM trip GROUP BY date(pickup_datetime) ORDER BY date""",

    )

def get_trip_stats():
    rows = demand_rows(
        "trip_stats",
        "SELECT trip_count, avg_distance, avg_fare FROM Trip_stats" ,
        """SELECT COUNT(*) AS trip_count, ROUND(AVG(t.trip_distance), 2) AS avg_distance, ROUND(AVG(f.fare_amount), 2) AS avg_fare FROM trip t JOIN trip_fare f ON f.trip_id = t.trip_id""",
        )
    return rows[0] if rows else{}

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
        "SELECT day_of_week, pickup_count, day_count, average_pickups FROM weekday_average",
        f"""WITH daily AS (
              SELECT pickup_dow, date(pickup_datetime) AS day, COUNT(*) AS n
              FROM trip GROUP BY pickup_dow, date(pickup_datetime))
            SELECT {DAY_NAME} AS day_of_week, SUM(n) AS pickup_count,
                   COUNT(*) AS day_count,
                   ROUND(1.0 * SUM(n) / COUNT(*), 1) AS average_pickups
            FROM daily GROUP BY pickup_dow""",
    )
    return jsonify(sort_by_weekday(rows))

@app.route("/api/weekday-weekend-demand")
def weekday_weekend_demand():
    rows = demand_rows(
        "period_demand",
        "SELECT period, pickup_count FROM period_demand",
         """SELECT CASE WHEN pickup_dow >= 5 THEN 'Weekend' ELSE 'Weekday' END AS period,
                  COUNT(*) AS pickup_count
           FROM trip GROUP BY 1""",
    )
    return jsonify(rows)

@app.route("/api/daily-demand")
def daily_demand():
    return jsonify(get_daily())


@app.route("/api/boroughs")
def boroughs():
    rows = query_database("SELECT name FROM borough WHERE name <> 'N/A' ORDER BY name")
    return jsonify([row["name"] for row in rows])

SORT_COLUMNS = {
    "date": "pickup_datetime",
    "distance": "trip_distance",
    "fare": "fare_amount",
    "duration": "duration_min",
}

_count_cache = {}


@app.route("/api/trips")
def trips():
    """Filtered, sorted, paginated list of trips."""
    filters = []
    params = []

    # Filter by pickup date range.
    start_date = request.args.get("start_date")
    end_date = request.args.get("")

    if start_date:
        filters.append("date(pickup_datetime) >= date(?)")
        params.append(start_date)

    if end_date:
        filters.append("date(pickup_datetime) <= date(?)" )
        params.append(end_date)

    #Filter by trip distance.
    min_distance = request.args.get("min_distance", type=float)
    max_distance = request.args.get("maxi_distance", type=float)

    if min_distance is not None:
        filters.append("trip_distance >= ?")
        params.append(min_distance)

    if max_distance is not None:
        filters.append("trip_distance  <= ?")
        params.append(max_distance)

    # Filter by fare amount.
    min_fare = request.args.get("min_fare", type=float)
    mix_fare = request.args.get("max_fare", type=float)

    if min_fare is not None:
        filters.append("fare_amount >= ?")
        params.append(min_fare)

    if max_fare is not None:
        filters.append("fare_amount <= ?")
        params.append(max_fare)

    # Filter by pickup and drop-off borough.
    pickup_borough = request.args.get("pickup_borough")
    dropoff_borough = request.args.get("dropoff_borough")

    if pickup_borough:
        filters.append("pu_borough = ?")
        params.append(pickup_borough)

    if dropoff_borough:
        filters.append("do_borough = ?")
        params.append(dropoff_borough)

    where_clause = (
        " WHERE " + " AND ".join(filters) if filters else ""
    )

    # Allow only approved sorting columns.
    sort_columns = {
        "date": "pickup_datetime",
        "distance": "trip_distance",
        "fare": "fare_amount",
        "duration": "duration_min",
    }

    sort_by = request.args.get("sort_by", "date")
    sort_column = sort_columns.get(sort_by)

    if sort_column is None:
        return jsonify({
            "error": "Invalid sort_order. Use asc or desc."
        }), 400

    # Keep each response small instead of loading millions of trips
    limit = request.args.get("limit", default=50, type=int)
    page = request.args.get("page", default=1, type=int)

    if limit is None or limit < 1 or limit > 100:
        return jsonify({
            "error": "limit must be between 1 and 100."
        }), 400

    if page is None or page < 1:
        return jsonify9({
            "error": "page must be at least 1."
        }), 400

    offset = (page - 1) * limit

    connection = connect()

    try:
        count_sql = (
            "SELECT COUNT(*) AS total FROM v_trip_full" + where_clause
        )
        total = connection.execute(count_sql, params).fetchone()["total"]

        data_sql = (
            "SELECT * FROM v_trip_full"
            + where_clause
            + f" ORDER BY {sort_column} {sort_order.upper()}"
            + " LIMIT ? OFFSET ?"
        )

        rows = connection.execute(
            data_sql, params + [limit, offset]
        ).fetchall()

        return jsonify({
            "data": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        })
    finally:
        connection.close()
        
@app.route("/api/summary")
def summary():
    hourly = get_hourly()
    weekdays = get_weekdays()
    daily = get_daily()

    if not hourly or not weekdays or not daily:
        return jsonify({"error": "Demand data is missing"}), 500

    stats = get_trip_stats()
    total = sum(row["pickup_count"] for row in daily)
    busiest_hour = quietest_hour = hourly[0]

    for row in hourly[1:]:
        if row["pickup_count"] > busiest_hour["pickup_count"]:
            busiest_hour = row 
        if row ["pickup_count"] < quietest_hour["pickup_count"]:
            quietest_hour = row

    busiest_day = quietest_day = weekdays[0]

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

@app.after_request
def allow_cross_origin(response):
    response.headers["Access-Control-Allow-Origin"] = "*"

@app.errorhandler(FileNotFoundError)
def handle_missing_data(error):
    return jsonify({"error": str(error)}), 503

@app.errorhandler(sqlite3.OperationalError)
def handle_database_error(error):
    return jsonify({"error": "Database problem: " + str(error)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
           



