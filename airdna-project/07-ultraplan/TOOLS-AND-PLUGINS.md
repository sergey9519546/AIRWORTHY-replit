# Tools, Plugins & Skills for AirDNA Clone

> Complete inventory of what's available, what's installed, and what's needed.

---

## 1. OpenClaw Skills (Already Installed)

| Skill | Status | Use in Project |
|-------|--------|----------------|
| **agent-browser** | ✅ v0.27.0 | Browser automation, cookie extraction, SSR blob scraping |
| **data-analysis** | ✅ Installed | Statistical analysis, chart selection, metric contracts |
| **code-generator** | ✅ Installed | Scaffold Python code, generate functions/classes |
| **github** | ✅ Installed | Version control, repo management |
| **clawhub-cli** | ✅ Installed | Install more skills from ClawHub |
| **akshare** | ✅ Installed | Financial data APIs (Chinese market, may have real estate data) |
| **excel-xlsx** | ✅ Installed | Export data to Excel/spreadsheets |
| **mimo-omni** | ✅ Installed | Multimodal analysis (images, charts) |
| **frontend-design** | ✅ Installed | UI design for the web app |
| **healthcheck** | ✅ Installed | System health monitoring |
| **audit** | ✅ Installed | Security auditing |
| **harden** | ✅ Installed | Security hardening |
| **extract** | ✅ Installed | Data extraction |
| **skill-creator** | ✅ Installed | Create custom skills |
| **self-improvement** | ✅ Installed | Agent self-improvement patterns |

---

## 2. OpenClaw Skills (Should Install from ClawHub)

Based on the awesome-openclaw-skills list (5,300+ skills available):

### Data & Analytics (28 skills available)
```bash
# Install via:
openclaw skills install <skill-slug>
# or:
npx clawhub install <skill-slug>
```

| Skill | Purpose | Priority |
|-------|---------|----------|
| **sql** | Query design, review for data extraction | 🔴 High |
| **csv** | Cleanup, normalization for tabular data | 🔴 High |
| **dashboard** | KPI visualization patterns | 🟡 Medium |
| **report** | Stakeholder-facing deliverables | 🟡 Medium |
| **business-intelligence** | KPI systems, operating cadence | 🟡 Medium |

### Browser & Automation (323 skills available)
| Skill | Purpose | Priority |
|-------|---------|----------|
| **agent-browser** | ✅ Already installed | — |
| **2captcha** | Solve CAPTCHAs for scraping | 🟡 Medium |
| **scrapling** | Anti-bot adaptive scraping | 🟡 Medium |

### Search & Research (345 skills available)
| Skill | Purpose | Priority |
|-------|---------|----------|
| **academic-research** | Search academic papers (OpenAlex API) | 🟢 Low |
| **arxiv-search-collector** | arXiv paper retrieval | 🟢 Low |

### DevOps & Cloud (393 skills available)
| Skill | Purpose | Priority |
|-------|---------|----------|
| **docker** | Containerization | 🔴 High |
| **railway** or **fly-io** | Deployment | 🟡 Medium |

---

## 3. Python Packages (Need to Install)

### Machine Learning (Critical)
```bash
pip3 install xgboost lightgbm catboost optuna shap scikit-learn
```

| Package | Purpose | Priority |
|---------|---------|----------|
| **xgboost** | Gradient boosting (primary model) | 🔴 Critical |
| **lightgbm** | Gradient boosting (baseline/faster) | 🔴 High |
| **catboost** | Gradient boosting (native categorical support) | 🟡 Medium |
| **optuna** | Hyperparameter tuning | 🔴 Critical |
| **shap** | Model interpretability (feature importance) | 🔴 High |
| **scikit-learn** | ML utilities, metrics, preprocessing | 🔴 Critical |

### Data Science (Critical)
```bash
pip3 install pandas numpy scipy matplotlib geopy
```

| Package | Purpose | Status |
|---------|---------|--------|
| **pandas** | Data manipulation | ✅ Installed (3.0.3) |
| **numpy** | Numerical computing | ✅ Installed (2.4.6) |
| **scipy** | Scientific computing, KD-Tree | 🔴 Need install |
| **matplotlib** | Visualization | 🔴 Need install |
| **geopy** | Geocoding (Nominatim wrapper) | 🔴 Need install |

### API & Web (Critical)
```bash
pip3 install fastapi uvicorn pydantic cachetools
```

| Package | Purpose | Priority |
|---------|---------|----------|
| **fastapi** | Web framework for API | 🔴 Critical |
| **uvicorn** | ASGI server | 🔴 Critical |
| **pydantic** | Data validation (bundled with FastAPI) | 🔴 Critical |
| **cachetools** | TTL cache for geocoding | 🔴 High |

### Scraping (Already Installed)
| Package | Purpose | Status |
|---------|---------|--------|
| **requests** | HTTP client | ✅ Installed (2.34.2) |
| **playwright** | Browser automation | ✅ Installed (1.60.0) |

### Testing (Critical)
```bash
pip3 install pytest hypothesis faker
```

| Package | Purpose | Priority |
|---------|---------|----------|
| **pytest** | Test framework | 🔴 Critical |
| **hypothesis** | Property-based testing | 🟡 Medium |
| **faker** | Generate test data | 🟡 Medium |

### Database (Deferred — not needed for MVP)
| Package | Purpose | Priority |
|---------|---------|----------|
| **psycopg2-binary** | PostgreSQL driver | 🟢 Later |
| **sqlalchemy** | ORM | 🟢 Later |
| **redis** | Caching layer | 🟢 Later |
| **celery** | Background task queue | 🟢 Later |

---

## 4. External APIs & Services

### Geocoding
| Service | Free Tier | Cost/1K | Priority |
|---------|-----------|---------|----------|
| **Mapbox Geocoding** | 100K/mo | $0.75 | 🔴 Primary |
| **Nominatim (OSM)** | 1 req/sec | Free | 🟡 Fallback |
| **HERE Geocoding** | 250K/mo | $0.83 | 🟢 Alternative |
| **Google Maps** | $200 credit/mo | $5.00 | 🟢 Last resort |

### Mapping
| Service | Free Tier | Purpose |
|---------|-----------|---------|
| **Mapbox GL JS** | 50K loads/mo | Map visualization |
| **Leaflet + OSM** | Unlimited | Free alternative |

### Data Sources
| Source | Cost | Data |
|--------|------|------|
| **InsideAirbnb** | Free (CC BY 4.0) | 30K+ NYC listings, calendar, reviews |
| **Nager.Date** | Free, no limits | Public holidays (100+ countries) |
| **Ticketmaster** | Free (5K calls/day) | Events data |
| **US Census** | Free | Demographics |
| **OpenStreetMap** | Free | POI data, boundaries |

### Anti-Bot / Scraping (If needed later)
| Service | Cost | Purpose |
|---------|------|---------|
| **Scrapfly** | $49+/mo | Anti-bot bypass SaaS |
| **Bright Data** | $500+/mo | Residential proxies |
| **2captcha** | $2.99/1K | CAPTCHA solving |

---

## 5. Development Tools

### Already Available
| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12.3 | Primary language |
| **Node.js** | v22.22.3 | agent-browser, clawhub |
| **agent-browser** | 0.27.0 | Browser automation |
| **curl** | Available | HTTP testing |
| **git** | Available | Version control |

### Need to Install
| Tool | Install Command | Purpose |
|------|-----------------|---------|
| **Docker** | `apt install docker.io` | Containerization |
| **PostgreSQL** | `apt install postgresql` | Database (later) |
| **Redis** | `apt install redis-server` | Caching (later) |

---

## 6. Deployment Platforms (Free/Low-Cost)

| Platform | Free Tier | Best For |
|----------|-----------|----------|
| **Railway** | $5/mo credit | FastAPI + PostgreSQL |
| **Fly.io** | 3 shared VMs free | Docker containers |
| **Render** | Free web services | Simple deployment |
| **Vercel** | Free for hobby | Frontend (if React) |
| **Cloudflare Pages** | Unlimited free | Static frontend |
| **Upstash** | 10K commands/day free | Redis caching |

---

## 7. Recommended Install Order

### Step 1: Core ML Packages
```bash
pip3 install xgboost lightgbm optuna shap scikit-learn scipy matplotlib
```

### Step 2: API Packages
```bash
pip3 install fastapi uvicorn cachetools geopy
```

### Step 3: Testing Packages
```bash
pip3 install pytest hypothesis faker
```

### Step 4: OpenClaw Skills
```bash
# Check if clawhub CLI works
npx clawhub --version

# Install data-related skills
openclaw skills install sql
openclaw skills install csv
```

### Step 5: Verify Installation
```bash
python3 -c "
import xgboost, lightgbm, optuna, shap, sklearn, scipy, matplotlib, fastapi, uvicorn, geopy, cachetools, pytest
print('All packages imported successfully!')
"
```

---

## 8. What We DON'T Need (Yet)

| Tool | Why Not |
|------|---------|
| PostgreSQL/PostGIS | In-memory with KD-Tree is fine for 5K listings |
| Redis | cachetools.TTLCache is sufficient for MVP |
| Celery | No background tasks in MVP |
| Docker | Can deploy without it initially |
| Scrapfly/Bright Data | Using InsideAirbnb data, not scraping |
| Vrbo API | Blocked, not in MVP scope |
| Booking.com API | Partial, not in MVP scope |
