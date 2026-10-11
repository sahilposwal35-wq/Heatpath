"""
Pydantic request/response schemas for HeatPath API.
All coordinates are validated against the pilot area bounding box.
"""
from __future__ import annotations

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime

from app.config import settings


# ── Request schemas ───────────────────────────────────────────────────────────

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")

    @field_validator("lat")
    @classmethod
    def lat_in_pilot_area(cls, v: float) -> float:
        # Warn but don't reject — routing will simply fail if outside coverage
        return v

    @field_validator("lon")
    @classmethod
    def lon_in_pilot_area(cls, v: float) -> float:
        return v


class RouteRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    # ISO 8601 datetime string (e.g. "2026-10-10T14:30:00+05:30")
    departure_time: str = Field(
        ...,
        description="ISO 8601 datetime with timezone (e.g. '2026-10-10T14:30:00+05:30')",
    )
    profile: Literal["faster", "balanced", "exposure"] = Field(
        "balanced",
        description=(
            "Route preference: 'faster' (minimize time), "
            "'balanced' (balance time and exposure), "
            "'exposure' (minimize estimated heat exposure)"
        ),
    )

    @field_validator("departure_time")
    @classmethod
    def validate_departure_time(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(
                "departure_time must be a valid ISO 8601 datetime string "
                "(e.g. '2026-10-10T14:30:00+05:30')"
            )
        return v

    @model_validator(mode="after")
    def origin_destination_differ(self) -> "RouteRequest":
        if (
            abs(self.origin.lat - self.destination.lat) < 1e-5
            and abs(self.origin.lon - self.destination.lon) < 1e-5
        ):
            raise ValueError("Origin and destination must be different locations.")
        return self


# ── Response schemas ──────────────────────────────────────────────────────────

class ScoreComponents(BaseModel):
    alpha_time: float = Field(..., description="Profile-weighted time component of route cost")
    beta_exposure: float = Field(..., description="Profile-weighted exposure component")
    gamma_distance: float = Field(..., description="Profile-weighted distance component")


class RouteResult(BaseModel):
    route_index: int
    label: str = Field(..., description="e.g. 'Fastest', 'Heat-aware', 'Alternative 2'")
    distance_m: float = Field(..., description="Route distance in metres")
    duration_s: float = Field(..., description="Estimated walking duration in seconds")
    distance_km: float = Field(..., description="Route distance in kilometres (rounded)")
    duration_min: float = Field(..., description="Estimated walking duration in minutes (rounded)")

    # Exposure score fields
    avg_exposure_score: float = Field(
        ...,
        description=(
            "Duration-weighted average segment exposure proxy (0=low, 1=high). "
            "Relative model estimate, not measured temperature."
        ),
    )
    cumulative_exposure_score: float = Field(
        ...,
        description="Cumulative exposure proxy for the full route (0–1).",
    )
    route_cost: float = Field(
        ...,
        description="Combined route objective cost for ranking (profile-weighted, 0–1).",
    )
    score_components: ScoreComponents
    data_coverage: float = Field(
        ...,
        description="Fraction of route duration covered by segments with sufficient data (0–1).",
    )
    data_confidence: Literal["high", "medium", "low"]

    # Comparison
    is_recommended: bool
    extra_minutes_vs_fastest: Optional[float] = Field(
        None,
        description="Additional minutes vs fastest route. None for the fastest route itself.",
    )
    model_score_reduction_pct: Optional[float] = Field(
        None,
        description=(
            "Estimated model-score reduction vs fastest route (%). "
            "Label: 'estimated model-score reduction', NOT 'percent less heat experienced'."
        ),
    )

    # Explanation and geometry
    explanation: str
    geometry: list[list[float]] = Field(
        ...,
        description="GeoJSON coordinate pairs [[lon, lat], ...] for the route line.",
    )
    data_source: str = Field(..., description="'live', 'cached', or 'sample'")
    missing_features: list[str] = Field(
        default_factory=list,
        description="Features not available for this route's scoring.",
    )


class WeatherInfo(BaseModel):
    temperature_c: Optional[float]
    apparent_temperature_c: Optional[float]
    uv_index: Optional[float]
    cloud_cover_pct: Optional[float]
    wind_speed_kmh: Optional[float]
    retrieved_at_utc: str
    data_source: str
    grid_resolution_note: str


class SolarInfo(BaseModel):
    elevation_deg: float
    azimuth_deg: float
    is_daylight: bool
    irradiance_proxy: float
    calculated_for_utc: str


class RouteResponse(BaseModel):
    routes: list[RouteResult]
    weather: Optional[WeatherInfo]
    solar_at_origin: Optional[SolarInfo]
    departure_time_utc: str
    pilot_area_name: str = "Pune — Shivajinagar / Deccan pilot area"
    score_formula_note: str = (
        "Scores are relative exposure proxies computed from available data. "
        "They are not measured temperatures or validated physiological heat stress values. "
        "Model: segment_exposure = clamp(w_sun*sun + w_uv*uv + w_weather*weather, 0, 1). "
        "Route cost = α*norm_time + β*avg_exposure + γ*norm_dist (profile-weighted)."
    )
    attribution: str = (
        "Map/routing data © OpenStreetMap contributors (ODbL) | "
        "Routing: Valhalla (MIT) | "
        "Weather: Open-Meteo.com (CC BY 4.0)"
    )


# ── Health / status schemas ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    app_name: str


class DataStatusResponse(BaseModel):
    routing: dict[str, Any]
    weather: dict[str, Any]
    solar: dict[str, Any]
    pilot_area: dict[str, Any]


class AreaResponse(BaseModel):
    name: str
    description: str
    bbox: dict[str, float]
    center: dict[str, float]
    example_pairs: list[dict[str, Any]]
    data_sources: list[str]
    limitations: list[str]


class GeocodeResult(BaseModel):
    name: str
    display_name: str
    lat: float
    lon: float
