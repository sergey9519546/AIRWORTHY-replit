# MVP Scope & Competitive Differentiation

> What to build first, how to beat AirDNA

---

## MVP Scope (Minimum Viable Product)

### Phase 1: Data Foundation (Weeks 1-2)
- [ ] Airbnb listing scraper (GraphQL shadow API)
- [ ] Calendar scraper (daily snapshots)
- [ ] Booking detection engine (calendar diff + heuristics)
- [ ] PostgreSQL database with listing/calendar/booking tables
- [ ] Basic data cleaning pipeline

### Phase 2: Core Analytics (Weeks 3-4)
- [ ] Per-listing metrics (occupancy, ADR, revenue)
- [ ] Market-level aggregation
- [ ] Comp selection algorithm
- [ ] Revenue estimation (Rentalizer clone)

### Phase 3: Product (Weeks 5-6)
- [ ] Search by address/market
- [ ] Map view (Mapbox)
- [ ] Listing detail view
- [ ] Market overview dashboard
- [ ] Basic pricing (free tier + paid)

### What's NOT in MVP
- ❌ Vrbo/Booking.com integration
- ❌ Dynamic pricing recommendations
- ❌ Cross-platform matching
- ❌ Historical data (starts from day 1)
- ❌ API access
- ❌ Mobile app

---

## Competitive Differentiation

### Where AirDNA is Weak

| Weakness | Our Advantage |
|---|---|
| **Opaque methodology** | Transparent algorithms, explainable scores |
| **Optimistic estimates** | Conservative estimates with clear confidence intervals |
| **Stale data (daily)** | Real-time or near-real-time updates |
| **Expensive ($20-120/mo)** | Cheaper or free tier |
| **No API self-service** | Self-service API from day 1 |
| **Enterprise focus** | Individual investor focus |
| **Complex UI** | Simple, clean interface |
| **No mobile app** | Mobile-first design |

### Our Unique Selling Points

1. **Transparency** — Show exactly how estimates are calculated
2. **Confidence Intervals** — Always show range, not single number
3. **Real-Time Data** — Update more frequently than daily
4. **Affordable** — $5-15/mo or free tier with more data
5. **API-First** — Self-service API for developers
6. **Modern UX** — Clean, fast, mobile-friendly

### What AirDNA Does Well (Don't Try to Beat)
- 10+ years of historical data
- 16M listings tracked
- Institutional trust (banks use it)
- Brand recognition
- Enterprise sales team

### Our Target Customer
- Individual STR investors
- New hosts evaluating markets
- Small property managers (1-20 units)
- Developers building STR tools
- Real estate agents

---

## Pricing Strategy

| Tier | Price | Features |
|---|---|---|
| **Free** | $0 | Basic market stats, 5 property lookups/month |
| **Starter** | $9/mo | Unlimited lookups, revenue estimates, comps |
| **Pro** | $29/mo | Historical data, API access, exports |
| **Team** | $79/mo | Multi-user, custom reports, priority support |

### Why Cheaper Than AirDNA
- No enterprise sales overhead
- Automated data collection (no manual QA)
- Cloud-native infrastructure
- Focus on self-service

---

## Go-to-Market Strategy

1. **Launch on Product Hunt** — Get initial users
2. **Content Marketing** — Blog posts about STR investing
3. **Reddit/Forum Presence** — r/AirBnB, r/realestateinvesting
4. **SEO** — Target "airbnb revenue calculator" keywords
5. **Partnerships** — Integrate with property management tools
6. **API Marketplace** — List on RapidAPI for developers
