#!/usr/bin/env python3
"""
Load InsideAirbnb data into SQLite database.
Supports multiple regions (states), cities, and snapshot dates.
"""
import csv
import gzip
import os
import re
import sqlite3
import sys
import urllib.request
import concurrent.futures
from pathlib import Path

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'airbnb.db')
DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')

# Snapshots to download/load: (state, city, date)
SNAPSHOTS = [
    # California
    ('ca', 'los-angeles', '2026-04-14'),
    ('ca', 'los-angeles', '2026-06-15'),
    ('ca', 'oakland', '2026-05-27'),
    ('ca', 'oakland', '2026-06-27'),
    ('ca', 'pacific-grove', '2026-05-14'),
    ('ca', 'pacific-grove', '2026-06-14'),
    ('ca', 'san-diego', '2026-05-27'),
    ('ca', 'san-diego', '2026-06-27'),
    ('ca', 'san-francisco', '2026-04-14'),
    ('ca', 'san-francisco', '2026-05-14'),
    ('ca', 'san-francisco', '2026-06-14'),
    ('ca', 'san-mateo-county', '2026-05-27'),
    ('ca', 'san-mateo-county', '2026-06-27'),
    ('ca', 'santa-clara-county', '2026-06-28'),
    ('ca', 'santa-cruz-county', '2026-06-30'),
    # Florida
    ('fl', 'broward-county', '2026-06-29'),
]


def url_for(state, city, date, filename):
    """Build InsideAirbnb data URL."""
    return (
        f"https://data.insideairbnb.com/united-states/{state}/{city}/{date}"
        f"/data/{filename}.csv.gz"
    )


def local_path(state, city, date, filename):
    """Local path for a downloaded file."""
    return os.path.join(DATA_DIR, state, city, date, f"{filename}.csv.gz")


def ensure_dirs():
    """Create data directory tree."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def download_file(state, city, date, filename):
    """Download a single file if not already present."""
    url = url_for(state, city, date, filename)
    path = local_path(state, city, date, filename)
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

    if os.path.exists(path):
        print(f"  [cached] {path}")
        return path

    print(f"  [downloading] {url}")
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as e:
        print(f"  ERROR downloading {url}: {e}")
        if os.path.exists(path):
            os.remove(path)
        raise
    return path


def download_all(snapshots):
    """Download all snapshot files in parallel."""
    tasks = []
    for state, city, date in snapshots:
        for filename in ['listings', 'calendar', 'reviews']:
            tasks.append((state, city, date, filename))

    print(f"Downloading {len(tasks)} files...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(download_file, s, c, d, f) for s, c, d, f in tasks]
        for future in concurrent.futures.as_completed(futures):
            future.result()  # raise exceptions if any


def parse_price(price_str):
    """Parse price string like '$113.97' to float."""
    if not price_str:
        return None
    try:
        return float(price_str.replace('$', '').replace(',', ''))
    except ValueError:
        return None


def parse_bool(val):
    """Convert 't'/'f' to 1/0."""
    if val is None or val == '':
        return None
    return 1 if val.lower() == 't' else 0


def parse_int(val):
    """Parse integer, return None if empty."""
    if val is None or val == '':
        return None
    try:
        return int(val)
    except ValueError:
        return None


def parse_float(val):
    """Parse float, return None if empty."""
    if val is None or val == '':
        return None
    try:
        return float(val)
    except ValueError:
        return None


def parse_bathrooms(text_val, num_val):
    """Derive a numeric bathroom count.

    InsideAirbnb's numeric `bathrooms` column is frequently blank, so we prefer
    the leading number in the free-text `bathrooms_text` (e.g. "1.5 baths",
    "1 shared bath", "Half-bath") and fall back to the numeric column.
    """
    if text_val:
        t = text_val.strip().lower()
        if t.startswith('half'):
            return 0.5
        m = re.match(r'\s*([0-9]+(?:\.[0-9]+)?)', t)
        if m:
            return float(m.group(1))
    return parse_float(num_val)


# Columns we extract from listings.csv (in order matching our schema)
LISTINGS_COLUMNS = [
    'id', 'name', 'description', 'host_id', 'host_name', 'host_since',
    'host_is_superhost', 'host_listings_count', 'host_identity_verified',
    'neighbourhood_cleansed', 'neighbourhood_group_cleansed',
    'latitude', 'longitude', 'property_type', 'room_type',
    'accommodates', 'bedrooms', 'beds', 'price',
    'minimum_nights', 'maximum_nights',
    'number_of_reviews', 'number_of_reviews_ltm', 'number_of_reviews_l30d',
    'first_review', 'last_review',
    'review_scores_rating', 'review_scores_accuracy', 'review_scores_cleanliness',
    'review_scores_checkin', 'review_scores_communication',
    'review_scores_location', 'review_scores_value',
    'instant_bookable', 'calculated_host_listings_count',
    'availability_30', 'availability_60', 'availability_90', 'availability_365',
    'estimated_occupancy_l365d', 'estimated_revenue_l365d',
    'amenities'
]


INT_COLUMNS = {
    'id', 'host_id', 'accommodates', 'beds', 'minimum_nights', 'maximum_nights',
    'number_of_reviews', 'number_of_reviews_ltm', 'number_of_reviews_l30d',
    'instant_bookable', 'calculated_host_listings_count',
    'availability_30', 'availability_60', 'availability_90', 'availability_365',
    'estimated_occupancy_l365d',
}

FLOAT_COLUMNS = {
    'latitude', 'longitude', 'bedrooms',
    'review_scores_rating', 'review_scores_accuracy', 'review_scores_cleanliness',
    'review_scores_checkin', 'review_scores_communication', 'review_scores_location',
    'review_scores_value', 'estimated_revenue_l365d',
}

BOOL_COLUMNS = {'host_is_superhost', 'host_identity_verified'}


def load_listings(conn, state, city, date):
    """Load listings.csv.gz for one snapshot."""
    filepath = local_path(state, city, date, 'listings')
    print(f"Loading listings: {state}/{city}/{date} ...")

    col_names = ['state', 'city', 'snapshot_date'] + LISTINGS_COLUMNS + ['price_numeric', 'bathrooms']
    placeholders = ', '.join(['?' for _ in col_names])
    insert_sql = f"INSERT INTO listings ({', '.join(col_names)}) VALUES ({placeholders})"

    count = 0
    errors = 0
    batch = []

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                values = [state, city, date]
                for col in LISTINGS_COLUMNS:
                    val = row.get(col, '')
                    values.append(None if val == '' else val)

                # Parse numeric/bool fields
                for i, col in enumerate(LISTINGS_COLUMNS, start=3):
                    if col in INT_COLUMNS:
                        values[i] = parse_int(values[i])
                    elif col in FLOAT_COLUMNS:
                        values[i] = parse_float(values[i])
                    elif col in BOOL_COLUMNS:
                        values[i] = parse_bool(values[i])

                # Add parsed price
                price_numeric = parse_price(row.get('price', ''))
                values.append(price_numeric)

                # Bathroom count. InsideAirbnb's numeric `bathrooms` column is
                # frequently blank, so prefer the more-complete free-text
                # `bathrooms_text` (e.g. "1.5 baths", "1 shared bath") and fall
                # back to the numeric column.
                values.append(parse_bathrooms(row.get('bathrooms_text', ''),
                                              row.get('bathrooms', '')))

                batch.append(values)
                count += 1

                if len(batch) >= 1000:
                    conn.executemany(insert_sql, batch)
                    batch = []
                    if count % 10000 == 0:
                        print(f"  ... {count:,} listings loaded")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  Warning: Error processing listing {row.get('id', '?')}: {e}")

        if batch:
            conn.executemany(insert_sql, batch)

    conn.commit()
    print(f"  Loaded {count:,} listings ({errors} errors)")
    return count


def load_calendar(conn, state, city, date):
    """Load calendar.csv.gz for one snapshot."""
    filepath = local_path(state, city, date, 'calendar')
    print(f"Loading calendar: {state}/{city}/{date} ...")

    insert_sql = """
        INSERT INTO calendar (listing_id, state, city, snapshot_date, date, available, minimum_nights, maximum_nights)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    count = 0
    batch = []

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listing_id = parse_int(row.get('listing_id', ''))
            d = row.get('date', '')
            available = parse_bool(row.get('available', ''))
            min_nights = parse_int(row.get('minimum_nights', ''))
            max_nights = parse_int(row.get('maximum_nights', ''))

            batch.append((listing_id, state, city, date, d, available, min_nights, max_nights))
            count += 1

            if len(batch) >= 10000:
                conn.executemany(insert_sql, batch)
                batch = []
                if count % 500000 == 0:
                    print(f"  ... {count:,} calendar rows loaded")

    if batch:
        conn.executemany(insert_sql, batch)

    conn.commit()
    print(f"  Loaded {count:,} calendar rows")
    return count


def load_reviews(conn, state, city, date):
    """Load reviews.csv.gz for one snapshot."""
    filepath = local_path(state, city, date, 'reviews')
    print(f"Loading reviews: {state}/{city}/{date} ...")

    insert_sql = """
        INSERT INTO reviews (listing_id, state, city, snapshot_date, date, reviewer_id, reviewer_name, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    count = 0
    batch = []

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listing_id = parse_int(row.get('listing_id', ''))
            d = row.get('date', '')
            reviewer_id = parse_int(row.get('reviewer_id', ''))
            reviewer_name = row.get('reviewer_name', '')
            comments = row.get('comments', '')

            batch.append((listing_id, state, city, date, d, reviewer_id, reviewer_name, comments))
            count += 1

            if len(batch) >= 10000:
                conn.executemany(insert_sql, batch)
                batch = []
                if count % 200000 == 0:
                    print(f"  ... {count:,} reviews loaded")

    if batch:
        conn.executemany(insert_sql, batch)

    conn.commit()
    print(f"  Loaded {count:,} reviews")
    return count


def load_snapshot(conn, state, city, date):
    """Load one full snapshot."""
    listings_count = load_listings(conn, state, city, date)
    calendar_count = load_calendar(conn, state, city, date)
    reviews_count = load_reviews(conn, state, city, date)
    return listings_count, calendar_count, reviews_count


def main():
    """Main entry point."""
    # Check database
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("Run create_database.py first!")
        sys.exit(1)

    ensure_dirs()

    # Download all files first
    download_all(SNAPSHOTS)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    print("=" * 60)
    print("Loading InsideAirbnb Data")
    print("=" * 60)

    total_listings = 0
    total_calendar = 0
    total_reviews = 0

    for state, city, date in SNAPSHOTS:
        print(f"\n--- {state}/{city} @ {date} ---")
        l, c, r = load_snapshot(conn, state, city, date)
        total_listings += l
        total_calendar += c
        total_reviews += r

    # Verify counts
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM listings")
    db_listings = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM calendar")
    db_calendar = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reviews")
    db_reviews = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print("Loading Complete!")
    print("=" * 60)
    print(f"Snapshots loaded: {len(SNAPSHOTS)}")
    print(f"Total listings: {total_listings:,}")
    print(f"Total calendar: {total_calendar:,}")
    print(f"Total reviews:  {total_reviews:,}")
    print(f"\nDatabase verification:")
    print(f"  listings in DB: {db_listings:,}")
    print(f"  calendar in DB: {db_calendar:,}")
    print(f"  reviews in DB:  {db_reviews:,}")

    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
