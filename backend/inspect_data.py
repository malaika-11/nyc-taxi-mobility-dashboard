from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"

def main():
    trip_file = DATA_DIR / "yellow_tripdata_2019-01.csv"
    zones_file = DATA_DIR / "taxi_zone_lookup.csv"

    print("=== TRIP DATA SAMPLE ===")
    for chunk in pd.read_csv(trip_file, chunksize=10000):
        print("Columns:", chunk.columns.tolist())
        print("\nData types:\n", chunk.dtypes)
        print("\nMissing values:\n", chunk.isnull().sum())
        print("\nFirst 5 records:\n",chunk.head().to_string())
        break

    print("\n=== TAXI ZONE LOOKUP ===")
    zones = pd.read_csv(zones_file)
    print("Shape:",zones.shape)
    print("Columns:",zones.columns.tolist())
    print(zones.head().to_string())

if __name__ == "__main__":
    main()