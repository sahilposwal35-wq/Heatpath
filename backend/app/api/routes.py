"""
FastAPI route handlers.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

# Add project root to path for sample data
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from app.config import settings
from app.schemas.routes import (
    RouteRequest, RouteResponse, RouteResult, WeatherInfo, SolarInfo,
    HealthResponse, DataStatusResponse, AreaResponse, ScoreComponents,
)
from app.routing.valhalla import get_pedestrian_routes, ValhallaRoutingError
from app.routing.ranker import rank_routes
from app.data_sources.weather import get_current_weather, WeatherError
from app.solar.calculator import SolarCalculator
from app.geospatial.features import build_segment_features
from app.scoring.model import score_segment, aggregate_route_scores
from app.aws.cloudwatch import log_route_query_to_cloudwatch

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.version,
        app_name=settings.app_name,
    )


@router.get("/api/area", response_model=AreaResponse, tags=["Info"])
async def get_area():
    """Return supported pilot area details and example origin/destination pairs."""
    return AreaResponse(
        name="Pune — Shivajinagar / Deccan pilot area",
        description=(
            "A small walkable area in central Pune, Maharashtra, India. "
            "The area includes Shivajinagar, FC College Road, Deccan Gymkhana, "
            "and JM Road — streets with multiple viable pedestrian route alternatives."
        ),
        bbox={
            "lat_min": settings.pilot_lat_min,
            "lat_max": settings.pilot_lat_max,
            "lon_min": settings.pilot_lon_min,
            "lon_max": settings.pilot_lon_max,
        },
        center={
            "lat": settings.pilot_center_lat,
            "lon": settings.pilot_center_lon,
        },
        example_pairs=[
            {
                "name": "Shivajinagar to Deccan Gymkhana",
                "origin": {"lat": 18.5204, "lon": 73.8399},
                "destination": {"lat": 18.5074, "lon": 73.8479},
                "note": "~1.8–2.5 km walk; multiple route alternatives exist",
            },
            {
                "name": "FC College to Nal Stop",
                "origin": {"lat": 18.5220, "lon": 73.8440},
                "destination": {"lat": 18.5060, "lon": 73.8310},
                "note": "~2.5–3.5 km walk through residential and commercial streets",
            },
            {
                "name": "Pune Station to Shivajinagar",
                "origin": {"lat": 18.5293, "lon": 73.8743},
                "destination": {"lat": 18.5204, "lon": 73.8399},
                "note": "~5–6 km walk; longer route with more alternatives",
            },
        ],
        data_sources=[
            "OpenStreetMap pedestrian network (ODbL)",
            "Valhalla routing engine (MIT)",
            "Open-Meteo weather API (CC BY 4.0)",
            "Solar position calculation (standard spherical trigonometry)",
        ],
        limitations=[
            "Building-height and canopy data not available for shade modelling",
            "Weather is area-wide (~1 km grid), not street-level",
            "Solar position alone is used as sun-exposure proxy, not exact shade",
            "Route alternatives depend on Valhalla's algorithm — not all pairs return multiple alternatives",
        ],
    )


@router.get("/api/data-status", response_model=DataStatusResponse, tags=["Info"])
async def get_data_status():
    """Return current status and freshness of each data source."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Test weather connectivity
    weather_ok = False
    weather_msg = ""
    try:
        w = await get_current_weather(
            settings.pilot_center_lat, settings.pilot_center_lon
        )
        weather_ok = True
        weather_msg = f"Live — retrieved at {w.retrieved_at_utc}"
    except WeatherError as e:
        weather_msg = f"Unavailable: {e}"

    return DataStatusResponse(
        routing={
            "provider": "Valhalla (public instance)",
            "url": settings.valhalla_base_url,
            "status": "live (not pre-tested at status check time)",
            "attribution": "© OpenStreetMap contributors (ODbL) | Valhalla MIT",
            "supports_alternatives": True,
            "notes": "Rate-limited public demo instance",
        },
        weather={
            "provider": "Open-Meteo",
            "url": settings.open_meteo_base_url,
            "status": weather_msg if weather_ok else f"error: {weather_msg}",
            "is_live": weather_ok,
            "resolution": "~1 km grid",
            "attribution": "Weather data from Open-Meteo.com (CC BY 4.0)",
        },
        solar={
            "provider": "HeatPath solar calculator (built-in)",
            "algorithm": "Spencer 1971 Fourier approximation",
            "status": "always available",
            "accuracy_note": "±1–2° typical; suitable for relative comparison only",
        },
        pilot_area={
            "name": "Pune — Shivajinagar / Deccan",
            "bbox": {
                "lat_min": settings.pilot_lat_min,
                "lat_max": settings.pilot_lat_max,
                "lon_min": settings.pilot_lon_min,
                "lon_max": settings.pilot_lon_max,
            },
            "checked_at_utc": now_utc,
        },
    )


@router.post("/api/routes", response_model=RouteResponse, tags=["Routing"])
async def find_routes(request: RouteRequest):
    """
    Find and score pedestrian route alternatives.

    Returns candidate routes with distance, duration, exposure scores,
    data confidence, explanation, and recommendation.

    Scores are relative model proxies, not measured temperatures.
    Falls back to synthetic demo data if routing service is unavailable.
    """
    # ── Parse departure time ──────────────────────────────────────────────────
    try:
        departure_dt = datetime.fromisoformat(request.departure_time)
        if departure_dt.tzinfo is None:
            # Assume IST if no timezone provided
            from datetime import timedelta
            departure_dt = departure_dt.replace(
                tzinfo=timezone(timedelta(hours=5, minutes=30))
            )
        departure_utc = departure_dt.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="departure_time must be a valid ISO 8601 datetime.",
        )

    departure_utc_str = departure_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Fetch weather ─────────────────────────────────────────────────────────
    weather = None
    weather_info: Optional[WeatherInfo] = None
    try:
        weather = await get_current_weather(
            settings.pilot_center_lat,
            settings.pilot_center_lon,
            target_utc=departure_utc,
        )
        weather_info = WeatherInfo(
            temperature_c=weather.temperature_c,
            apparent_temperature_c=weather.apparent_temperature_c,
            uv_index=weather.uv_index,
            cloud_cover_pct=weather.cloud_cover_pct,
            wind_speed_kmh=weather.wind_speed_kmh,
            retrieved_at_utc=weather.retrieved_at_utc,
            data_source=weather.data_source,
            grid_resolution_note=weather.grid_resolution_note,
        )
    except WeatherError:
        # Weather unavailable — proceed without it; scores will reflect this
        pass

    # ── Solar at origin ───────────────────────────────────────────────────────
    solar_info: Optional[SolarInfo] = None
    try:
        solar = SolarCalculator.calculate(
            request.origin.lat, request.origin.lon, departure_utc
        )
        solar_info = SolarInfo(
            elevation_deg=round(solar.elevation_deg, 2),
            azimuth_deg=round(solar.azimuth_deg, 2),
            is_daylight=solar.is_daylight,
            irradiance_proxy=round(solar.irradiance_proxy, 4),
            calculated_for_utc=departure_utc_str,
        )
    except Exception:
        pass

    # ── Fetch routes ──────────────────────────────────────────────────────────
    data_source = "live"
    try:
        candidate_routes = await get_pedestrian_routes(
            origin_lat=request.origin.lat,
            origin_lon=request.origin.lon,
            dest_lat=request.destination.lat,
            dest_lon=request.destination.lon,
            max_alternatives=2,
        )
    except ValhallaRoutingError as e:
        # Fall back to sample data
        data_source = "sample"
        candidate_routes = _load_sample_routes()
        if not candidate_routes:
            raise HTTPException(
                status_code=503,
                detail=f"Routing unavailable and no sample data: {e}",
            )

    if not candidate_routes:
        raise HTTPException(
            status_code=404,
            detail="No routes found between the specified origin and destination.",
        )

    # ── Score each route ──────────────────────────────────────────────────────
    fastest = candidate_routes[0]
    all_metrics = []
    all_missing = []

    for route in candidate_routes:
        seg_features = [
            build_segment_features(seg, departure_utc, weather)
            for seg in route.segments
        ]
        seg_scores = [score_segment(f) for f in seg_features]

        metrics = aggregate_route_scores(
            seg_scores,
            seg_features,
            profile=request.profile,
            fastest_duration_s=fastest.duration_s,
            fastest_distance_m=fastest.distance_m,
        )
        all_metrics.append(metrics)

        # Collect unique missing features
        missing = list(
            dict.fromkeys(
                feat
                for f in seg_features
                for feat in f.features_missing
            )
        )
        all_missing.append(missing)

    # ── Rank routes ───────────────────────────────────────────────────────────
    geometries = [r.geometry for r in candidate_routes]
    ranked = rank_routes(
        all_metrics,
        geometries,
        all_missing,
        profile=request.profile,
        data_source=data_source,
    )

    # ── Build response ────────────────────────────────────────────────────────
    route_results = []
    for r in ranked:
        route_results.append(
            RouteResult(
                route_index=r.route_index,
                label=r.label,
                distance_m=round(r.distance_m, 1),
                duration_s=round(r.duration_s, 1),
                distance_km=round(r.distance_m / 1000, 2),
                duration_min=round(r.duration_s / 60, 1),
                avg_exposure_score=r.avg_exposure,
                cumulative_exposure_score=r.cumulative_exposure,
                route_cost=r.route_cost,
                score_components=ScoreComponents(**r.score_components),
                data_coverage=r.data_coverage,
                data_confidence=r.confidence,
                is_recommended=r.is_recommended,
                extra_minutes_vs_fastest=r.extra_minutes_vs_fastest,
                model_score_reduction_pct=r.model_score_reduction_pct,
                explanation=r.explanation,
                geometry=r.geometry,
                data_source=r.data_source,
                missing_features=r.missing_features,
            )
        )

    # ── Log telemetry to AWS CloudWatch ───────────────────────────────────────
    recommended_route = next((r for r in route_results if r.is_recommended), None)
    log_route_query_to_cloudwatch(
        origin=(request.origin.lat, request.origin.lon),
        destination=(request.destination.lat, request.destination.lon),
        profile=request.profile,
        num_routes=len(route_results),
        best_route_label=recommended_route.label if recommended_route else "N/A",
        time_saved_or_score_diff={
            "extra_minutes_vs_fastest": recommended_route.extra_minutes_vs_fastest if recommended_route else 0.0,
            "model_score_reduction_pct": recommended_route.model_score_reduction_pct if recommended_route else 0.0,
            "avg_exposure_score": recommended_route.avg_exposure_score if recommended_route else 0.0,
        },
    )

    return RouteResponse(
        routes=route_results,
        weather=weather_info,
        solar_at_origin=solar_info,
        departure_time_utc=departure_utc_str,
    )


def _load_sample_routes():
    """Load synthetic sample routes as CandidateRoute-like objects for fallback."""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from data.sample.pune_demo_routes import SAMPLE_ROUTES
        from app.routing.valhalla import CandidateRoute, RouteSegment

        routes = []
        for r_data in SAMPLE_ROUTES.get("routes", []):
            geom = r_data["geometry"]
            # Build minimal segments from geometry
            segs = []
            for i in range(len(geom) - 1):
                lon1, lat1 = geom[i]
                lon2, lat2 = geom[i + 1]
                from app.routing.valhalla import haversine_m
                seg_len = haversine_m(lat1, lon1, lat2, lon2)
                total_dur = r_data["duration_s"]
                total_dist = r_data["distance_m"] or 1
                seg_dur = (seg_len / total_dist) * total_dur
                segs.append(
                    RouteSegment(
                        start_lat=lat1, start_lon=lon1,
                        end_lat=lat2, end_lon=lon2,
                        length_m=seg_len, duration_s=seg_dur,
                    )
                )

            routes.append(
                CandidateRoute(
                    route_index=r_data["route_index"],
                    distance_m=r_data["distance_m"],
                    duration_s=r_data["duration_s"],
                    geometry=geom,
                    segments=segs,
                    source="sample",
                )
            )
        return routes
    except Exception:
        return []
