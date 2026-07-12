# Rentalizer Product Innovations — 10 Growth Features

> Prepared by: Senior Product Manager
> Date: 2026-06-29
> Context: Based on Rentalizer NYC STR revenue estimator (FastAPI + XGBoost + KD-Tree comps, InsideAirbnb data, CC BY 4.0)

---

## Table of Contents

1. [Chrome Extension — Revenue Overlay on Airbnb](#1-chrome-extension--revenue-overlay-on-airbnb)
2. [Email Alerts — Market Change Notifications](#2-email-alerts--market-change-notifications)
3. [Portfolio Analysis — Multi-Property Dashboard](#3-portfolio-analysis--multi-property-dashboard)
4. [PDF Reports — Auto-Generated Investment Memos](#4-pdf-reports--auto-generated-investment-memos)
5. [API Marketplace — Sell the Engine](#5-api-marketplace--sell-the-engine)
6. [Browser Extension for Real Estate Agents](#6-browser-extension-for-real-estate-agents)
7. ["What's My Property Worth?" Calculator](#7-whats-my-property-worth-calculator)
8. [Market Comparison Tool — City vs City](#8-market-comparison-tool--city-vs-city)
9. [Investment ROI Calculator](#9-investment-roi-calculator)
10. [Social Sharing — "My Property Earns $X"](#10-social-sharing--my-property-earns-x)

---

## 1. Chrome Extension — Revenue Overlay on Airbnb

### Vision
Instant revenue intelligence while browsing Airbnb. No context-switching. The user sees estimated annual revenue directly on any Airbnb listing page they visit.

### User Stories

**As a property investor browsing Airbnb,**
I want to see estimated annual revenue on each listing page,
so that I can quickly evaluate investment potential without leaving Airbnb.

**As a new host researching the market,**
I want to compare my listing's estimated revenue against similar properties,
so that I can price competitively.

**As a real estate agent showing clients STR potential,**
I want revenue estimates auto-populated on Airbnb pages I share on screen,
so that I can demonstrate ROI in real-time during property tours.

### Implementation

```
Architecture:
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Content Script   │────▶│  Background SW   │────▶│  Rentalizer API  │
│  (injected into   │     │  (caches results,│     │  /v1/estimate    │
│   airbnb.com)     │     │   rate limits)   │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │
        ▼
┌──────────────────┐
│  Floating Panel   │
│  Revenue badge    │
│  Confidence range │
│  "View Details"   │
└──────────────────┘
```

**Technical Details:**
- **Content Script** parses Airbnb listing page DOM: extract title, bedrooms, bathrooms, accommodates, nightly rate, and address (from map section or structured data)
- **Service Worker** deduplicates requests, caches results in `chrome.storage.local` (TTL: 7 days), rate-limits to 10 requests/min for free users
- **Overlay UI** injects a floating badge on the listing card (mini) and a slide-out panel on the listing detail page (full estimate with comps)
- **Manifest V3** for Chrome Web Store compliance

**API Additions Needed:**
- New endpoint: `POST /v1/estimate/from-url` — accepts an Airbnb URL, scrapes listing metadata server-side, returns estimate
- Alternatively: client-side extraction + existing `/v1/estimate` (simpler, no scraping liability)

**Monetization:**
- Free: 10 lookups/day
- Pro ($9/mo): Unlimited lookups, export to CSV
- Team ($29/mo): Shared workspace, branding

**Effort:** 3-4 weeks (2 eng)
**Priority:** 🔴 HIGH — strongest growth hack, viral by nature

---

## 2. Email Alerts — Market Change Notifications

### Vision
Proactive intelligence delivered to inbox. Users subscribe to markets or properties and get alerts when revenue estimates shift, new comps appear, or market conditions change.

### User Stories

**As an investor monitoring a target market,**
I want weekly email digests showing revenue trend changes for Brooklyn,
so that I can time my acquisition without checking the site daily.

**As a property owner,**
I want an alert when a new comparable listing appears within 1km of my property,
so that I can adjust my pricing strategy proactively.

**As a portfolio manager,**
I want monthly summary emails with estimated revenue changes across all my tracked properties,
so that I can report performance to stakeholders.

### Implementation

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Alert Engine     │────▶│  Email Renderer  │────▶│  SendGrid/SES    │
│  (cron: daily)    │     │  (Jinja2 + MJML) │     │                  │
│                   │     │                  │     │                  │
│  - Market scanner │     │  - Weekly digest │     │                  │
│  - Comp watcher   │     │  - Alert emails  │     │                  │
│  - Trend detector │     │  - Monthly rollup│     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

**Technical Details:**
- **Database:** `subscriptions` table (user_id, market/property, alert_type, frequency)
- **Alert Types:**
  - `market_weekly_digest` — borough-level metrics: median revenue, occupancy trend, new listings, removed listings
  - `comp_alert` — new listing appears within user's tracked property radius
  - `revenue_shift` — estimate changes >10% for a tracked property (triggered on data refresh)
  - `monthly_portfolio_rollup` — aggregated performance across all tracked properties
- **Trend Detection:** Compare current model estimates vs. 30/60/90-day ago snapshots (requires storing historical estimates)
- **Email Templates:** MJML for responsive HTML, plain-text fallback, unsubscribe link (CAN-SPAM)
- **Frequency:** Users choose daily/weekly/monthly per alert type

**Data Requirements:**
- Store historical estimates per property (snapshot table)
- Store historical market stats per borough per month
- Index new/removed listings from each InsideAirbnb data refresh

**Monetization:**
- Free: 1 market alert (weekly)
- Starter ($9/mo): 5 markets, weekly digests
- Pro ($29/mo): Unlimited markets, comp alerts, daily frequency
- Team ($79/mo): Shared alerts, Slack/webhook integration

**Effort:** 4-5 weeks (2 eng + 1 design)
**Priority:** 🟡 MEDIUM — retention driver, requires data pipeline maturity

---

## 3. Portfolio Analysis — Multi-Property Dashboard

### Vision
A unified dashboard for investors with multiple properties. Upload or enter a portfolio, see aggregated revenue, compare properties side-by-side, and identify underperformers.

### User Stories

**As an investor with 5 STR properties,**
I want a single dashboard showing estimated revenue for all my properties,
so that I can see which ones are underperforming and need attention.

**As a property manager pitching to a new client,**
I want to upload their portfolio of 12 properties and generate a professional analysis,
so that I can demonstrate my market expertise and win the contract.

**As an investor evaluating a new acquisition,**
I want to add a hypothetical property to my existing portfolio and see the blended ROI,
so that I can make a data-driven acquisition decision.

### Implementation

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Portfolio UI     │────▶│  Batch API       │────▶│  Analytics Engine│
│  - Upload CSV     │     │  /v1/batch       │     │  - Aggregation   │
│  - Manual entry   │     │  (max 50)        │     │  - Comparison    │
│  - Map view       │     │                  │     │  - Ranking       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │
        ▼
┌──────────────────┐
│  Dashboard        │
│  - Total revenue  │
│  - Per-property   │
│  - Revenue/bedroom│
│  - Revenue/sqft   │
│  - Market heatmap │
└──────────────────┘
```

**Technical Details:**
- **Database:** `portfolios` table (user_id, name, created_at), `portfolio_properties` table (portfolio_id, address, bedrooms, bathrooms, accommodates, nightly_rate, estimate_cache)
- **Batch Processing:** Expand existing `/v1/batch` to support 50 properties (currently capped at 20), add async option for large portfolios
- **Portfolio Metrics:**
  - Total estimated annual revenue (sum)
  - Average revenue per property
  - Revenue per bedroom (efficiency metric)
  - Concentration risk (% revenue in single borough)
  - Comparison vs. borough medians
  - Revenue distribution (histogram)
- **CSV Import:** Accept CSV with columns: address, bedrooms, bathrooms, accommodates, nightly_rate. Validate, geocode, estimate all.
- **Map View:** Mapbox GL with color-coded pins (green = above median, red = below)

**Monetization:**
- Free: 1 portfolio, 3 properties max
- Starter ($9/mo): 3 portfolios, 10 properties each
- Pro ($29/mo): Unlimited portfolios, 50 properties, CSV import/export
- Team ($79/mo): Shared portfolios, client-facing reports

**Effort:** 5-6 weeks (2 eng + 1 design)
**Priority:** 🟡 MEDIUM — high value for power users, expands TAM to property managers

---

## 4. PDF Reports — Auto-Generated Investment Memos

### Vision
One-click professional PDF reports that investors can share with partners, lenders, or spouses. Branded, data-rich, and actionable.

### User Stories

**As an investor pitching a deal to my partner,**
I want to generate a PDF report with revenue estimates, comps, and market context,
so that I can make a professional case for the investment.

**As a real estate agent,**
I want to add my logo and branding to Rentalizer reports before sending to clients,
so that I look like a market expert.

**As an investor applying for a DSCR loan,**
I want a report with methodology, confidence intervals, and data sources,
so that the lender trusts the revenue projections.

### Implementation

**Report Sections:**
1. **Executive Summary** — Property address, estimated annual revenue, confidence range, verdict (Above/Average/Below market)
2. **Property Details** — Bedrooms, bathrooms, guests, nightly rate, borough
3. **Revenue Analysis** — Point estimate, confidence interval visualization (gauge chart), comparison to borough median
4. **Comparable Properties** — Top 5 comps table (distance, bedrooms, revenue, similarity score)
5. **Market Context** — Borough stats (median revenue, median price, active listings, revenue-to-price ratio)
6. **Methodology** — How the model works, data source (InsideAirbnb, CC BY 4.0), confidence calculation
7. **Disclaimers** — Not financial advice, estimates based on historical data, etc.

**Technical Stack:**
- **Template:** WeasyPrint (HTML/CSS → PDF) or ReportLab for programmatic generation
- **Charts:** Matplotlib/Plotly rendered to PNG, embedded in PDF
- **Branding:** Pro/Team users can upload logo, set accent color
- **Delivery:** Instant download + email attachment option

**Monetization:**
- Starter ($9/mo): 3 reports/month, Rentalizer branding
- Pro ($29/mo): Unlimited reports, custom branding, email delivery
- Team ($79/mo): Bulk generation, API access for reports

**Effort:** 3-4 weeks (1 eng + 1 design)
**Priority:** 🔴 HIGH — direct revenue driver, enables agent/manager sales channel

---

## 5. API Marketplace — Sell the Engine

### Vision
Expose the Rentalizer estimation engine as a self-service API on RapidAPI and direct. Developers, proptech startups, and data analysts pay per-call or subscribe.

### User Stories

**As a proptech developer building a property analysis tool,**
I want to call a revenue estimation API with an address and property details,
so that I can embed revenue estimates in my app without building my own model.

**As a data analyst at a real estate fund,**
I want to run batch estimates on 500 properties via API,
so that I can screen acquisition targets programmatically.

**As a real estate content creator,**
I want to embed a "Check Revenue" widget on my blog,
so that my readers can estimate revenue and I earn affiliate commissions.

### Implementation

**API Tiers:**

| Tier | Rate Limit | Batch Size | Price |
|------|-----------|------------|-------|
| Free | 100 calls/mo | 1 | $0 |
| Starter | 5,000 calls/mo | 10 | $29/mo |
| Pro | 50,000 calls/mo | 50 | $149/mo |
| Enterprise | Unlimited | 200 | Custom |

**Technical Details:**
- **API Key Auth:** `X-API-Key` header, stored hashed in database
- **Rate Limiting:** Token bucket per API key, 429 responses with `Retry-After` header
- **Usage Metering:** Log every request (api_key, endpoint, timestamp, response_time, status)
- **Developer Portal:** Interactive docs (Swagger UI already exists), code samples (Python, JS, cURL, Ruby), webhook for batch completion
- **RapidAPI Listing:** Mirror endpoints on RapidAPI for discovery (RapidAPI takes 20% cut but provides distribution)
- **SDK:** Python and JavaScript SDKs (auto-generated from OpenAPI spec)

**Monetization:**
- Per-call pricing on RapidAPI ($0.02-0.05/call)
- Subscription tiers on direct portal (better margins)
- Enterprise: custom SLA, dedicated infrastructure, priority support

**Effort:** 4-5 weeks (2 eng)
**Priority:** 🟡 MEDIUM — revenue diversification, long sales cycle but high LTV

---

## 6. Browser Extension for Real Estate Agents

### Vision
A specialized tool for real estate agents to demonstrate STR revenue potential during property showings and client meetings. White-label capable.

### User Stories

**As a real estate agent specializing in investment properties,**
I want to show clients estimated STR revenue on any property listing (Zillow, Redfin, Realtor.com),
so that I can differentiate myself from other agents and close deals faster.

**As a brokerage owner,**
I want my agents to use a branded version of the Rentalizer extension,
so that our firm looks tech-forward and data-driven.

**As an agent preparing a listing presentation,**
I want to generate a "STR Revenue Potential" one-pager for a seller,
so that I can justify my pricing strategy with data.

### Implementation

**Differences from Consumer Chrome Extension (#1):**

| Feature | Consumer Extension | Agent Extension |
|---------|-------------------|-----------------|
| Supported Sites | Airbnb only | Zillow, Redfin, Realtor.com, MLS |
| Data Extracted | Listing details | Property specs (from any listing site) |
| White-label | No | Yes (custom logo, colors) |
| Report Generation | Link to web | Inline PDF generation |
| Pricing | Freemium | Per-seat licensing |
| Client Sharing | No | Yes (branded shareable links) |

**Technical Details:**
- **Multi-site Content Scripts:** Parse structured data from Zillow (JSON-LD), Redfin (React state), Realtor.com (meta tags), and generic real estate pages
- **Property Data Extraction:** bedrooms, bathrooms, sqft, lot size, year built, address, asking price
- **Revenue-to-Price Ratio:** Calculate and display prominently (key metric for investors)
- **Client Mode:** Generate a shareable link with a branded landing page showing the estimate
- **CRM Integration:** Optional webhook to push estimates to agent's CRM (follow-up trigger)

**Monetization:**
- Individual Agent: $49/mo per seat
- Brokerage (5+ seats): $39/mo per seat
- White-label: $99/mo + $19/seat

**Effort:** 5-6 weeks (2 eng + 1 design)
**Priority:** 🟡 MEDIUM — high-value segment, longer sales cycle, strong retention

---

## 7. "What's My Property Worth?" Calculator

### Vision
A viral, embeddable calculator for property owners. Enter your address, see estimated STR revenue, compare to your current income, get a "rental arbitrage" score.

### User Stories

**As a homeowner considering converting my spare room to an Airbnb,**
I want to see how much I could earn as a short-term rental,
so that I can decide if it's worth the effort vs. traditional renting.

**As a current Airbnb host,**
I want to check if my revenue is above or below the market average for my property type,
so that I can optimize my pricing or listing.

**As a real estate blogger,**
I want to embed the Rentalizer calculator on my site,
so that my readers get value and I earn affiliate commissions.

### Implementation

**User Flow:**
```
Enter Address → Confirm Property Details → See Estimate → Compare to:
  ├── Long-term rental estimate (Zillow Rent Zestimate API or manual input)
  ├── Arbitrage score (STR revenue / LTR revenue)
  ├── Revenue per bedroom
  └── Market percentile ranking
```

**Output Card:**
```
┌─────────────────────────────────────────────┐
│  🏠 Your Property's STR Potential           │
│                                             │
│  Estimated Annual Revenue                   │
│  $XX,XXX — $XX,XXX                          │
│  ████████████████████░░░░  High Confidence  │
│                                             │
│  vs. Long-Term Rental: +XX% more            │
│  Market Percentile: Top XX%                 │
│  Revenue per Bedroom: $X,XXX/mo             │
│                                             │
│  [Share This Estimate] [Get Full Report]    │
│                                             │
│  ⚠️ Estimates based on historical data.     │
│  Not financial advice.                      │
└─────────────────────────────────────────────┘
```

**Embeddable Widget:**
- JavaScript snippet for blogs/websites
- iframe option for no-JS environments
- Customizable theme (light/dark)
- Affiliate tracking via URL parameter

**Technical Details:**
- **LTR Comparison:** Accept manual input (current monthly rent) or integrate Zillow API for rent estimates
- **Arbitrage Score:** STR annual revenue / (LTR monthly × 12). Score > 1.3 = strong STR advantage
- **Percentile Ranking:** Compare user's estimate against distribution of all listings in same borough + bedroom count
- **Lead Capture:** Optional email gate for full report (email → Mailchimp/ConvertKit)

**Monetization:**
- Free (lead generation): Basic estimate, email gate for full report
- Affiliate: Links to property management tools, insurance, furnishing companies
- Pro users get ad-free embeds

**Effort:** 2-3 weeks (1 eng + 1 design)
**Priority:** 🔴 HIGH — viral growth engine, SEO magnet, lead generation

---

## 8. Market Comparison Tool — City vs City

### Vision
Interactive comparison dashboard for investors deciding which market to enter. Compare two or more cities side-by-side on key STR metrics.

### User Stories

**As an investor deciding between Nashville and Austin for my next STR purchase,**
I want to compare revenue potential, occupancy trends, and regulation risk side-by-side,
so that I can make a data-driven market selection.

**As a real estate content creator,**
I want to generate a "Top 10 STR Markets" ranking with data-backed methodology,
so that my content is credible and shareable.

**As a property manager expanding to a new city,**
I want to compare my current market's performance against potential expansion markets,
so that I can prioritize where to open an office next.

### Implementation

**Comparison Dimensions:**

| Category | Metrics |
|----------|---------|
| **Revenue** | Median annual revenue, ADR (avg daily rate), RevPAR |
| **Occupancy** | Average occupancy rate, seasonal variance, peak months |
| **Supply** | Active listings, YoY growth, listing density per capita |
| **Regulation** | STR-friendly score (manual curation), permit requirements, tax rates |
| **Investment** | Median property price, cap rate, cash-on-cash return, price-to-revenue ratio |
| **Growth** | Revenue trend (12-month), new listing velocity, demand growth |

**UI Layout:**
```
┌─────────────────────┬─────────────────────┐
│   Nashville 🎸      │   Austin 🤠         │
├─────────────────────┼─────────────────────┤
│ Revenue: $42,000    │ Revenue: $38,500    │
│ ADR: $185           │ ADR: $165           │
│ Occupancy: 62%      │ Occupancy: 58%      │
│ Active Listings: 4.2K│ Active Listings: 6.8K│
│ Cap Rate: 6.8%      │ Cap Rate: 5.9%      │
│ STR Score: 8.5/10   │ STR Score: 7.2/10   │
├─────────────────────┼─────────────────────┤
│ 📈 12-mo Trend ↑12% │ 📈 12-mo Trend ↑8%  │
└─────────────────────┴─────────────────────┘
```

**Technical Details:**
- **Data Sources:** InsideAirbnb (CC BY 4.0) for Airbnb data; manual curation for regulatory data; public property price data (Zillow API or county records)
- **Market Database:** Pre-computed metrics per city, refreshed with each InsideAirbnb data update
- **Regulatory Score:** Manually curated per city, updated quarterly (crowdsource later)
- **Expansion Path:** Start with top 20 US STR markets, expand based on demand
- **SEO Play:** Each comparison generates a unique URL (`/compare/nashville-vs-austin`) — massive long-tail SEO opportunity

**Monetization:**
- Free: Compare 2 cities, basic metrics
- Pro ($29/mo): Compare up to 5 cities, full metrics, export
- Team ($79/mo): Custom reports, regulatory alerts, API access

**Effort:** 6-8 weeks (2 eng + 1 data analyst)
**Priority:** 🟡 MEDIUM — requires multi-city data, but massive SEO and content value

---

## 9. Investment ROI Calculator

### Vision
Go beyond revenue estimation. Full investment analysis including purchase price, financing, expenses, and projected returns over 5-10 years.

### User Stories

**As an investor evaluating a $450K condo for STR,**
I want to enter the purchase price, down payment, interest rate, and expected expenses,
so that I can see my projected cash flow, cap rate, and 5-year ROI before making an offer.

**As a first-time STR investor,**
I want the calculator to suggest typical expense categories and defaults for my market,
so that I don't forget to budget for cleaning, management, or STR insurance.

**As an investor comparing financing options,**
I want to see how a 20% down vs. 25% down payment affects my monthly cash flow and total ROI,
so that I can optimize my capital allocation.

### Implementation

**Input Form:**
```
Purchase Details:
  ├── Purchase Price: $450,000
  ├── Down Payment: 20% ($90,000)
  ├── Interest Rate: 6.5%
  ├── Loan Term: 30 years
  └── Closing Costs: 3% ($13,500)

Revenue (auto-filled from Rentalizer):
  ├── Estimated Annual Revenue: $42,000
  └── [Adjust ±10% slider]

Operating Expenses (defaults for NYC):
  ├── Property Management: 20% ($8,400)
  ├── Cleaning/Turnover: $150/turn × 120 turns ($18,000)
  ├── Insurance (STR): $2,400/yr
  ├── Property Tax: $6,000/yr
  ├── Maintenance: 5% ($2,100)
  ├── Utilities: $3,600/yr
  ├── Supplies/Consumables: $1,200/yr
  ├── Platform Fees: 3% ($1,260)
  └── [Add Custom Expense]
```

**Output Dashboard:**
```
┌─────────────────────────────────────────────┐
│  📊 Investment Analysis                     │
│                                             │
│  Monthly Cash Flow:        +$380/mo         │
│  Annual Cash Flow:         +$4,560          │
│  Cap Rate:                 5.2%             │
│  Cash-on-Cash Return:      5.1%             │
│  DSCR:                     1.28             │
│                                             │
│  5-Year Projection:                         │
│  ├── Total Cash Flow:     $22,800           │
│  ├── Principal Paydown:   $18,400           │
│  ├── Appreciation (3%):   $71,200           │
│  └── Total ROI:           $112,400 (125%)   │
│                                             │
│  Break-even Occupancy:    42%               │
│  [Download PDF Report] [Share]              │
└─────────────────────────────────────────────┘
```

**Technical Details:**
- **Mortgage Calculator:** Standard amortization formula, monthly payment = P[r(1+r)^n]/[(1+r)^n-1]
- **Expense Defaults:** Pre-loaded per market (NYC, Nashville, Austin, etc.), editable by user
- **Projections:** Monte Carlo simulation on revenue (normal distribution based on confidence interval) and appreciation (historical avg ± std dev)
- **Sensitivity Analysis:** "What if" sliders for revenue ±20%, interest rate ±1%, appreciation ±2%
- **Tax Benefits:** Optional section for depreciation (27.5yr residential), mortgage interest deduction (show estimated tax savings)

**Monetization:**
- Free: Basic ROI calculation, Rentalizer estimate
- Pro ($29/mo): Full expense breakdown, 5-year projections, PDF export, tax analysis
- Team ($79/mo): Multiple scenarios, portfolio-level ROI, client sharing

**Effort:** 4-5 weeks (2 eng + 1 design)
**Priority:** 🔴 HIGH — highest value-add for investor segment, natural upgrade from revenue estimate

---

## 10. Social Sharing — "My Property Earns $X"

### Vision
Viral sharing mechanics that turn every estimate into a marketing moment. Users share their revenue badge on social media, driving organic traffic.

### User Stories

**As a proud Airbnb host,**
I want to share a beautiful graphic showing my property's estimated revenue on Instagram,
so that I can flex my investment success and attract followers.

**As an investor who just got a high-confidence estimate,**
I want to share my result on Twitter with a branded Rentalizer badge,
so that my network sees the tool and some sign up (referral credit).

**As a real estate agent,**
I want to share a client's property estimate as a LinkedIn post,
so that I demonstrate my market knowledge and attract new investor clients.

### Implementation

**Shareable Card Generation:**
```
┌─────────────────────────────────────────────┐
│  🏠 My NYC Property                         │
│                                             │
│  Estimated Annual Revenue                   │
│           $42,500                           │
│  ████████████████████░░░░  High Confidence  │
│                                             │
│  Top 15% in Brooklyn                        │
│  📍 Williamsburg, NY                        │
│                                             │
│  ── Powered by Rentalizer ──                │
│  rentalizer.app                             │
└─────────────────────────────────────────────┘
```

**Platforms & Formats:**
- **Instagram:** 1080×1080 image card (auto-generated via canvas API or Puppeteer)
- **Twitter/X:** Summary card with OG image + pre-written tweet text
- **LinkedIn:** Professional format with methodology note
- **Facebook:** Open Graph image + description
- **TikTok:** Short video template (animated number reveal) — stretch goal

**Technical Details:**
- **Server-Side Rendering:** Endpoint `GET /v1/share/{estimate_id}` renders an HTML card, screenshots it with Puppeteer, returns PNG
- **Dynamic OG Images:** `GET /v1/og/{estimate_id}` returns an image optimized for social previews (1200×630)
- **Pre-written Copy:** Generate platform-specific captions:
  - Twitter: "My NYC Airbnb could earn $42K/year! 🏠💰 Check yours → rentalizer.app #ShortTermRental #RealEstate"
  - LinkedIn: "Rentalizer analysis shows strong STR potential for this Williamsburg property..."
- **Referral System:** Each share includes a unique referral link. Referred signups earn credits for the referrer.
- **Privacy Controls:** Users choose what to share (full address, neighborhood only, or city only)
- **Leaderboard:** Opt-in "Top Earners" leaderboard by borough — gamification

**Monetization:**
- Free: Share to 1 platform, Rentalizer branding
- Pro ($29/mo): Custom branding, all platforms, analytics on shares
- Referral credits: $5 credit per referred signup

**Effort:** 2-3 weeks (1 eng + 1 design)
**Priority:** 🔴 HIGH — viral growth loop, low implementation cost, high ROI

---

## Implementation Roadmap

### Phase 1: Quick Wins (Weeks 1-4)
| # | Feature | Effort | Impact | Priority |
|---|---------|--------|--------|----------|
| 7 | "What's My Property Worth?" Calculator | 2-3 wk | 🔴 High | Lead gen, SEO |
| 10 | Social Sharing | 2-3 wk | 🔴 High | Viral growth |
| 4 | PDF Reports | 3-4 wk | 🔴 High | Revenue driver |

### Phase 2: Growth Engines (Weeks 5-10)
| # | Feature | Effort | Impact | Priority |
|---|---------|--------|--------|----------|
| 1 | Chrome Extension | 3-4 wk | 🔴 High | User acquisition |
| 9 | Investment ROI Calculator | 4-5 wk | 🔴 High | Conversion driver |
| 5 | API Marketplace | 4-5 wk | 🟡 Medium | Revenue diversification |

### Phase 3: Platform Expansion (Weeks 11-18)
| # | Feature | Effort | Impact | Priority |
|---|---------|--------|--------|----------|
| 2 | Email Alerts | 4-5 wk | 🟡 Medium | Retention |
| 3 | Portfolio Analysis | 5-6 wk | 🟡 Medium | Power users |
| 6 | Agent Browser Extension | 5-6 wk | 🟡 Medium | New segment |
| 8 | Market Comparison Tool | 6-8 wk | 🟡 Medium | SEO, content |

---

## Revenue Impact Projection

| Feature | New Users (6mo) | Conversion Lift | Revenue Impact |
|---------|-----------------|-----------------|----------------|
| Chrome Extension | +5,000 | +15% to Pro | $6,750/mo |
| Email Alerts | +2,000 | +20% retention | $3,600/mo |
| Portfolio Analysis | +500 | +25% to Team | $1,950/mo |
| PDF Reports | +3,000 | +30% to Starter | $8,100/mo |
| API Marketplace | +200 (devs) | Direct revenue | $4,500/mo |
| Agent Extension | +300 (agents) | $49/seat | $14,700/mo |
| Property Calculator | +10,000 | +5% to Starter | $4,500/mo |
| Market Comparison | +3,000 | +10% to Pro | $8,700/mo |
| ROI Calculator | +4,000 | +20% to Pro | $23,200/mo |
| Social Sharing | +8,000 | +3% to Starter | $2,160/mo |
| **Total** | **+38,000** | — | **~$78,000/mo** |

*Assumptions: 6-month cumulative, based on pricing tiers ($9 Starter, $29 Pro, $49 Agent, $79 Team)*

---

## Key Dependencies & Risks

| Risk | Affected Features | Mitigation |
|------|-------------------|------------|
| Multi-city data not available | #6, #8 | Start NYC-only, expand with InsideAirbnb cities |
| Model accuracy insufficient | All | Transparent confidence intervals, conservative estimates |
| Chrome Web Store rejection | #1, #6 | Follow Manifest V3 strictly, no scraping violations |
| Email deliverability | #2 | Use established ESP (SendGrid), warm up domain |
| API abuse | #5 | Rate limiting, API key validation, usage alerts |
| Social platform API changes | #10 | Generate images server-side, don't rely on platform APIs |
| Legal (financial advice claims) | #7, #9 | Disclaimers everywhere, "estimates only" language |

---

## Next Steps

1. **Validate with users:** Interview 10 NYC STR investors to prioritize features
2. **Build #7 and #10 first:** Lowest effort, highest viral potential
3. **Set up analytics:** Track which features drive signups and conversions
4. **Plan multi-city expansion:** Identify next 5 cities based on InsideAirbnb data availability
5. **Legal review:** Ensure all new features comply with disclaimers and CC BY 4.0 attribution
