#!/usr/bin/env python3
"""
Load only the latest InsideAirbnb listings snapshot per city for the map.
Much faster than loading calendar/reviews for every snapshot.
"""
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'airbnb.db')

sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from load_data import (
    DATA_DIR, download_file, load_listings,
    # Snapshots list
    SNAPSHOTS,
)


# Latest snapshot per city, by date.
LATEST_SNAPSHOTS = {}
for state, city, date in SNAPSHOTS:
    key = (state, city)
    if key not in LATEST_SNAPSHOTS or date > LATEST_SNAPSHOTS[key][2]:
        LATEST_SNAPSHOTS[key] = (state, city, date)


def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("Run create_database.py first!")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    print("=" * 60)
    print("Loading latest listings snapshots for the map")
    print("=" * 60)

    snapshots = list(LATEST_SNAPSHOTS.values())
    # Download listings files first
    for state, city, date in snapshots:
        download_file(state, city, date, 'listings')

    total = 0
    for state, city, date in snapshots:
        print(f"\n--- {state}/{city} @ {date} ---")
        total += load_listings(conn, state, city, date)

    print("\n" + "=" * 60)
    print(f"Loaded {total:,} listings from {len(snapshots)} cities")
    print("=" * 60)
    conn.close()

    # Seasonal demand curves (map's "Demand" layer) are derived from a
    # separate forward-calendar download, not the listings snapshot itself.
    # Without this step, any newly loaded/refreshed city would silently have
    # no demand_curve and the Demand layer would look blank for it — so we
    # always re-derive curves as part of the standard map-data load.
    print("\nDeriving seasonal demand curves for the newly loaded snapshots...")
    import load_demand_curves
    load_demand_curves.main()


if __name__ == '__main__':
    main()
