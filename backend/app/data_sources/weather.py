"""
Open-Meteo weather data adapter.

Attribution: Weather data from Open-Meteo.com (CC BY 4.0)
Terms: Free for non-commercial use; no API key required.
URL: https://open-meteo.com

Important limitations:
- Grid resolution ~1 km — does NOT represent individual street microclimates.
- Applied as area-wide weather context, not per-segment ground truth.
- UV index is a radiation proxy, not precise MRT or WBGT.
"""
from __future__ import annotations

import httpx
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config import settings


@dataclass
class WeatherConditions:
    """
    Weather conditions for a pilot area at a given time.

    Source: Open-Meteo forecast API.
    Resolution: ~1 km grid — area-wide context only.
    """
    temperature_c: Optional[float]
    apparent_temperature_c: Optional[float]
    cloud_cover_pct: Optional[float]
    uv_index: Optional[float]
    wind_speed_kmh: Optional[float]
    # Metadata
    retrieved_at_utc: str
    data_source: str = "Open-Meteo (live)"
    is_live: bool = True
    grid_resolution_note: str = (
        "~1 km grid — area-wide context, not street-level microclimate"
    )


class WeatherError(Exception):
    pass


async def get_current_weather(
    lat: float,
    lon: float,
    target_utc: Optional[datetime] = None,
) -> WeatherConditions:
    """
    Fetch current (or nearest-hour) weather from Open-Meteo for the given location.

    Args:
        lat, lon: Coordinates (typically pilot area centre).
        target_utc: If provided, attempt to retrieve the hourly value nearest to this time.
                    Falls back to current conditions if target is too far from now.

    Returns:
        WeatherConditions with available fields.
        Raises WeatherError on failure.
    """
    url = f"{settings.open_meteo_base_url}/forecast"
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": "temperature_2m,apparent_temperature,cloud_cover,uv_index,wind_speed_10m",
        "hourly": "temperature_2m,apparent_temperature,cloud_cover,uv_index",
        "forecast_days": 2,
        "timezone": settings.pilot_timezone,
    }

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise WeatherError("Weather service timed out.")
        except httpx.HTTPStatusError as e:
            raise WeatherError(f"Weather service returned HTTP {e.response.status_code}.")
        except Exception as e:
            raise WeatherError(f"Weather service unavailable: {e}")

    data = resp.json()
    now_utc = datetime.now(timezone.utc)
    retrieved_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Try to match hourly forecast nearest to target departure time
    if target_utc is not None:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if times:
            # Find nearest hour index
            best_idx = _nearest_hour_index(times, target_utc)
            if best_idx is not None:
                return WeatherConditions(
                    temperature_c=_safe_float(hourly.get("temperature_2m", []), best_idx),
                    apparent_temperature_c=_safe_float(
                        hourly.get("apparent_temperature", []), best_idx
                    ),
                    cloud_cover_pct=_safe_float(hourly.get("cloud_cover", []), best_idx),
                    uv_index=_safe_float(hourly.get("uv_index", []), best_idx),
                    wind_speed_kmh=None,  # not in hourly params
                    retrieved_at_utc=retrieved_at,
                    data_source="Open-Meteo (hourly forecast)",
                    is_live=True,
                )

    # Fall back to current conditions
    current = data.get("current", {})
    return WeatherConditions(
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        cloud_cover_pct=current.get("cloud_cover"),
        uv_index=current.get("uv_index"),
        wind_speed_kmh=current.get("wind_speed_10m"),
        retrieved_at_utc=retrieved_at,
        data_source="Open-Meteo (current)",
        is_live=True,
    )


def _safe_float(lst: list, idx: int) -> Optional[float]:
    try:
        val = lst[idx]
        return float(val) if val is not None else None
    except (IndexError, TypeError, ValueError):
        return None


def _nearest_hour_index(times: list[str], target_utc: datetime) -> Optional[int]:
    """Find the index of the time string nearest to target_utc."""
    try:
        best_idx = 0
        best_diff = float("inf")
        for i, t in enumerate(times):
            # Times from Open-Meteo are local; parse as naive then treat as pilot-tz
            # For comparison we use a simple string heuristic
            try:
                dt = datetime.fromisoformat(t)
                # Approximate UTC offset for IST
                dt_approx_utc = dt.replace(tzinfo=None)
                target_naive = target_utc.replace(tzinfo=None)
                diff = abs((target_naive - dt_approx_utc).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
            except ValueError:
                continue
        return best_idx if best_diff < 86400 else None
    except Exception:
        return None
