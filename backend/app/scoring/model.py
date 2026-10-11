"""Exposure scoring and route ranking model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SegmentFeatures:
    """
    Environmental features for one route segment.

    All normalized values are in [0, 1].
    None = feature unavailable for this segment.
    """
    # Geometry
    length_m: float  # segment length in metres
    duration_s: float  # estimated walking time in seconds

    # Solar
    solar_elevation_deg: Optional[float] = None  # degrees above horizon
    # Normalized solar intensity proxy: sin(elevation) when daytime, 0 at night
    sun_factor: Optional[float] = None  # 0 (no sun) → 1 (zenith, full exposure)

    # Weather (area-wide, from Open-Meteo grid — not street-level)
    uv_index: Optional[float] = None  # 0–11+
    uv_factor: Optional[float] = None  # normalized 0–1 from uv_index
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    cloud_cover_pct: Optional[float] = None  # 0–100
    weather_factor: Optional[float] = None  # normalized weather severity 0–1

    # Vegetation/canopy (unavailable in this pilot — future work)
    canopy_proxy: Optional[float] = None  # 0=no canopy, 1=full canopy; None=unknown

    # Data quality
    features_available: list[str] = field(default_factory=list)
    features_missing: list[str] = field(default_factory=list)


@dataclass
class SegmentScore:
    """Computed exposure score for one segment."""
    exposure: float  # clamped 0–1
    confidence: float  # 0–1 (fraction of weighted features that were available)
    components: dict[str, float]  # per-feature contribution
    missing: list[str]


@dataclass
class RouteMetrics:
    """Aggregated score metrics for an entire route."""
    distance_m: float
    duration_s: float
    # Average segment exposure weighted by segment duration
    avg_exposure: float  # 0–1
    # Total cumulative exposure cost (sum of exposure * duration_fraction)
    cumulative_exposure: float  # 0–1 (normalized against route duration)
    # Data coverage: fraction of route duration covered by full-feature segments
    data_coverage: float  # 0–1
    # Route objective score (for ranking with profile weights)
    route_cost: float  # 0–1
    confidence: str  # "high" | "medium" | "low"
    score_components: dict[str, float]
# Segment and profile weights

# Per-segment exposure weights — must sum to 1.0
SEGMENT_WEIGHTS = {
    "sun": 0.50,     # solar irradiance proxy (elevation-based)
    "uv": 0.30,      # UV index (directly measures ultraviolet radiation)
    "weather": 0.20, # temperature + apparent temperature composite
}

# Route objective weights per profile
PROFILE_WEIGHTS = {
    "faster": {"alpha": 0.70, "beta": 0.20, "gamma": 0.10},
    "balanced": {"alpha": 0.40, "beta": 0.40, "gamma": 0.20},
    "exposure": {"alpha": 0.20, "beta": 0.65, "gamma": 0.15},
}

# Maximum detour allowed vs fastest route (for exposure profile)
MAX_DETOUR_FACTOR = 1.40  # 40% extra time vs fastest


def normalize_uv(uv_index: float) -> float:
    """
    Normalize UV index to 0–1.
    UV ≥ 11 is extreme (1.0). Scale is roughly logarithmic in health impact
    but we use a simple linear cap for transparency.
    """
    return min(1.0, max(0.0, uv_index / 11.0))


def normalize_weather(
    temperature_c: Optional[float],
    apparent_temperature_c: Optional[float],
    cloud_cover_pct: Optional[float],
) -> Optional[float]:
    """
    Composite weather severity factor normalized to 0–1.

    Components:
    - Apparent temperature severity (> 25°C starts scaling up; 45°C+ = 1.0)
    - Cloud cover inverse (100% cloud = 0 solar, 0% cloud = 1.0 solar)

    Returns None if all inputs are missing.
    """
    parts: list[float] = []
    weights: list[float] = []

    # Use apparent temperature preferentially, fall back to dry-bulb
    temp = apparent_temperature_c if apparent_temperature_c is not None else temperature_c
    if temp is not None:
        # Severity: 25°C baseline, 45°C = max
        temp_factor = max(0.0, min(1.0, (temp - 25.0) / 20.0))
        parts.append(temp_factor)
        weights.append(0.7)

    if cloud_cover_pct is not None:
        # High cloud cover reduces solar load
        cloud_factor = 1.0 - (cloud_cover_pct / 100.0)
        parts.append(cloud_factor)
        weights.append(0.3)

    if not parts:
        return None

    total_w = sum(weights)
    return sum(p * w for p, w in zip(parts, weights)) / total_w


def score_segment(features: SegmentFeatures) -> SegmentScore:
    """
    Compute a normalized exposure score for a single route segment.

    Missing features: weight is redistributed proportionally to available features.
    If ALL features are missing, returns exposure=0.5 with confidence=0.0
    (indicating maximum uncertainty, not zero exposure).
    """
    components: dict[str, float] = {}
    available_weights: dict[str, float] = {}
    missing: list[str] = []

    if features.sun_factor is not None:
        available_weights["sun"] = SEGMENT_WEIGHTS["sun"]
        components["sun"] = features.sun_factor
    else:
        missing.append("solar_position")

    if features.uv_factor is not None:
        available_weights["uv"] = SEGMENT_WEIGHTS["uv"]
        components["uv"] = features.uv_factor
    else:
        missing.append("uv_index")

    if features.weather_factor is not None:
        available_weights["weather"] = SEGMENT_WEIGHTS["weather"]
        components["weather"] = features.weather_factor
    else:
        missing.append("weather")

    # If all missing, fallback to neutral score with zero confidence
    total_available_w = sum(available_weights.values())
    if total_available_w == 0:
        return SegmentScore(
            exposure=0.5,  # Unknown, not zero — use midpoint with zero confidence
            confidence=0.0,
            components={},
            missing=missing,
        )

    # Redistribute weights to available features
    score_raw = sum(
        components[k] * (w / total_available_w)
        for k, w in available_weights.items()
    )

    exposure = max(0.0, min(1.0, score_raw))
    confidence = total_available_w  # fraction of potential weight that was available

    return SegmentScore(
        exposure=exposure,
        confidence=confidence,
        components=components,
        missing=missing,
    )


def aggregate_route_scores(
    segment_scores: list[SegmentScore],
    segment_features: list[SegmentFeatures],
    profile: str = "balanced",
    fastest_duration_s: Optional[float] = None,
    fastest_distance_m: Optional[float] = None,
) -> RouteMetrics:
    """
    Aggregate segment scores into route-level metrics.

    Uses duration-weighted average for avg_exposure.
    Cumulative exposure = sum(segment_exposure * segment_duration / total_duration).
    Data coverage = sum(duration of high-confidence segments) / total_duration.
    Route cost = alpha*norm_time + beta*avg_exposure + gamma*norm_dist (profile weights).
    """
    if not segment_scores:
        return RouteMetrics(
            distance_m=0,
            duration_s=0,
            avg_exposure=0.5,
            cumulative_exposure=0.5,
            data_coverage=0.0,
            route_cost=0.5,
            confidence="low",
            score_components={},
        )

    total_duration = sum(f.duration_s for f in segment_features)
    total_distance = sum(f.length_m for f in segment_features)

    if total_duration == 0:
        return RouteMetrics(
            distance_m=total_distance,
            duration_s=0,
            avg_exposure=0.5,
            cumulative_exposure=0.5,
            data_coverage=0.0,
            route_cost=0.5,
            confidence="low",
            score_components={},
        )

    # Duration-weighted average exposure
    weighted_exposure = sum(
        s.exposure * f.duration_s
        for s, f in zip(segment_scores, segment_features)
    )
    avg_exposure = weighted_exposure / total_duration

    # Cumulative exposure proxy (already normalized 0–1 per segment)
    cumulative_exposure = avg_exposure  # same formula; kept distinct for future

    # Data coverage: fraction of walk time with confidence ≥ 0.5
    covered_duration = sum(
        f.duration_s
        for s, f in zip(segment_scores, segment_features)
        if s.confidence >= 0.5
    )
    data_coverage = covered_duration / total_duration

    # Route objective cost
    w = PROFILE_WEIGHTS.get(profile, PROFILE_WEIGHTS["balanced"])
    alpha = w["alpha"]
    beta = w["beta"]
    gamma = w["gamma"]

    # Normalize time and distance against baseline (fastest route)
    # If no baseline provided, use this route as its own reference (normalized to 0.5)
    norm_time = (
        total_duration / fastest_duration_s
        if fastest_duration_s and fastest_duration_s > 0
        else 0.5
    )
    norm_dist = (
        total_distance / fastest_distance_m
        if fastest_distance_m and fastest_distance_m > 0
        else 0.5
    )

    # Clamp normalized values (prevents absurd detour routes from skewing score)
    norm_time = min(norm_time, MAX_DETOUR_FACTOR)
    norm_dist = min(norm_dist, MAX_DETOUR_FACTOR)

    # Normalize to 0–1 range
    norm_time_01 = norm_time / MAX_DETOUR_FACTOR
    norm_dist_01 = norm_dist / MAX_DETOUR_FACTOR

    route_cost = (
        alpha * norm_time_01
        + beta * avg_exposure
        + gamma * norm_dist_01
    )
    route_cost = max(0.0, min(1.0, route_cost))

    # Confidence label
    if data_coverage >= 0.7:
        confidence_label = "high"
    elif data_coverage >= 0.4:
        confidence_label = "medium"
    else:
        confidence_label = "low"

    return RouteMetrics(
        distance_m=total_distance,
        duration_s=total_duration,
        avg_exposure=round(avg_exposure, 4),
        cumulative_exposure=round(cumulative_exposure, 4),
        data_coverage=round(data_coverage, 3),
        route_cost=round(route_cost, 4),
        confidence=confidence_label,
        score_components={
            "alpha_time": round(alpha * norm_time_01, 4),
            "beta_exposure": round(beta * avg_exposure, 4),
            "gamma_distance": round(gamma * norm_dist_01, 4),
        },
    )


def exposure_reduction_pct(
    baseline_score: float, recommended_score: float
) -> Optional[float]:
    """
    Calculate estimated model-score reduction percentage.

    IMPORTANT LABEL: This is 'estimated model-score reduction', NOT
    'percent less heat experienced'. Do not display if baseline is 0
    or routes are not comparable.

    Returns None if calculation is not meaningful.
    """
    if baseline_score <= 0:
        return None
    if baseline_score == recommended_score:
        return 0.0
    reduction = 100.0 * (baseline_score - recommended_score) / baseline_score
    return round(reduction, 1)
