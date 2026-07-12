"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)
    bedrooms: int = Field(ge=0, le=10, default=1)
    bathrooms: float = Field(ge=0, le=10, default=1.0)
    accommodates: int = Field(ge=1, le=20, default=2)
    nightly_rate: float = Field(gt=0, le=10000, default=150)
    property_type: str = Field(default="Entire home/apt")
    minimum_nights: int = Field(ge=1, le=365, default=1)
    is_superhost: bool = Field(default=False)
    host_listings_count: int = Field(ge=1, le=1000, default=1)


class ConfidenceResponse(BaseModel):
    level: str
    revenue_lower: float
    revenue_upper: float
    cv: float


class CompResponse(BaseModel):
    distance_km: float
    bedrooms: int
    revenue: float
    similarity_score: float
    borough: str


class MarketResponse(BaseModel):
    borough: str
    median_revenue: float
    median_price: float
    active_listings: int


class EstimateResponse(BaseModel):
    address: str
    lat: float
    lng: float
    annual_revenue: float
    confidence: ConfidenceResponse
    comps: list[CompResponse]
    market: MarketResponse
    disclaimer: str
    data_source: str
    model_version: str
    data_freshness: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    suggestion: str = ""


class HealthResponse(BaseModel):
    status: str


class ModelInfoResponse(BaseModel):
    model_type: str
    version: str
    n_features: int
    metrics: dict


class CreditsResponse(BaseModel):
    data_source: str
    license: str
    license_url: str
    attribution: str
