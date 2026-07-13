#!/usr/bin/env python3
"""
Derive a REAL month-by-month demand signal for each map listing.

The map's "Demand" layer previously colored listings by lifetime review count as
a rough proxy. This script replaces that proxy with a genuine seasonal booking
signal derived from InsideAirbnb's per-listing forward availability calendar
(calendar.csv.gz): for each future date, `available = f` means the night is
booked or blocked. Aggregating booked-share by calendar month yields a real
12-value seasonal demand curve per listing.

To avoid bloating the database with tens of millions of raw calendar rows, we do
NOT store the calendar itself. We stream it, aggregate to a compact 12-number
curve per listing, and store that JSON on a new `listings.demand_curve` column.

Storage: `listings.demand_curve` = JSON array of 12 floats in [0,1], index 0=Jan
... 11=Dec, each = booked nights / total scheduled nights for that calendar month
(combined across all calendar years the snapshot spans). NULL when the listing is
absent from the calendar file.

Idempotent: re-running re-derives and overwrites the column.
"""
import csv
import gzip
import io
import json
import os
import sqlite3
import sys
import tempfile
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'airbnb.db')

# Download calendars to a scratch dir (NOT under the repo) so the large gz files
# are never committed. Aggregation keeps only the compact curves.
SCRATCH_DIR = os.path.join(tempfile.gettempdir(), 'airworthy_calendars')


def url_for(state, city, date):
    return (
        f"https://data.insideairbnb.com/united-states/{state}/{city}/{date}"
        f"/data/calendar.csv.gz"
    )


def latest_snapshots(conn):
    """The (state, city, snapshot_date) actually loaded into the map DB.

    Mirrors /api/listings' "latest snapshot per city" contract so the curves
    line up exactly with the rows the map renders.
    """
    rows = conn.execute(
        """
        SELECT state, city, MAX(snapshot_date) AS snapshot_date
        FROM listings
        GROUP BY state, city
        ORDER BY state, city
        """
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def download_calendar(state, city, date):
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    path = os.path.join(SCRATCH_DIR, f"{state}_{city}_{date}_calendar.csv.gz")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"  [cached] {path}")
        return path
    url = url_for(state, city, date)
    print(f"  [downloading] {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(path, 'wb') as f:
        f.write(data)
    return path


def aggregate_curves(path):
    """Stream one calendar file → {listing_id: [12 booked], [12 total]}.

    Returns {listing_id: [float or None]*12} booked-share curve.
    """
    booked = defaultdict(lambda: [0] * 12)
    total = defaultdict(lambda: [0] * 12)

    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lid_raw = row.get('listing_id', '')
            date = row.get('date', '')
            if not lid_raw or len(date) < 7:
                continue
            try:
                lid = int(lid_raw)
                month_idx = int(date[5:7]) - 1
            except ValueError:
                continue
            if month_idx < 0 or month_idx > 11:
                continue
            total[lid][month_idx] += 1
            # InsideAirbnb: available 't' = free night, 'f' = booked/blocked.
            if (row.get('available', '') or '').strip().lower() == 'f':
                booked[lid][month_idx] += 1

    curves = {}
    for lid, tot in total.items():
        bkd = booked[lid]
        curve = []
        for m in range(12):
            if tot[m] > 0:
                curve.append(round(bkd[m] / tot[m], 4))
            else:
                curve.append(None)
        curves[lid] = curve
    return curves


def ensure_column(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(listings)").fetchall()]
    if 'demand_curve' not in cols:
        print("Adding listings.demand_curve column ...")
        conn.execute("ALTER TABLE listings ADD COLUMN demand_curve TEXT")
        conn.commit()


def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    ensure_column(conn)

    snapshots = latest_snapshots(conn)
    print("=" * 60)
    print(f"Deriving demand curves for {len(snapshots)} city snapshots")
    print("=" * 60)

    grand_total = 0
    for state, city, date in snapshots:
        print(f"\n--- {state}/{city} @ {date} ---")
        try:
            path = download_calendar(state, city, date)
        except Exception as e:
            print(f"  ERROR downloading calendar, skipping: {e}")
            continue

        curves = aggregate_curves(path)
        print(f"  aggregated curves for {len(curves):,} listings")

        # Update only rows for this snapshot; match on the Airbnb listing id.
        updates = []
        for lid, curve in curves.items():
            updates.append((json.dumps(curve), lid, state, city, date))

        conn.executemany(
            """
            UPDATE listings
            SET demand_curve = ?
            WHERE id = ? AND state = ? AND city = ? AND snapshot_date = ?
            """,
            updates,
        )
        conn.commit()
        matched = conn.execute(
            """
            SELECT COUNT(*) FROM listings
            WHERE state = ? AND city = ? AND snapshot_date = ?
              AND demand_curve IS NOT NULL
            """,
            (state, city, date),
        ).fetchone()[0]
        print(f"  matched {matched:,} listing rows in DB")
        grand_total += matched

    covered = conn.execute(
        "SELECT COUNT(*) FROM listings WHERE demand_curve IS NOT NULL"
    ).fetchone()[0]
    total_rows = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    print("\n" + "=" * 60)
    print(f"Demand curves populated for {covered:,} / {total_rows:,} listings")
    print("=" * 60)

    # Coverage check scoped to the *latest* snapshot per city — this is what
    # the map actually renders (see /api/listings), so a gap here means the
    # Demand layer will look blank/wrong for that city right now, not just
    # for stale historical rows we don't care about.
    gaps = conn.execute(
        """
        SELECT l.state, l.city, l.snapshot_date,
               COUNT(*) AS total, SUM(CASE WHEN l.demand_curve IS NULL THEN 1 ELSE 0 END) AS missing
        FROM listings l
        JOIN (
            SELECT state, city, MAX(snapshot_date) AS snapshot_date
            FROM listings GROUP BY state, city
        ) latest
          ON l.state = latest.state AND l.city = latest.city AND l.snapshot_date = latest.snapshot_date
        GROUP BY l.state, l.city, l.snapshot_date
        HAVING missing > 0
        """
    ).fetchall()
    if gaps:
        print("\nWARNING: the following current-snapshot cities are missing demand curves")
        print("(their map Demand layer will look blank/wrong until this is fixed):")
        for state, city, date, total_n, missing_n in gaps:
            print(f"  - {state}/{city} @ {date}: {missing_n:,} / {total_n:,} listings missing demand_curve")
    conn.close()


if __name__ == '__main__':
    main()
