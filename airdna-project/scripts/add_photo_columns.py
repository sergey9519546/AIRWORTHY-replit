#!/usr/bin/env python3
"""One-off migration: add and backfill the listings.picture_url / listing_url columns.

The listings table historically dropped the real listing photo (`picture_url`)
and its source page (`listing_url`) even though every InsideAirbnb snapshot
carries both. This migration adds the two TEXT columns in place and backfills
them from the locally cached raw listings files, matched by
(id, state, city, snapshot_date).

It is idempotent: re-running only refreshes values for rows it can match, and
never drops the listings table (which would wipe the separately-populated
demand_curve data). Modeled on add_bathrooms_column.py.
"""
import csv
import gzip
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'airbnb.db')

sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from load_data import local_path


def column_exists(conn, table, column):
    return any(r[1] == column for r in conn.execute(f'PRAGMA table_info({table})'))


def main():
    if not os.path.exists(DB_PATH):
        print(f'Database not found at {DB_PATH}')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    for column in ('picture_url', 'listing_url'):
        if not column_exists(conn, 'listings', column):
            print(f'Adding {column} column ...')
            conn.execute(f'ALTER TABLE listings ADD COLUMN {column} TEXT')
            conn.commit()
        else:
            print(f'{column} column already present')

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
                picture_url = (row.get('picture_url') or '').strip() or None
                listing_url = (row.get('listing_url') or '').strip() or None
                if picture_url is None and listing_url is None:
                    continue
                updates.append((picture_url, listing_url, row['id'], state, city, date))

        conn.executemany(
            'UPDATE listings SET picture_url = ?, listing_url = ? '
            'WHERE id = ? AND state = ? AND city = ? AND snapshot_date = ?',
            updates,
        )
        conn.commit()
        total_updated += len(updates)
        print(f'  {state}/{city}/{date}: {len(updates):,} rows backfilled')

    filled = conn.execute(
        'SELECT COUNT(*) FROM listings WHERE picture_url IS NOT NULL'
    ).fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    print(f'\nBackfilled {total_updated:,} rows; '
          f'{filled:,}/{total:,} listings now have a picture_url.')
    conn.close()


if __name__ == '__main__':
    main()
