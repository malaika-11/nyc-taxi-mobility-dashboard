import csv
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_FILE = ROOT_DIR / "database" / "taxi.db"
OUTPUT_DIR = ROOT_DIR / "outputs"
LOG_FILE = ROOT_DIR / "data"/ "logs" / "demand_analysis_log.txt"

WEEKDAYS = [
    "Monday", "Tuesday" , "Wednesday" , "Thursday" , "Friday" , "Saturday" , "Sunday" ,
]

def write_csv(path, fieldnames, rows):
    """Write rows to a CSV file with a header."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def run_analysis():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DB_FILE.exists():
        raise FileNotFoundError(f"Database not found: {DB_FILE}")

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row

    try:
        #Demand by pickup hour,
        hourly = connection.execute("""
        SELECT pickup_hour AS hour, COUNT(*) AS pickups
        FROM trip
        GROUP BY pickup_hour
        ORDER BY pickup_hour
        """).fetchall()

        write_csv(
            OUTPUT_DIR / "hourly_demand.csv",
            ["hour", "pickups"],
            [dict(row) for row in hourly],
        ) 

        #Demand by calendar date.
        daily = connection.execute("""
            SELECT
                date(pickup_datetime) AS date,
                CASE pickup_dow
                    WHEN 0 THEN 'Monday'
                    WHEN 1 THEN 'Tuesday'
                    WHEN 2 THEN 'Wednesday'
                    WHEN 3 THEN 'Thursday'
                    WHEN 4 THEN 'Friday'
                    WHEN 5 THEN 'Saturday'
                    ELSE 'Sunday'
                END AS weekday,
            COUNT(*) AS pickups
        FROM trip
        GROUP BY date(pickup_datetime), pickup_dow
        ORDER BY date    
    """).fetchall()
    
        write_csv(
            OUTPUT_DIR / "daily_demand.csv",
            ["date", "weekday", "pickups"],
            [dict(row) for row in daily],
        )  

        #Total pickups by weekday.
        weekday_totals = connection.execute("""
        SELECT
            pickup_dow,
            COUNT(*) AS pickups
        FROM trip
        GROUP BY pickup_dow
    """).fetchall()

        totals = {
            row["pickup_dow"]: row["pickups"] 
            for row in weekday_totals
        }

        weekday_rows = [
            {"weekday": WEEKDAYS[index], "pickups": totals.get(index, 0)}
            for index in range(7)
        ]

        write_csv(
            OUTPUT_DIR / "day_of_week_demand.csv",
            ["weekday", "pickups"],
            weekday_rows,
        )

       # Average pickups per calendar day for each weekday.
        daily_totals = {}
        for row in daily:
            day = WEEKDAYS.index(row["weekday"])
            daily_totals.setdefault(day, []).append(row["pickups"])

        average_rows = []
        for index, weekday in enumerate(WEEKDAYS):
            values = daily_totals.get(index, [])
            average = sum(values) / len(values) if values else 0

            average_rows.append({
                "weekday": weekday,
                "total_pickups": sum(values),
                "number_of_days": len(values),
                "average_daily_pickups": f"{average:.2f}",
            })

        write_csv(
            OUTPUT_DIR / "average_daily_demand.csv",
            [
            "weekday", "total_pickups",
            "number_of_days", "average_daily_pickups",
            ],
        average_rows,
    )

        #Compare weekdays and weekends.
        period_totals = {"Weekday": 0, "Weekend": 0}
        for row in daily:
            period = "Weekend" if row ["weekday"] in ("Saturday", "Sunday") else "Weekday"
            period_totals[period] += row["pickups"]

        period_rows = [
            {"period": period, "pickups": period_totals[period]}
            for period in ("Weekday", "Weekend")
            ]

        write_csv(
            OUTPUT_DIR / "weekday_weekend_demand.csv",
            ["period", "pickups"],
            period_rows,
        )

        total_trips = sum(row["pickups"] for row in daily)
        busiest_hour = max(hourly, key=lambda row: row["pickups"])
        quietest_hour = min(hourly, key=lambda row: row["pickups"])
        busiest_day = max(weekday_rows, key=lambda row: row["pickups"])

        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(f"\nAnalysis run: {datetime.now().isoformat(timespec='seconds')}\n")
            file.write(f"Database: {DB_FILE}\n")
            file.write(f"Trips analysed: {total_trips:,}\n")
            file.write(f"Dates analysed: {len(daily)}\n")
            file.write(
                f"Busiest hour: {busiest_hour['hour']}:00 "
                f"({busiest_hour['pickups']:,} pickups)\n"
            )
            file.write(
                f"Quietest hour: {quietest_hour['hour']}:00 "
                f"({quietest_hour['pickups']:,} pickups)\n"
            )
            file.write(
                f"Busiest weekday by total: {busiest_day['weekday']}"
                f"({busiest_day['pickups']:,} pickups)\n"
            )
            file.write("Generated all five demand CSV files successfully.\n")

        print(f"Trips analysed: {total_trips:,}")
        print(f"Dates analysed: {len(daily)}")
        print(f"Busiest hour: {busiest_hour['hour']}: 00")
        print(f"Quitest hour: {quietest_hour['hour']}: 00")
        print(f"Busiest weekday: {busiest_day['weekday']}")
        print(f"Log saved to: {LOG_FILE}")
   

    finally:
        connection.close()

if __name__ == "__main__":
    run_analysis()


    
