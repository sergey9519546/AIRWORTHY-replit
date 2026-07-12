# Guestready/airdna-api Source Code

> Python client for AirDNA Enterprise API

---

## Repository
- **Repo:** github.com/guestready/airdna-api
- **Stars:** 2
- **License:** None
- **Created:** 2024-07-04
- **Updated:** 2026-01-27

## Architecture
```
src/airdna_api/
├── __init__.py
├── client.py          # AirDNAClient(GenericClient) — Bearer token auth
├── endpoints.py       # AirDNAEndpoint(PostEndpoint), RentalizerEstimateEndpoint
├── serializers.py     # DRF serializers for request/response
└── sessions.py        # AirDNASession — base_url, headers
```

## Session (Base URL)
```python
class AirDNASession:
    base_url = "https://api.airdna.co/api/enterprise/v1/"
    def headers(self):
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
```

## Rentalizer Request Serializer
```python
class RentalizerEstimateRequestSerializer(serializers.Serializer):
    accommodates = serializers.IntegerField()
    bathrooms = serializers.IntegerField()
    bedrooms = serializers.IntegerField()
    lat = serializers.CharField()
    lng = serializers.CharField()
```

## Rentalizer Response Serializer (Full)
```python
class RentalizerEstimateResponseSerializer(serializers.Serializer):
    payload = PayloadSerializer(source="*")

class PayloadSerializer(serializers.Serializer):
    details = DetailsSerializer()
    location = LocationSerializer()
    stats = StatsSerializer()

class StatsSerializer(serializers.Serializer):
    future = FutureSerializer()
    property_value = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)

class FutureSerializer(serializers.Serializer):
    metrics = MetricsSerializer(many=True)
    summary = SummarySerializer()

class MetricsSerializer(serializers.Serializer):
    adr = serializers.DecimalField(decimal_places=2, max_digits=17)
    date = serializers.CharField()
    occupancy = serializers.DecimalField(decimal_places=2, max_digits=3)
    revenue = serializers.IntegerField()
    revenue_lower = serializers.IntegerField()
    revenue_upper = serializers.IntegerField()
```

## Dependencies
- `generic-api` (GuestReady's internal REST framework)
- Django REST Framework serializers

## Key Insight
The Rentalizer response includes `revenue_lower` and `revenue_upper` — confidence intervals that AirDNA doesn't prominently show in the UI. Also includes `property_value` estimate.
