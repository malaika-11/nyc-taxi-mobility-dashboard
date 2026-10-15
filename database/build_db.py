import argparse, json, sqlite3, sys, tempfile, zipfile
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import shapefile 
import numpy as np
from pyproj import Transformer

VENDORS = {1: "Creative Mobile Technologies", 2: "Curb Mobility", 6:"Myle Technologies", 7: "Helix" }
RATE_CODES = {1: "Standard", 2: "JFK", 3: "Newark", 4: "Nassau/Westchester", 5: "Negotiated", 6: "Group ride", 99: "Unknown"}
PAYMENTS = {0: "Flex Fare", 1: "Credit card", 2: "Cash", 3: "No charge", 4: "Dispute", 5: "Unknown", 6: "Voided"}

HERE = Path(__file__).resolve().parent   # so the script works from any folder
SCHEMA_FILE = HERE / "schema.sql"
SUMMARY_FILE = HERE / "summary_tables.sql"

MAX_DISTANCE_MILES = 100
MAX_FARE_DOLLARS = 500
MAX_SPEED_MPH = 100
SUSPICIOUS_SPEED_MPH = 70

def resolve_shapefile(path):
    """Accept either taxi_zones.shp or the original taxi_zones.zip from the TLC."""
    if not str(path).lower().endswith(".zip"):
        return str(path)
    folder = Path(tempfile.mkdtemp(prefix="taxi_zones_"))
    with zipfile.ZipFile(path) as archive:
        archive.extractall(folder)
    return str(next(folder.rglob("*.shp")))

def setup_zones(con, lookup_file, shp_file):

    con.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    con.executescript(open("schema.sql").read())
    con.executemany(" INSERT OR IGNORE INTO vendor VALUES (?, ?)", VENDORS.items())
    con.executemany(" INSERT OR IGNORE INTO rate_code VALUES (?, ?)", RATE_CODES.items())
    con.executemany(" INSERT OR IGNORE INTO payment_type VALUES (?, ?)", PAYMENTS.items())

    zones = pd.read_csv(lookup_file).fillna("N/A")
    zones.columns = ["location_id", "borough", "zone", "service_zone"]

    for name in zones["borough"]. unique():
        con.execute("INSERT OR IGNORE INTO borough (name) VALUES (?)", (name,))

    for name in zones ["service_zone"]. unique():
        con.execute ("INSERT OR IGNORE INTO service_zone (name) Values (?)", (name,))

    borough_id  = dict(con.execute("SELECT name, borough_id FROM borough"))
    service_id = dict(con.execute("SELECT name, service_zone_id FROM service_zone"))

    for z in zones.itertuples(): 
        con.execute("INSERT OR REPLACE INTO zone values (?, ?, ?, ?)", (z.location_id, z.zone, borough_id[z.borough], service_id [z.service_zone]))

    shp_file = resolve_shapefile(shp_file)

    converter = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    con.execute("DELETE FROM zone_geometry")
    for item in shapefile.Reader(shp_file). shapeRecords():
        location_id = int(item.record["LocationID"])
        shape = item.shape.__geo_interface__
        polygons = [shape["coordinates"]] if shape["type"] == "Polygon" else shape["coordinates"]
        for polygon in polygons: 
            new_polygon = [[list(converter.transform(x, y)) for x, y in ring] for ring in polygon]
            geojson = json.dumps({"type": "Polygon", "coordinates": new_polygon})
            con.execute("INSERT INTO zone_geometry(location_id, geojson) VALUES(?, ?)", (location_id, geojson)) 
    con.commit()

def read_in_chunks(path):
    size = 200000
    if path.endswith(".csv"):
        return pd.read_csv(path, chunksize=size, parse_dates=["tpep_pickup_datetime", "tpep_dropoff_datetime"])
    df = pd.read_parquet(path)
    return[df[i:i + size] for i in range (0, len(df), size)]

def find_duplicates(df, seen):
    key = ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance", "total_amount"]
    fingerprints = pd.util.hash_pandas_object(df[key], index=False).to_numpy()
    repeated_in_chunk = pd.Series(fingerprints).duplicated().to_numpy()
    seen_in_earlier_chunk = np.isin(fingerprints, seen)
    duplicate = repeated_in_chunk | seen_in_earlier_chunk
    seen = np.concatenate([seen, fingerprints[~duplicate]])
    return pd.Series(duplicate, index=df.index), seen

def find_suspicious(df):
    rules = [
        ("ODD_PASSENGER_COUNT", df["passenger_count"].isna() | (df["passenger_count"] ==0) | (df["passenger_count"] > 6)),
        ("FAST_TRIP", df["avg_speed_mph"] > SUSPICIOUS_SPEED_MPH),
        ("TOTAL_BELOW_FARE", df ["total_amount"] < df["fare_amount"]), 
    ]
    reason = pd.Series("", index=df.index)
    for name, broken in rules:
        reason[(reason =="") & broken] = name
    return reason     


def find_bad_rows(df, start, end, duplicate):
    pickup = df["tpep_pickup_datetime"]
    dropoff = df["tpep_dropoff_datetime"]
    hours = (dropoff -pickup). dt.total_seconds() /3600
    speed = df["trip_distance"] /hours.where(hours > 0)
    required = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance", "fare_amount", "total_amount"]

    rules = [
        ("MISSING_VALUE", df[required]. isna(). any(axis=1)),
        ("OUTSIDE_DATE_RANGE", (pickup < start) | (pickup >= end)),
        ("DROPOFF_NOT_AFTER_PICKUP", dropoff <= pickup),
        ("TRIP_OVER_24_HOURS", hours > 24), 
        ("ZERO_OR_NEGATIVE_DISTANCE", df["trip_distance"] <= 0),
        ("IMPOSSIBLE_SPEED", speed > MAX_SPEED_MPH),
        ("NEGATIVE_AMOUNT", (df["fare_amount"] < 0) | (df["total_amount"] < 0) | (df["tip_amount"] < 0)),
        ("BAD_LOCATION_ID", ~df["PULocationID"].between(1, 265) | ~df["DOLocationID"].between(1, 265)), 
        ("UNKNOWN_VENDOR", ~df["VendorID"].isin(VENDORS)),
        ("UNKNOWN_PAYMENT_TYPE", ~df["payment_type"].isin(PAYMENTS)),
        ("UNKNOWN_RATE_CODE", ~df["RatecodeID"].isin(RATE_CODES)),
        ("DISTANCE_OVER_LIMIT", df["trip_distance"] > MAX_DISTANCE_MILES),
        ("FARE_OVER_LIMIT", df["fare_amount"] > MAX_FARE_DOLLARS),
        ("DUPLICATE_ROW", duplicate),

    ]

    reason = pd.Series("", index=df.index)
    for name, broken in rules:
        reason[(reason == "") & broken] = name
    return reason 

def load_trips(con, trip_file, start, end):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    next_id = 1 + con.execute("SELECT  COALESCE(MAX(trip_id), 0) FROM trip").fetchone()[0]
    seen = np.array([], dtype="uint64")

    for df in read_in_chunks(trip_file):
        df = df.rename(columns={"Airport_fee": "airport_fee"})
        for col in ["congestion_surcharge", "airport_fee", "cbd_congestion_fee"]:
            if col not in df.columns:
                df[col] = 0
            df[col] = df[col].fillna(0)
        df ["RatecodeID"] = df["RatecodeID"].fillna(99).astype(int)
        duplicate, seen = find_duplicates(df, seen)
        reason = find_bad_rows(df, start, end, duplicate)
        log = pd.DataFrame({"source_file": trip_file, "source_row": df.index[reason != ""], "reason_code": reason[reason != ""]})
        log.to_sql("excluded_record", con, if_exists="append", index=False)
        df =df[reason == ""].copy()

        df["duration_min"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60
        df["avg_speed_mph"] = df["trip_distance"] / (df["duration_min"] /60)
        df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
        df["pickup_dow"] = df["tpep_pickup_datetime"].dt.dayofweek
        df["fare_per_mile"] = df["fare_amount"] / df["trip_distance"].where(df["trip_distance"] > 0)
        paid_by_card = (df["payment_type"] == 1) & (df["fare_amount"] >0)
        df["tip_pct"] = (df["tip_amount"] / df["fare_amount"] * 100).where(paid_by_card)
        df["store_and_fwd"] = df["store_and_fwd_flag"].map({"Y": True, "N": False})
        flagged = find_suspicious(df)
        odd = pd.DataFrame({"source_file": trip_file, "source_row": df.index[flagged != ""], "reason_code": flagged[flagged != ""]})
        odd.to_sql("suspicious_record", con, if_exists="append", index=False)

        df["pickup_datetime"] = df["tpep_pickup_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df["dropoff_datetime"] = df["tpep_dropoff_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df["trip_id"] = range(next_id, next_id +len(df))
        next_id += len(df)

        df = df.rename(columns={"VendorID": "vendor_id", "PULocationID": "pu_location_id","DOLocationID": "do_location_id", "RatecodeID": "rate_code_id", "payment_type": "payment_type_id"})
        trip_columns = ["trip_id", "vendor_id", "pickup_datetime", "dropoff_datetime", "pu_location_id","do_location_id", "rate_code_id", "payment_type_id", "passenger_count", "trip_distance", "store_and_fwd", "duration_min", "avg_speed_mph", "pickup_hour", "pickup_dow"]
        fare_columns = ["trip_id", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "congestion_surcharge", "airport_fee", "cbd_congestion_fee", "total_amount", "fare_per_mile", "tip_pct"]
        df[trip_columns].to_sql("trip", con, if_exists="append", index=False)
        df[fare_columns].to_sql("trip_fare", con, if_exists="append", index=False)
        con.commit()
        print ("loaded", len(df), "trips, excluded", len(log), ", flagged", len(odd))

def build_summaries(con):
    """(Re)create the indexes and the pre-aggregated tables the dashboard reads."""
    con.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))   # idempotent
    con.executescript(SUMMARY_FILE.read_text(encoding="utf-8"))
    con.execute("ANALYZE")
    con.commit()
    print("summary tables built")



def main():
    parser = argparse.ArgumentParser(description="Build the NYC taxi SQLite database.")
    parser.add_argument("--db", default=str(HERE / "taxi.db"), help="output database file")
    parser.add_argument("--init", action="store_true", help="create tables and load zones")
    parser.add_argument("--lookup", help="taxi_zone_lookup.csv")
    parser.add_argument("--shp", help="taxi_zones.shp (or the taxi_zones.zip)")
    parser.add_argument("--trips", help="yellow trip file (.csv or .parquet)")
    parser.add_argument("--start", default="2000-01-01", help="keep trips from this date")
    parser.add_argument("--end", default="2100-01-01", help="keep trips before this date")
    parser.add_argument("--append", action="store_true", help="allow loading into a database that already has trips")
    parser.add_argument("--summary", action="store_true", help="build indexes and summary tables")
    args = parser.parse_args()



    if args.init and (not args.lookup or not args.shp):
        parser.error("--init needs --lookup and --shp")

    connection = sqlite3.connect(args.db)
    connection.execute("PRAGMA foreign_keys = ON")
    if args.init:
        setup_zones(connection, args.lookup, args.shp)
    if args.trips:
        has_zones = connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'zone'").fetchone()
        if not has_zones:
            sys.exit("No tables yet. Run once with --init --lookup ... --shp ... first.")
        existing = connection.execute("SELECT COUNT(*) FROM trip").fetchone()[0]
        if existing and not args.append:
            sys.exit(f"{args.db} already contains {existing:,} trips. Delete the file "
                     "to rebuild from scratch, or pass --append to add more.")
        load_trips(connection, args.trips, args.start, args.end)
    if args.summary:
        build_summaries(connection)
    connection.close()

if __name__ == "__main__":
    main()
