# Infrastructure & Scale

> How to run this at scale

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              SCHEDULER (cron)                │
│  Daily: scrape calendars for all listings    │
│  Weekly: discover new listings               │
│  Monthly: compute market aggregations        │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────▼───────────┐
       │   SCRAPING WORKERS    │
       │  Playwright + CDP     │
       │  Anti-bot bypass      │
       │  Proxy rotation       │
       │  Rate limiting        │
       └───────────┬───────────┘
                   │
       ┌───────────▼───────────┐
       │   DATA PIPELINE       │
       │  Parse GraphQL resp   │
       │  Calendar diff        │
       │  Booking inference    │
       │  Anomaly detection    │
       └───────────┬───────────┘
                   │
       ┌───────────▼───────────┐
       │   DATABASE            │
       │  PostgreSQL + PostGIS │
       │  TimescaleDB          │
       │  Redis (cache)        │
       └───────────┬───────────┘
                   │
       ┌───────────▼───────────┐
       │   API + DASHBOARD     │
       │  FastAPI backend      │
       │  React frontend       │
       │  Mapbox maps          │
       └───────────────────────┘
```

## Database

### PostgreSQL + PostGIS
- Geospatial queries for proximity-based comp selection
- `ST_DWithin()` for radius searches
- `ST_Distance()` for distance calculations

### TimescaleDB
- Time-series optimization for calendar snapshots
- Automatic partitioning by time
- Efficient aggregation queries

### Redis
- Cache GraphQL responses (TTL: 1 hour for pricing, 24h for listing metadata)
- Rate limiting state
- Session management

## Proxy Strategy

| Provider | Type | Use Case |
|---|---|---|
| Bright Data | Residential | Airbnb scraping |
| Oxylabs | Residential | Vrbo scraping |
| Smartproxy | Datacenter | Booking.com |
| Self-hosted | Rotating | Fallback |

- Rotate proxies per request
- Session-based proxies for authenticated endpoints
- 1 request per 2-3 seconds per proxy

## Scraping Schedule

| Task | Frequency | Listings | Est. Time |
|---|---|---|---|
| Calendar snapshots | Daily | All tracked | 2-4 hours |
| New listing discovery | Weekly | Per market | 1-2 hours |
| Listing metadata refresh | Monthly | All | 4-8 hours |
| Market aggregation | Monthly | All markets | 30 min |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Frontend | React + TypeScript |
| Database | PostgreSQL + PostGIS + TimescaleDB |
| Cache | Redis |
| Maps | Mapbox GL JS |
| Scraping | Playwright + CDP |
| Queue | Celery + Redis |
| Hosting | AWS / GCP |
| CDN | Cloudflare |

## Cost Estimates (Monthly)

| Item | Cost |
|---|---|
| Proxy service | $200-500 |
| Database (managed) | $50-200 |
| Compute (scraping) | $100-300 |
| Mapbox | $0-50 |
| Total | $350-1,050 |
