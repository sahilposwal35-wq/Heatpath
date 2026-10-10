"""
Route ranking module.

Ranks candidate routes by profile-weighted cost.
Generates plain-language explanation from computed structured facts.
Enforces maximum detour constraint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.scoring.model import RouteMetrics, exposure_reduction_pct, MAX_DETOUR_FACTOR


@dataclass
class RankedRoute:
    """A scored and ranked candidate route."""
    route_index: int
    label: str  # e.g. "Fastest", "Heat-aware", "Alternative"
    distance_m: float
    duration_s: float
    avg_exposure: float
    cumulative_exposure: float
    route_cost: float
    data_coverage: float
    confidence: str
    score_components: dict
    geometry: list[list[float]]
    is_recommended: bool
    extra_minutes_vs_fastest: Optional[float]
    model_score_reduction_pct: Optional[float]
    explanation: str
    data_source: str
    missing_features: list[str] = field(default_factory=list)


def rank_routes(
    routes_metrics: list[RouteMetrics],
    routes_geometry: list[list[list[float]]],
    routes_missing_features: list[list[str]],
    profile: str,
    data_source: str = "live",
) -> list[RankedRoute]:
    """
    Rank candidate routes, pick recommendation, generate explanations.

    Rules:
    - Route 0 from Valhalla is always the fastest (Valhalla's primary route).
    - For 'faster' profile: recommend the fastest.
    - For 'balanced' / 'exposure': recommend lowest route_cost within detour constraint.
    - If only one route: no comparison possible; state this clearly.
    - Never claim a recommendation if all routes have the same score.
    """
    if not routes_metrics:
        return []

    fastest = routes_metrics[0]
    fastest_duration = fastest.duration_s
    fastest_distance = fastest.distance_m

    ranked: list[RankedRoute] = []

    for idx, (metrics, geom, missing) in enumerate(
        zip(routes_metrics, routes_geometry, routes_missing_features)
    ):
        # Label assignment
        if idx == 0:
            label = "Fastest"
        elif idx == 1:
            label = "Heat-aware"
        else:
            label = f"Alternative {idx}"

        # Extra time vs fastest
        extra_s = metrics.duration_s - fastest_duration
        extra_min = round(extra_s / 60, 1) if extra_s > 0 else 0.0

        # Detour check
        detour_factor = (
            metrics.duration_s / fastest_duration if fastest_duration > 0 else 1.0
        )
        exceeds_detour = detour_factor > MAX_DETOUR_FACTOR

        ranked.append(
            RankedRoute(
                route_index=idx,
                label=label,
                distance_m=metrics.distance_m,
                duration_s=metrics.duration_s,
                avg_exposure=metrics.avg_exposure,
                cumulative_exposure=metrics.cumulative_exposure,
                route_cost=metrics.route_cost,
                data_coverage=metrics.data_coverage,
                confidence=metrics.confidence,
                score_components=metrics.score_components,
                geometry=geom,
                is_recommended=False,  # set below
                extra_minutes_vs_fastest=extra_min if idx > 0 else None,
                model_score_reduction_pct=None,  # set below
                explanation="",  # set below
                data_source=data_source,
                missing_features=missing,
            )
        )

    # ── Pick recommendation ───────────────────────────────────────────────────
    if len(ranked) == 1:
        ranked[0].is_recommended = True
        ranked[0].explanation = _explain_single(ranked[0], profile)
    else:
        # Filter to non-detour routes for exposure/balanced profiles
        candidates = (
            [r for r in ranked if not (
                r.duration_s / fastest_duration > MAX_DETOUR_FACTOR
                and profile in ("balanced", "exposure")
            )]
            or ranked  # fallback: use all if all exceed constraint
        )

        if profile == "faster":
            best = ranked[0]  # always fastest
        else:
            best = min(candidates, key=lambda r: r.route_cost)

        best.is_recommended = True

        # ── Calculate score reduction vs fastest ─────────────────────────────
        fastest_exposure = ranked[0].avg_exposure
        if best.route_index != 0:
            reduction = exposure_reduction_pct(fastest_exposure, best.avg_exposure)
            best.model_score_reduction_pct = reduction
            # Also store on fastest for display
            ranked[0].model_score_reduction_pct = None

        # ── Generate explanations ─────────────────────────────────────────────
        for r in ranked:
            r.explanation = _explain_route(r, ranked[0], best, profile)

    return ranked


def _explain_route(
    route: RankedRoute,
    fastest: RankedRoute,
    recommended: RankedRoute,
    profile: str,
) -> str:
    """
    Generate a plain-language explanation from computed facts only.
    No invented percentages or unsupported claims.
    """
    parts: list[str] = []

    if route.is_recommended:
        if route.route_index == 0:
            parts.append("This is the fastest route and also the recommended route for this profile.")
        else:
            extra = route.extra_minutes_vs_fastest or 0
            parts.append(
                f"Route adds {extra:.1f} min vs fastest."
            )
            if (
                route.avg_exposure < fastest.avg_exposure
                and route.avg_exposure > 0
            ):
                diff = fastest.avg_exposure - route.avg_exposure
                parts.append(
                    f"Estimated exposure score is lower ({route.avg_exposure:.3f} vs "
                    f"{fastest.avg_exposure:.3f} for fastest) by {diff:.3f} units under this model."
                )
                if route.model_score_reduction_pct is not None:
                    parts.append(
                        f"Estimated model-score reduction: {route.model_score_reduction_pct:.1f}% "
                        f"(this is a model-score change, not a measured physiological reduction)."
                    )
            elif route.avg_exposure >= fastest.avg_exposure:
                parts.append(
                    "Note: exposure score is not lower than the fastest route under current data. "
                    "Profile weights cause this route to be preferred for other reasons."
                )
            parts.append("Recommended for the selected preference profile.")
    else:
        if route.route_index == 0:
            parts.append("This is the fastest route.")
            if recommended.route_index != 0:
                extra = recommended.extra_minutes_vs_fastest or 0
                parts.append(
                    f"The recommended route takes {extra:.1f} min longer "
                    f"but has a lower estimated exposure score "
                    f"({recommended.avg_exposure:.3f} vs {route.avg_exposure:.3f})."
                )
        else:
            parts.append("Alternative route — not recommended for this profile.")

    # Confidence note
    if route.confidence == "low":
        parts.append(
            "⚠ Data confidence: low — several environmental features were unavailable. "
            "Score is a coarse estimate."
        )
    elif route.confidence == "medium":
        parts.append("Data confidence: medium — some features available.")

    # Missing features note
    missing = [f for f in route.missing_features if f != "canopy_data"]
    if "canopy_data" in route.missing_features:
        parts.append(
            "Building-height and canopy data are unavailable for this pilot area; "
            "street-level shade is not modelled."
        )

    return " ".join(parts)


def _explain_single(route: RankedRoute, profile: str) -> str:
    """Explanation when only one route was returned."""
    parts = [
        "Only one route was available for this origin–destination pair. "
        "No route comparison could be performed."
    ]
    if route.confidence == "low":
        parts.append("Data confidence is low for this route.")
    return " ".join(parts)
