---
name: Rentalizer geocoder listings-DB fallback
description: Why the geocoder falls back to the local listings database when Mapbox/Nominatim fail, and how to keep it safe.
---

Users frequently paste an Airbnb/Vrbo listing title into the address box on
the homepage or property report. External geocoders (Mapbox `types=address`,
Nominatim `country_codes=us`) are tuned for street addresses and routinely fail
on titles like `"Seascape Ocean View Hideaway 760"`. Because the app already
loads those listings into `db/airbnb.db` with `name`, `latitude`, and
`longitude`, the geocoder uses an exact, case-insensitive match against
`listings.name` as a final fallback before giving up.

**Why:** this is the fastest, most accurate fix for the common failure mode
"I pasted the listing name and it couldn't geocode." It reuses data we already
have, returns the same coordinates we use for comps, and degrades gracefully
when the DB is missing or the name isn't found.

**How to apply:**
- The fallback lives in `src/geocoder.py` as `_geocode_listings_db()` and is
  called from `geocode()` only after Mapbox and Nominatim both return nothing.
- It opens a fresh SQLite connection per call with `check_same_thread=False`,
  so the geocoder stays thread-safe even though SQLite connections can't be
  shared across threads.
- It only matches `LOWER(name) = ?` exactly (case-insensitive). Avoid broader
  `LIKE` or fuzzy matching: a title substring can match many listings and send
  the user to the wrong location.
- The returned `GeocodeResult.source` is `"listings_db"` so logs/metrics can
  distinguish it from `mapbox`/`nominatim`.
- Keep the DB path in sync with `src/api.py` and `src/amenity_calibration.py`
  (all three point at `db/airbnb.db`). If the path ever changes, update all
  `_db_path()` helpers together.
