---
name: Rentalizer Realie parcel enrichment
description: How real assessor/parcel data (owner, year built, AVM, lot size) is wired into the revenue estimate via Realie.ai.
---

## What it is
`src/realie_client.py` calls Realie's Property Data API (`GET
https://app.realie.ai/api/public/property/location/`, header
`Authorization: <raw key>` — no "Bearer" prefix) to enrich `/v1/estimate` with
real parcel/assessor data: year built, lot acres, building sqft, bedrooms/
bathrooms (assessor record, not the user's input), owner name, assessed value,
AVM (`modelValue` + min/max range), and last sale price/date. Wired in
additively as `EstimateResponse.parcel` (nullable) — chosen by the user
explicitly as "enrich the report with parcel data" over geocoding-replacement
or AVM-cross-check alternatives.

## Non-obvious API behavior (verified live, not just from docs)
- **Radius must be ≥ ~0.1 miles.** Anything ≤0.05mi frequently returns `404
  {"error":"No properties found"}` even directly over a real parcel — Location
  Search isn't a point-in-polygon parcel lookup, it's a radius search, and
  geocoding imprecision + parcel-centroid offsets need room. 0.1mi is the
  working value; results are NOT sorted by distance, so the client haversine-
  sorts the returned candidates and picks the nearest to the exact query point.
- Auth failures are `401`/`403` (bad key / usage cap), not the request itself
  erroring — treat both as "disable enrichment for now", not a crash.
- Date fields like `transferDate` are `YYYYMMDD` strings, not ISO — despite the
  docs example showing hyphens.
- **"Not recorded" comes back as `0`/`0.0`, not null,** for numeric measurement
  fields (buildingArea, totalBedrooms, totalBathrooms, totalMarketValue, etc.).
  A parcel can return a valid `parcelId`/`ownerName`/AVM while every physical
  measurement is 0. When displaying these, require a *positive* value before
  showing one — otherwise the report prints misleading "0 sq ft" / "$0" facts.

## Why fail-open matters here
Realie coverage/uptime must never gate the core revenue estimate (the
product's actual value prop). `get_parcel()` returns `None` for: no API key
configured, any HTTP error, any network/timeout exception, or no parcel found
— never raises. Mirrors the existing Mapbox→Nominatim fail-open pattern in
`geocoder.py`.

## How to apply
- To surface parcel data in the UI (property report, map inspector), read
  `EstimateResponse.parcel` — it's already on the wire, additive, and null-safe.
- `owner_name` is included by design (explicit user ask) — it's public assessor
  record data tied to the property, same as what county assessor sites/Zillow
  already show, not sensitive user data.
