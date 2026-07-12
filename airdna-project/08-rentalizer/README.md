# Rentalizer — Airbnb Revenue Estimator

Estimate annual short-term rental revenue for any NYC property.

## Data Source

Data from [InsideAirbnb](https://insideairbnb.com), licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

Data has been processed and transformed for revenue estimation purposes.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Prepare data
python scripts/prepare_data.py

# Train model
python scripts/train_model.py 20

# Run server
uvicorn src.api:app --reload
```

Open http://localhost:8000

## API

```bash
# Single estimate
curl -X POST http://localhost:8000/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{"address": "350 5th Ave, New York, NY", "bedrooms": 2, "nightly_rate": 200}'

# Health check
curl http://localhost:8000/v1/health

# Model info
curl http://localhost:8000/v1/model/info

# Credits / Attribution
curl http://localhost:8000/v1/credits
```

## Disclaimer

Revenue estimates are provided for informational purposes only and do not constitute
financial, investment, or real estate advice. Estimates are based on historical data
from InsideAirbnb and may not reflect current market conditions. Actual revenue may
vary significantly from estimates. Consult a qualified professional before making
investment decisions.

## License

This project uses data from InsideAirbnb licensed under CC BY 4.0.
