"""
Valhalla routing adapter.

Uses the public Valhalla instance at valhalla1.openstreetmap.de.
Decodes encoded polyline (precision 6) to lat/lon coordinate pairs.
Returns up to 3 pedestrian route alternatives.

Attribution: Routing by Valhalla / OpenStreetMap (MIT License)
Terms: Non-commercial demo use; attribution required.
"""
from __future__ import annotations

import math
import httpx
from typing import Optional
from dataclasses import dataclass, field

from app.config import settings
# Polyline decoding (precision 6)

def decode_polyline6(encoded: str) -> list[tuple[float, float]]:
    """
    Decode a Valhalla-encoded polyline (precision 6) to list of (lat, lon) tuples.

    Valhalla uses precision 6 (1e-6 degrees), unlike Google which uses precision 5.
    """
    coords: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    n = len(encoded)

    while index < n:
        # Decode latitude
        result = 0
        shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        # Decode longitude
        result = 0
        shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng

        coords.append((lat * 1e-6, lng * 1e-6))

    return coords


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two lat/lon points (Haversine formula)."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
# Route models

@dataclass
class RouteSegment:
    """A single segment between two consecutive shape points."""
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    length_m: float
    # Duration estimated proportionally from total route duration
    duration_s: float


@dataclass
class CandidateRoute:
    """A single pedestrian route returned by Valhalla."""
    route_index: int
    distance_m: float
    duration_s: float
    # GeoJSON-compatible coordinate pairs [[lon, lat], ...]
    geometry: list[list[float]]
    # Segments for scoring
    segments: list[RouteSegment]
    # Source: "live" or "sample"
    source: str = "live"
# Routing client

class ValhallaRoutingError(Exception):
    pass


async def get_pedestrian_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    max_alternatives: int = 2,
) -> list[CandidateRoute]:
    """
    Fetch up to (max_alternatives + 1) pedestrian routes from Valhalla.

    Args:
        origin_lat, origin_lon: Start point.
        dest_lat, dest_lon: End point.
        max_alternatives: Number of additional alternatives (0 = only fastest).

    Returns:
        List of CandidateRoute objects (main + alternatives).
        Raises ValhallaRoutingError on failure.

    Attribution: Routing data © OpenStreetMap contributors (ODbL);
                 Routing engine: Valhalla (MIT License)
    """
    url = f"{settings.valhalla_base_url}/route"
    payload = {
        "locations": [
            {"lon": origin_lon, "lat": origin_lat},
            {"lon": dest_lon, "lat": dest_lat},
        ],
        "costing": "pedestrian",
        "alternates": max_alternatives,
        "directions_options": {"units": "km"},
    }

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise ValhallaRoutingError("Routing service timed out. Using cached demo data.")
        except httpx.HTTPStatusError as e:
            raise ValhallaRoutingError(
                f"Routing service returned HTTP {e.response.status_code}."
            )
        except Exception as e:
            raise ValhallaRoutingError(f"Routing service unavailable: {e}")

    data = resp.json()

    # Collect main trip + alternates
    trips_raw: list[dict] = []
    main_trip = data.get("trip")
    if main_trip:
        trips_raw.append(main_trip)
    for alt in data.get("alternates", []):
        alt_trip = alt.get("trip")
        if alt_trip:
            trips_raw.append(alt_trip)

    if not trips_raw:
        raise ValhallaRoutingError("No routes returned by routing service.")

    routes: list[CandidateRoute] = []
    for idx, trip in enumerate(trips_raw[:3]):
        summary = trip.get("summary", {})
        distance_m = summary.get("length", 0) * 1000  # km → m
        duration_s = summary.get("time", 0)

        # Decode shape from first leg
        legs = trip.get("legs", [])
        if not legs:
            continue
        encoded_shape = legs[0].get("shape", "")
        if not encoded_shape:
            continue

        coords = decode_polyline6(encoded_shape)
        if len(coords) < 2:
            continue

        # Build GeoJSON-format geometry [[lon, lat], ...]
        geometry = [[lon, lat] for lat, lon in coords]

        # Build segments for scoring
        segments = _build_segments(coords, distance_m, duration_s)

        routes.append(
            CandidateRoute(
                route_index=idx,
                distance_m=distance_m,
                duration_s=duration_s,
                geometry=geometry,
                segments=segments,
                source="live",
            )
        )

    return routes


def _build_segments(
    coords: list[tuple[float, float]],
    total_distance_m: float,
    total_duration_s: float,
) -> list[RouteSegment]:
    """
    Split decoded coordinates into segments with estimated duration.

    Duration per segment estimated proportionally to length (uniform walking speed assumption).
    This is a simplification — actual walking speed varies, but is appropriate for
    this MVP's relative comparison.
    """
    if len(coords) < 2:
        return []

    segments: list[RouteSegment] = []
    seg_lengths: list[float] = []

    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        seg_len = haversine_m(lat1, lon1, lat2, lon2)
        seg_lengths.append(seg_len)

    computed_total = sum(seg_lengths) or total_distance_m or 1.0

    for i, (seg_len) in enumerate(seg_lengths):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        # Proportional duration
        seg_dur = (seg_len / computed_total) * total_duration_s
        segments.append(
            RouteSegment(
                start_lat=lat1,
                start_lon=lon1,
                end_lat=lat2,
                end_lon=lon2,
                length_m=seg_len,
                duration_s=seg_dur,
            )
        )

    return segments
