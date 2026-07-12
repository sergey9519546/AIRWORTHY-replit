#!/usr/bin/env python3
"""
Validate the loaded data and print a quality report.
Run this after load_data.py to verify everything loaded correctly.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'airbnb.db')


def run_query(conn, sql, params=None):
    """Run a query and return results."""
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    return cursor.fetchall()


def validate_data():
    """Run validation checks and print report."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    print("=" * 60)
    print("DATA VALIDATION REPORT")
    print("=" * 60)

    # 1. Basic counts
    print("\n1. TABLE COUNTS")
    print("-" * 40)
    for table in ['listings', 'calendar', 'reviews']:
        rows = run_query(conn, f"SELECT COUNT(*) FROM {table}")[0][0]
        print(f"  {table:12} {rows:>12,} rows")

    # 2. Snapshots loaded
    print("\n2. SNAPSHOTS LOADED")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT state, city, snapshot_date, COUNT(*) as cnt
        FROM listings
        GROUP BY state, city, snapshot_date
        ORDER BY state, city, snapshot_date
    """)
    print(f"  {'State':6} {'City':20} {'Date':12} {'Listings':>12}")
    for state, city, date, count in rows:
        print(f"  {state:6} {city:20} {date:12} {count:>12,}")

    # 3. Listings by region
    print("\n3. LISTINGS BY REGION")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT COALESCE(neighbourhood_group_cleansed, 'N/A') as borough, COUNT(*) as cnt
        FROM listings
        GROUP BY neighbourhood_group_cleansed
        ORDER BY cnt DESC
    """)
    for borough, count in rows:
        print(f"    {borough:30} {count:>10,}")

    # 4. Room type distribution
    print("\n4. ROOM TYPE DISTRIBUTION")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT room_type, COUNT(*) as cnt,
               ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 1) as pct
        FROM listings
        GROUP BY room_type
        ORDER BY cnt DESC
    """)
    for room_type, count, pct in rows:
        print(f"    {room_type:25} {count:>8,} ({pct}%)")

    # 5. Data quality checks
    print("\n5. DATA QUALITY CHECKS")
    print("-" * 40)

    # Duplicate IDs (per snapshot should be 0)
    dups = run_query(conn, """
        SELECT COUNT(*) FROM (
            SELECT id, city, snapshot_date, COUNT(*) as cnt
            FROM listings
            GROUP BY id, city, snapshot_date
            HAVING cnt > 1
        )
    """)[0][0]
    print(f"  Duplicate listing IDs per snapshot: {dups} {'✓' if dups == 0 else '✗'}")

    # Null prices
    null_prices = run_query(conn, """
        SELECT COUNT(*) FROM listings WHERE price IS NULL OR price = ''
    """)[0][0]
    print(f"  Null/empty prices: {null_prices} {'✓' if null_prices == 0 else '⚠'}")

    # Unparseable prices
    bad_prices = run_query(conn, """
        SELECT COUNT(*) FROM listings WHERE price_numeric IS NULL AND price IS NOT NULL AND price != ''
    """)[0][0]
    print(f"  Unparseable prices: {bad_prices} {'✓' if bad_prices == 0 else '⚠'}")

    # Zero reviews
    zero_reviews = run_query(conn, """
        SELECT COUNT(*) FROM listings WHERE number_of_reviews = 0
    """)[0][0]
    total = run_query(conn, "SELECT COUNT(*) FROM listings")[0][0]
    pct = round(100.0 * zero_reviews / total, 1) if total > 0 else 0
    print(f"  Listings with 0 reviews: {zero_reviews:,} ({pct}%)")

    # Missing coordinates
    missing_coords = run_query(conn, """
        SELECT COUNT(*) FROM listings WHERE latitude IS NULL OR longitude IS NULL
    """)[0][0]
    print(f"  Missing coordinates: {missing_coords} {'✓' if missing_coords == 0 else '⚠'}")

    # 6. Price statistics
    print("\n6. PRICE STATISTICS")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT
            ROUND(MIN(price_numeric), 2) as min_price,
            ROUND(AVG(price_numeric), 2) as avg_price,
            ROUND(MAX(price_numeric), 2) as max_price,
            COUNT(*) as valid_prices
        FROM listings
        WHERE price_numeric > 0
    """)
    if rows:
        min_p, avg_p, max_p, valid = rows[0]
        print(f"  Valid prices: {valid:,}")
        print(f"  Min: ${min_p:,.2f}")
        print(f"  Avg: ${avg_p:,.2f}")
        print(f"  Max: ${max_p:,.2f}")

    # 7. Calendar overview
    print("\n7. CALENDAR OVERVIEW")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT
            MIN(date) as earliest,
            MAX(date) as latest,
            COUNT(DISTINCT listing_id) as listings,
            ROUND(100.0 * SUM(CASE WHEN available = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as avail_pct
        FROM calendar
    """)
    if rows and rows[0][0] is not None:
        earliest, latest, listings, avail_pct = rows[0]
        print(f"  Date range: {earliest} to {latest}")
        print(f"  Listings with calendar: {listings:,}")
        print(f"  Availability rate: {avail_pct}%")
    else:
        print("  No calendar data loaded (load full snapshots with load_data.py)")

    # 8. Reviews overview
    print("\n8. REVIEWS OVERVIEW")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT
            MIN(date) as earliest,
            MAX(date) as latest,
            COUNT(DISTINCT listing_id) as listings,
            COUNT(*) as total_reviews
        FROM reviews
    """)
    if rows and rows[0][0] is not None:
        earliest, latest, listings, total = rows[0]
        print(f"  Date range: {earliest} to {latest}")
        print(f"  Listings with reviews: {listings:,}")
        print(f"  Total reviews: {total:,}")
    else:
        print("  No reviews data loaded (load full snapshots with load_data.py)")

    # 9. Revenue estimates by state and city
    print("\n9. REVENUE ESTIMATES BY STATE/CITY")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT
            state,
            city,
            snapshot_date,
            COUNT(*) as listings,
            ROUND(AVG(estimated_revenue_l365d), 0) as avg_revenue,
            ROUND(AVG(estimated_occupancy_l365d), 0) as avg_occupancy
        FROM listings
        WHERE estimated_revenue_l365d > 0
        GROUP BY state, city, snapshot_date
        ORDER BY state, city, snapshot_date
    """)
    print(f"  {'State':6} {'City':20} {'Date':12} {'Listings':>10} {'Avg Revenue':>12} {'Avg Occupancy':>14}")
    for state, city, date, listings, avg_rev, avg_occ in rows:
        print(f"  {state:6} {city:20} {date:12} {listings:>10,} ${avg_rev:>10,.0f} {avg_occ:>12,.0f} days")

    # 10. Index verification
    print("\n10. INDEXES")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT name FROM sqlite_master
        WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    for (name,) in rows:
        print(f"  ✓ {name}")

    # 11. Views verification
    print("\n11. VIEWS")
    print("-" * 40)
    rows = run_query(conn, """
        SELECT name FROM sqlite_master
        WHERE type = 'view'
        ORDER BY name
    """)
    for (name,) in rows:
        print(f"  ✓ {name}")

    conn.close()

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    validate_data()
