# AirDNA v1 API (Legacy)

> Original API from 2018, now deprecated/gated

---

## v1 API Details
- **Host:** `https://api.airdna.co`
- **Auth:** `access_token` query parameter
- **Released:** March 1, 2018
- **Pricing:** Enterprise discounts for >5,000 calls/month
- **Status:** Deprecated/gated (apidocs.airdna.co returns minimal content)

## v1 Endpoints

### Property Valuations
| Endpoint | Description |
|---|---|
| Rentalizer | Annual & Monthly Revenue, ADR, Occupancy with up to 10 comps |
| Rentalizer Summary | Annual Revenue, ADR, Occupancy (lighter version) |
| Rentalizer Redirect | Redirect user into Rentalizer tab in MarketMinder |

### Listing Data
| Endpoint | Description |
|---|---|
| Comparable Properties | Property attributes & rental performance for up to 25 comps |
| Available | Properties available during a given time period |
| Single Property | Property attributes & rental performance for single listing |

### Market Data
| Endpoint | Description |
|---|---|
| Market Summary | Overview of market statistics for last calendar month |
| Future Daily | Daily rental supply and rates for next 6 months |
| Active Listings | Historical number of Active Listings by year/month |
| Occupancy | Historical Occupancy rates by bedroom count, month, year |
| ADR | Historical Average Daily Rates by bedroom count, month, year |
| RevPAR | Historical RevPAR by bedroom count, month, year |
| Revenue | Historical Revenue by bedroom count, month, year |

### Other
| Endpoint | Description |
|---|---|
| Property Availability | Availability and estimated price of single property |
| Smart Rates | Manage smart rates for a property |

## Known v1 URL Pattern
```
GET https://api.airdna.co/v1/market/property_list?access_token={token}&city_id={id}&start_month=5&start_year=2019&number_of_months=36&currency=native&show_regions=true
```

## v1 → v2 Migration
| Aspect | v1 | v2 |
|---|---|---|
| Auth | `access_token` query param | `Authorization: Bearer` header |
| Base URL | `/v1/...` | `/api/enterprise/v2/...` |
| Docs | Postman | Redocly/OpenAPI |
| Access | HAR capture possible | Sales-gated |

## Source Code (jayesh2278/airdnascraper)
```python
url = "https://api.airdna.co/v1/market/property_list?access_token=NjYwMTgw|a495e9b28dae4f76af7b8c3e2696cdc3&city_id=71282&start_month=5&start_year=2019&number_of_months=36&currency=native&show_regions=true"
```
Uses browser-like headers (Chrome UA, origin/referer spoofing). Iterates over `data["properties"]`.
