"""
Segment feature builder.

Combines routing geometry, solar position, and weather data into
SegmentFeatures objects ready for the scoring model.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.routing.valhalla import RouteSegment
from app.solar.calculator import SolarCalculator
from app.scoring.model import (
    SegmentFeatures,
    normalize_uv,
    normalize_weather,
)
from app.data_sources.weather import WeatherConditions


def build_segment_features(
    segment: RouteSegment,
    utc_dt: datetime,
    weather: Optional[WeatherConditions],
) -> SegmentFeatures:
    """
    Attach environmental features to a route segment.

    Solar position is calculated from segment midpoint coordinates and UTC time.
    Weather is area-wide (from Open-Meteo grid) — not street-level.

    Missing features are represented as None, never silently zeroed.
    """
    # ── Midpoint of segment ───────────────────────────────────────────────────
    mid_lat = (segment.start_lat + segment.end_lat) / 2
    mid_lon = (segment.start_lon + segment.end_lon) / 2

    features_available: list[str] = []
    features_missing: list[str] = []

    # ── Solar position ────────────────────────────────────────────────────────
    solar_elevation_deg: Optional[float] = None
    sun_factor: Optional[float] = None
    try:
        solar = SolarCalculator.calculate(mid_lat, mid_lon, utc_dt)
        solar_elevation_deg = solar.elevation_deg
        sun_factor = solar.irradiance_proxy  # sin(elevation), 0 when below horizon
        features_available.append("solar_elevation")
    except Exception:
        features_missing.append("solar_elevation")

    # ── Weather ───────────────────────────────────────────────────────────────
    uv_index: Optional[float] = None
    uv_factor: Optional[float] = None
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    weather_factor: Optional[float] = None

    if weather is not None:
        if weather.uv_index is not None:
            uv_index = weather.uv_index
            uv_factor = normalize_uv(uv_index)
            features_available.append("uv_index")
        else:
            features_missing.append("uv_index")

        temperature_c = weather.temperature_c
        apparent_temperature_c = weather.apparent_temperature_c
        cloud_cover_pct = weather.cloud_cover_pct

        wf = normalize_weather(temperature_c, apparent_temperature_c, cloud_cover_pct)
        if wf is not None:
            weather_factor = wf
            features_available.append("weather_composite")
        else:
            features_missing.append("weather_composite")
    else:
        features_missing.extend(["uv_index", "weather_composite"])

    # Note: canopy/vegetation data not available for this pilot area
    features_missing.append("canopy_data")

    return SegmentFeatures(
        length_m=segment.length_m,
        duration_s=segment.duration_s,
        solar_elevation_deg=solar_elevation_deg,
        sun_factor=sun_factor,
        uv_index=uv_index,
        uv_factor=uv_factor,
        temperature_c=temperature_c,
        apparent_temperature_c=apparent_temperature_c,
        cloud_cover_pct=cloud_cover_pct,
        weather_factor=weather_factor,
        canopy_proxy=None,  # Not available — future work
        features_available=features_available,
        features_missing=features_missing,
    )
