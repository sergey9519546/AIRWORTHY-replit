#!/usr/bin/env python3
"""One-off migration: add and backfill the listings.bathrooms column.

The listings table historically omitted bathroom counts even though the source
InsideAirbnb snapshots carry them (in the free-text `bathrooms_text` column).
This migration adds a `bathrooms REAL` column in place and backfills it from the
locally cached raw listings files, matched by (id, state, city, snapshot_date).

It is idempotent: re-running only refreshes values for rows it can match, and
never drops the listings table (which would wipe the separately-populated
demand_curve data).
"""
import csv
import gzip
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'airbnb.db')

sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from load_data import local_path, parse_bathrooms


def column_exists(conn, table, column):
    return any(r[1] == column for r in conn.execute(f'PRAGMA table_info({table})'))


def main():
    if not os.path.exists(DB_PATH):
        print(f'Database not found at {DB_PATH}')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    if not column_exists(conn, 'listings', 'bathrooms'):
        print('Adding bathrooms column ...')
        conn.execute('ALTER TABLE listings ADD COLUMN bathrooms REAL')
        conn.commit()
    else:
        print('bathrooms column already present')

    snapshots = conn.execute(
        'SELECT DISTINCT state, city, snapshot_date FROM listings'
    ).fetchall()

    total_updated = 0
    for state, city, date in snapshots:
        filepath = local_path(state, city, date, 'listings')
        if not os.path.exists(filepath):
            print(f'  SKIP {state}/{city}/{date}: raw file missing ({filepath})')
            continue

        updates = []
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                baths = parse_bathrooms(row.get('bathrooms_text', ''),
                                        row.get('bathrooms', ''))
                if baths is None:
                    continue
                updates.append((baths, row['id'], state, city, date))

        conn.executemany(
            'UPDATE listings SET bathrooms = ? '
            'WHERE id = ? AND state = ? AND city = ? AND snapshot_date = ?',
            updates,
        )
        conn.commit()
        total_updated += len(updates)
        print(f'  {state}/{city}/{date}: {len(updates):,} rows backfilled')

    filled = conn.execute(
        'SELECT COUNT(*) FROM listings WHERE bathrooms IS NOT NULL'
    ).fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    print(f'\nBackfilled {total_updated:,} rows; '
          f'{filled:,}/{total:,} listings now have a bathrooms value.')
    conn.close()


if __name__ == '__main__':
    main()
