# Legal Considerations & ToS Risks

> What's legal, what's risky, what to avoid

---

## AirDNA's Legal Position (from HBS Case Study)

> "AirDNA can legally scrape data from the websites of Airbnb and VRBO on an ongoing basis; however, there is a risk that this could change with future regulation."

This confirms:
- Scraping is currently legal in the US (hiQ Labs v. LinkedIn precedent)
- No patents on the methodology
- Risk is regulatory, not legal

## Key Legal Precedents

| Case | Ruling | Relevance |
|---|---|---|
| **hiQ Labs v. LinkedIn (2022)** | Scraping publicly available data is legal | Protects our scraping of public Airbnb/Vrbo data |
| **Van Buren v. United States (2021)** | CFAA doesn't apply to public data | Protects against Computer Fraud claims |
| **Clearview AI cases** | Scraping public data is generally permissible | Supports our approach |

## What's Legal
- Scraping publicly available listing data (title, price, availability, reviews)
- Scraping calendar data (availability status)
- Storing and analyzing scraped data
- Building analytics on top of scraped data
- Using data for internal research and analysis

## What's Risky
- Circumventing paywalls or authentication
- Ignoring robots.txt (ethical issue, not legal)
- Republishing copyrighted content (listing descriptions, photos)
- Scraping at a rate that causes service degradation
- Violating specific ToS clauses (contract law, not criminal)

## What to Avoid
- Scraping user private data (messages, host contact info)
- Impersonating users or creating fake accounts
- Selling raw scraped data without transformation
- Ignoring DMCA takedown requests
- Scraping in jurisdictions where it's illegal

## Mitigation Strategies

### 1. Transform the Data
Don't republish raw data. Transform it:
- Calculate metrics (occupancy, ADR, revenue)
- Aggregate at market level
- Add your own analytics and scoring

### 2. Respect Rate Limits
- Don't overload servers
- Use reasonable scraping rates (1 req/2-3 sec)
- Implement backoff on 429 errors

### 3. Cache and Deduplicate
- Don't re-scrape unchanged data
- Use conditional requests (If-Modified-Since)
- Cache responses appropriately

### 4. Document Your Process
- Keep records of what you scrape and why
- Document your transformation pipeline
- Be prepared to explain your methodology

### 5. Terms of Service
- Review Airbnb/Vrbo/Booking.com ToS
- Note: AirDNA violates Airbnb's ToS (they scrape despite prohibition)
- ToS violations are civil, not criminal
- Risk of account ban, not lawsuit

## Insurance
- Consider Errors & Omissions insurance
- Document fair use / transformation arguments
- Keep legal counsel on retainer

## Bottom Line
- **Scraping publicly available data is legal** (US law)
- **Transform the data** — don't republish raw
- **Respect rate limits** — don't cause harm
- **Document everything** — be prepared to defend
- **Monitor regulatory changes** — laws may change
