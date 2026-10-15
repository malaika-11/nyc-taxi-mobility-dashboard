import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"

def find_trip_file():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    for pattern in ("yellow_tripdata*.parquet", "yellow_tripdata*.csv"):
        matches = sorted(DATA_DIR.glob(pattern))
        if matches:
            return matches[0]
    sys.exit("No yellow_tripdata file found in data/raw/. Pass the path as an argument.")

def main():
    trip_file = find_trip_file()
    zones_file = DATA_DIR / "taxi_zone_lookup.csv"

    print(f"=== TRIP DATA SAMPLE ({trip_file.name}) ===")
    if trip_file.suffix == ".parquet":
        import pyarrow.parquet as pq
        sample = next(pq.ParquetFile(trip_file).iter_batches(batch_size=10000)).to_pandas()
    else:
        sample = pd.read_csv(trip_file, nrows=10000)
    print("Columns:", sample.columns.tolist())
    print("\nData types:\n", sample.dtypes)
    print("\nMissing values:\n", sample.isnull().sum())
    print("\nFirst 5 records:\n", sample.head().to_string())

    print("\n=== TAXI ZONE LOOKUP ===")
    zones = pd.read_csv(zones_file)
    print("Shape:", zones.shape)
    print("Columns:", zones.columns.tolist())
    print(zones.head().to_string())

if __name__ == "__main__":
    main()