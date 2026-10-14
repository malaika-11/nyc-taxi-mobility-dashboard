import csv
import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "yellow_tripdata_2019-01.csv"
OUTPUT_DIR = ROOT / "outputs"