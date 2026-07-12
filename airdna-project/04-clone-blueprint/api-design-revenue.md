# Our API Design & Revenue Model

> What endpoints to expose, how to monetize

---

## API Design

### Base URL
```
https://api.ourproduct.com/v1/
```

### Authentication
```
Authorization: Bearer <API_KEY>
```

### Endpoints

#### Markets
```
GET  /markets                        — List markets
GET  /markets/{id}                   — Market details
GET  /markets/{id}/metrics           — Market metrics (occupancy, ADR, revenue)
GET  /markets/{id}/listings          — Listings in market
GET  /markets/{id}/trends            — Historical trends
```

#### Listings
```
GET  /listings/{id}                  — Listing details
GET  /listings/{id}/metrics          — Historical metrics
GET  /listings/{id}/calendar         — Availability calendar
GET  /listings/{id}/comps            — Comparable listings
GET  /listings/{id}/revenue-estimate — Revenue projection
```

#### Search
```
POST /search                         — Search listings by location, filters
POST /search/by-coordinates          — Search by lat/lng + radius
POST /search/by-map-bounds           — Search by bounding box
```

#### Revenue Estimation
```
POST /rentalizer/estimate            — Estimate revenue for any address
POST /rentalizer/bulk                — Bulk estimates
```

#### Analytics
```
GET  /analytics/occupancy            — Occupancy data
GET  /analytics/revenue              — Revenue data
GET  /analytics/adr                  — ADR data
GET  /analytics/seasonality          — Seasonality patterns
```

### Response Format
```json
{
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  },
  "links": {
    "self": "/listings?page=1",
    "next": "/listings?page=2"
  }
}
```

---

## Revenue Model

### Option 1: Subscription (Recommended)
- Monthly/annual plans
- Tiered by features and usage
- Predictable revenue
- Easy to implement

### Option 2: Usage-Based
- Per API call pricing
- Pay-as-you-go
- Good for developers
- Harder to predict revenue

### Option 3: Hybrid
- Base subscription + overage charges
- Best of both worlds
- More complex billing

### Recommended: Subscription + API Overage

| Tier | Monthly | Included API Calls | Overage |
|---|---|---|---|
| Free | $0 | 100 | N/A |
| Starter | $9 | 1,000 | $0.01/call |
| Pro | $29 | 10,000 | $0.005/call |
| Team | $79 | 50,000 | $0.002/call |
| Enterprise | Custom | Unlimited | Negotiated |

### Revenue Projections

| Month | Users | MRR |
|---|---|---|
| 1 | 50 | $450 |
| 3 | 200 | $1,800 |
| 6 | 500 | $4,500 |
| 12 | 1,000 | $9,000 |
| 24 | 5,000 | $45,000 |

### Cost Structure

| Item | Monthly Cost |
|---|---|
| Proxy service | $200-500 |
| Database (managed) | $50-200 |
| Compute | $100-300 |
| Maps (Mapbox) | $0-50 |
| CDN | $0-20 |
| Monitoring | $0-50 |
| **Total** | **$350-1,120** |

### Break-Even
- At $9/mo average, need ~125 paying users
- At $29/mo average, need ~40 paying users
- Achievable within 3-6 months

---

## Billing Integration

### Stripe (Recommended)
- Subscription management
- Usage metering
- Invoice generation
- Global payments

### Implementation
```python
import stripe

# Create customer
customer = stripe.Customer.create(email="user@example.com")

# Create subscription
subscription = stripe.Subscription.create(
    customer=customer.id,
    items=[{"price": "price_starter_monthly"}]
)

# Track usage for API calls
stripe.SubscriptionItem.create_usage_record(
    subscription_item=subscription.items.data[0].id,
    quantity=1,
    timestamp=int(time.time())
)
```
