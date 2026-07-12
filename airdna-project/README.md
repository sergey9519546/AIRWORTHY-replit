# 🏠 InsideAirbnb × 青旅选址

NYC Airbnb data analysis for youth hostel location selection.

## Quick Start

### 1. Set up environment
```bash
# Create virtual environment
python -m venv airbnb-env

# Activate it
# Windows:
airbnb-env\Scripts\activate
# Mac/Linux:
source airbnb-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Create database
```bash
python scripts/create_database.py
```

### 3. Load data
```bash
python scripts/load_data.py
```

### 4. Validate data
```bash
python scripts/validate_data.py
```

### 5. Start analysis
Open `notebooks/02_tier0_starter.ipynb` in Jupyter:
```bash
jupyter notebook notebooks/
```

## Project Structure

```
airdna-project/
├── data/
│   └── raw/                    # Raw CSV files (not in git)
├── db/
│   └── airbnb.db              # SQLite database (created by scripts)
├── notebooks/
│   ├── 01_data_loading.ipynb  # Data loading walkthrough
│   ├── 02_tier0_starter.ipynb # Tier 0: Data audit
│   └── ...                    # More notebooks as you progress
├── scripts/
│   ├── create_database.py     # Create SQLite database
│   ├── load_data.py           # Load CSVs into database
│   └── validate_data.py       # Data quality checks
├── output/
│   ├── charts/                # Generated visualizations
│   └── reports/               # Analysis reports
├── schema.sql                 # Database schema
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Data Source

Data from [InsideAirbnb](https://insideairbnb.com/get-the-data/) - NYC snapshot from June 2026.

- **listings.csv.gz** - 50,281 listings with details
- **calendar.csv.gz** - 2.4M daily availability records
- **reviews.csv.gz** - 1.3M guest reviews

## Database

SQLite database at `db/airbnb.db` with:
- `listings` - One row per listing
- `calendar` - Daily availability per listing
- `reviews` - Individual guest reviews
- `listing_stats` - Pre-computed view with revenue estimates
- `neighbourhood_summary` - Pre-computed neighborhood aggregates

## Analysis Tiers

### Tier 0: Data Audit (Days 1-3)
- Load data into database
- Verify data quality
- Document findings

### Tier 1: Market Overview (Days 4-8)
- Borough comparison
- Room type analysis
- Revenue estimates

### Tier 2: Location Scoring (Days 9-14)
- Ghost listing detection
- Host concentration analysis
- Seasonal patterns
- Composite scoring

### Tier 3: Deep Analysis (Days 15-28)
- Price prediction model
- Amenity impact analysis
- Interactive dashboard

## Tips

- Start with Tier 0 - don't skip it!
- Use the pre-computed views (`listing_stats`, `neighbourhood_summary`) for faster analysis
- The `estimated_revenue_l365d` field is already calculated - use it!
- Ask for help if stuck for more than 30 minutes
- Commit to Git frequently
