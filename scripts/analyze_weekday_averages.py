import csv
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT_DIR / "outputs" / "daily_demand.csv"
OUTPUT_FILE = ROOT_DIR / "outputs" / "average_daily_demand.csv"

WEEKDAYS = [
    "Monday", "Tuesday" , "Wednesday" , "Thursday" , "Friday" , "Saturday" , "Sunday" ,
]

def calculate_averages():
    """Calculate total demand, number of dates, and daily averages."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run scripts/analyze_demand.py first."
        )
    
    totals = defaultdict(int)
    days_count = defaultdict(int)

    with INPUT_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        required_columns = {"date", "weekday", "pickups"}
        if not reader.fieldnames or not required_columns.issubset(
            reader.fieldnames
        ):
            raise ValueError(
                "daily_demand.csv must contain date, weekday, and pickups."
            )
        for row in reader:
            weekday = row["weekday"].strip()

            if weekday not in WEEKDAYS:
                continue

            pickups = int(row["pickups"])
            totals[weekday] += pickups
            days_count[weekday] +=1

    with OUTPUT_FILE.open("w", newline="", encodig="utf-8") as file:
        fieldnames = [
           "weekday",
            "total_pickups",
            "number_of_days",
            "average_daily_pickups",
        ]

        writer = csv.DictWriter(file, fieldnames=fieldames)
        writer.writeheader

        for weekday in WEEKDAYS:
            count = days_count[weekday]

            if count == 0:
               average = 0

            else:
                average = totals[weekday] / count

            writer.writerow({
                "weekday": weekday,
                "total_pickups": totals[weekday],
                "number_of_days": count,
                "average_daily_pickups": f"{average:.2f}",
            })

        print(f"Average demand saved to: {OUTPUT_FILE}")
        print("\nAverage daily taxi pickups by weekday:")

        for weekday in WEEKDAYS:
            count = days_count[weekday]
            average = totals[weekday] / count if count else 0
            print(f"{weekday}: {average:,.2f} pickups per day ({count} days)")

if __name__ == "__main__":
    calculate_averages()