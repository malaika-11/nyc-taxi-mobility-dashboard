--NYC Taxi Database Schema (SQLite)
--You can run it automatically by build_db.py

PRAGMA foreign_keys = ON;

--Lookup tables: each value is stored once

CREATE TABLE IF NOT EXISTS borough (
    borough_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE 
);

CREATE TABLE IF NOT EXISTS service_zone (
    service_zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE 
);

CREATE TABLE IF NOT EXISTS zone (
    location_id INTEGER PRIMARY KEY,
    zone_name   TEXT NOT NULL,
    borough_id  INTEGER NOT NULL REFERENCES borough(borough_id),
    service_zone_id INTEGER NOT NULL REFERENCES service_zone(service_zone_id)

);

CREATE TABLE IF NOT EXISTS zone_geometry (
    geometry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL REFERENCES zone(location_id),
    geojson     TEXT NOT NULL 
);

CREATE TABLE IF NOT EXISTS vendor (
    vendor_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_code (
    rate_code_id INTEGER PRIMARY KEY,
    description  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payment_type (
    payment_type_id  INTEGER PRIMARY KEY,
    description    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trip (
    trip_id             INTEGER PRIMARY KEY,
    vendor_id          INTEGER NOT NULL REFERENCES vendor(vendor_id),
    pickup_datetime     TEXT NOT NULL,
    dropoff_datetime    TEXT NOT NULL,
    pu_location_id      INTEGER NOT NULL REFERENCES zone(location_id),
    do_location_id      INTEGER NOT NULL REFERENCES zone(location_id),
    rate_code_id        INTEGER NOT NULL REFERENCES rate_code(rate_code_id),
    payment_type_id     INTEGER NOT NULL REFERENCES payment_type(payment_type_id),
    passenger_count     INTEGER,
    trip_distance       REAL NOT NULL CHECK (trip_distance > 0),
    store_and_fwd       INTEGER,

    --features we calculate ourselves:
    duration_min        REAL NOT NULL CHECK (duration_min > 0),
    avg_speed_mph       REAL,
    pickup_hour         INTEGER NOT NULL,
    pickup_dow          INTEGER NOT NULL
);

--Money details
CREATE TABLE IF NOT EXISTS trip_fare (
    trip_id       INTEGER PRIMARY KEY REFERENCES trip(trip_id),
    fare_amount   REAL NOT NULL CHECK (fare_amount >=0),
    extra         REAL,
    mta_tax       REAL,
    tip_amount    REAL CHECK (tip_amount >= 0),
    tolls_amount  REAL,
    improvement_surcharge  REAL,
    congestion_surcharge   REAL,
    airport_fee   REAL,   
    cbd_congestion_fee     REAL, 
    total_amount  REAL NOT NULL CHECK (total_amount >= 0),
    --features we calculate ourselves
    fare_per_mile REAL,
    tip_pct       REAL
);

CREATE TABLE IF NOT EXISTS excluded_record(
    log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file  TEXT,
    source_row   INTEGER,
    reason_code  TEXT NOT NULL

);

-- INDEXES: make the dashboard faster

CREATE INDEX IF NOT EXISTS idx_trip_pickup      ON trip(pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_trip_pu_zone     ON trip(pu_location_id);
CREATE INDEX IF NOT EXISTS idx_trip_do_zone     ON trip(do_location_id);
CREATE INDEX IF NOT EXISTS idx_trip_hour_dow    ON trip(pickup_dow, pickup_hour);
CREATE INDEX IF NOT EXISTS idx_trip_distance    ON trip (trip_distance);
CREATE INDEX IF NOT EXISTS idx_trip_payment     ON trip(payment_type_id);
CREATE INDEX IF NOT EXISTS idx_fare_total       ON trip_fare(total_amount);

-- trips joined with zone names

CREATE VIEW IF NOT EXISTS v_trip_full AS
SELECT t.*, f.fare_amount, f.tip_amount, f.total_amount, f.fare_per_mile, f.tip_pct, pz.zone_name AS pu_zone, pb.name AS pu_borough, dz.zone_name AS do_zone, db.name AS do_borough, p.description AS payment_type

FROM trip t
JOIN trip_fare f     ON f.trip_id = t.trip_id
JOIN zone pz         ON pz.location_id = t.pu_location_id
JOIN borough pb      ON pb.borough_id = pz.borough_id
JOIN zone dz         ON dz.location_id = t.do_location_id
JOIN borough db      ON db.borough_id = dz.borough_id
JOIN payment_type p  ON p.payment_type_id = t.payment_type_id;
