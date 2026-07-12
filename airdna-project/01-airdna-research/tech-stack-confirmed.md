# AirDNA Confirmed Tech Stack

> From LinkedIn profiles, GitHub repos, DNS analysis, job postings

---

## Confirmed Stack

| Layer | Technology | Source |
|---|---|---|
| **Big Data Processing** | Scala + Apache Spark + Apache Kafka | Kristie Morrison LinkedIn |
| **Workflow Orchestration** | Apache Airflow | Wes Galbraith profile |
| **OLAP Analytics** | Apache Druid (migrated from PG) | Wes Galbraith LinkedIn |
| **Transaction DB** | PostgreSQL | Wes Galbraith LinkedIn |
| **Search Engine** | OpenSearch (migrated from ES) | Wes Galbraith profile |
| **Backend API** | Flask (Python) | Wes Galbraith profile |
| **Data Storage** | AWS S3 (Parquet format) | GitHub dna_util repo |
| **ML Experiment Tracking** | MLflow | GitHub dna_util repo |
| **ML Framework** | Python + XGBoost | HBS AI Institute |
| **Frontend** | Next.js + TypeScript + React | Job postings, source code |
| **UI Library** | MUI (Material UI) v5+ | Source code analysis |
| **CMS** | Prismic.io (headless) | Source code analysis |
| **Containerization** | Docker | Job postings |
| **Cloud Provider** | AWS (us-east-1) | DNS, S3 usage |
| **Orchestration** | Kubernetes | DNS CNAME records |
| **CDN/Proxy** | Cloudflare | DNS analysis |
| **Tools Hosting** | Vercel | DNS for tools.airdna.co |
| **API Docs** | Redocly (OpenAPI 3.0) | airdna.redoc.ly |
| **Auth** | OAuth2 (auth.airdna.co) | Browser redirect |
| **Analytics** | New Relic + Segment | Source code + DNS |
| **Email** | Google Workspace + SendGrid | DNS MX/TXT |
| **Support** | Intercom | DNS TXT |
| **Payments** | Stripe | DNS TXT |
| **Marketing** | HubSpot | DNS TXT |
| **CSS-in-JS** | Emotion | MUI default |

## Infrastructure Architecture

```
Airbnb/Vrbo/Booking.com
        │
        ▼
Residential Proxy Network (Bright Data/Oxylabs)
        │
        ▼
Custom Python Scrapers (16M req/day)
        │
        ▼
Apache Kafka (real-time streaming)
        │
        ▼
Apache Spark/Scala (ETL processing)
        │
        ▼
AWS S3 (Parquet data lake)
        │
        ├──→ Apache Druid (OLAP analytics)
        ├──→ OpenSearch (full-text search)
        └──→ MLflow (ML experiments)
        │
        ▼
Flask REST API (Kubernetes on AWS ELB)
        │
        ▼
Next.js Frontend (Cloudflare CDN)
```

## Scale Math
- 16M listings × 1 request/listing = 16M requests/day
- 16M / 24h = ~667K requests/hour = ~11K requests/minute
- At ~100 concurrent connections: ~110 requests/second sustained
- Estimated proxy cost: $500K-$2M/year

## DNS Mapping

| Domain | Target | Reveals |
|---|---|---|
| airdna.co | 104.20.28.191 | Cloudflare |
| api.airdna.co | k8s-apirouter-*.us-east-1.elb.amazonaws.com | Kubernetes + AWS ELB |
| app.airdna.co | Cloudflare | CDN |
| auth.airdna.co | Cloudflare | OAuth |
| tools.airdna.co | cname.vercel-dns.com | Vercel |

## Third-Party Services (from DNS TXT)
Google Workspace, SendGrid, Intercom, HubSpot, Stripe, Segment, Twilio, Slack, Atlassian, Postman, 1Password, Trustpilot, Facebook, Apple

## GitHub Org
- **Org:** github.com/airdnallc
- **Location:** Denver, CO
- **Public repos:** 1 (dna_util — data science utility functions)
- **Author:** Erich Wellinger (erich@airdna.co)
- **Dependencies:** pyaml, pandas, s3fs, fastparquet, mlflow
