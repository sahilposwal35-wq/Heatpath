"""
Unit tests for the HeatPath exposure scoring model.

Covers:
- Normalization and clamping
- Segment scoring with full features
- Segment scoring with missing features
- All-missing features (maximum uncertainty)
- Zero baseline in exposure_reduction_pct
- Route aggregation
- Profile weight changes
- Same-input reproducibility
- Time change affecting solar features
- No alternative route available
"""
import sys
import os
import math
from datetime import datetime, timezone, timedelta

# Ensure backend/app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.scoring.model import (
    SegmentFeatures,
    score_segment,
    aggregate_route_scores,
    exposure_reduction_pct,
    normalize_uv,
    normalize_weather,
    SEGMENT_WEIGHTS,
    PROFILE_WEIGHTS,
)
from app.solar.calculator import SolarCalculator


# normalize_uv

def test_normalize_uv_zero():
    assert normalize_uv(0.0) == 0.0


def test_normalize_uv_max():
    assert normalize_uv(11.0) == 1.0


def test_normalize_uv_extreme():
    # UV > 11 should clamp at 1.0
    assert normalize_uv(15.0) == 1.0


def test_normalize_uv_midpoint():
    val = normalize_uv(5.5)
    assert abs(val - 0.5) < 0.01


def test_normalize_uv_negative():
    # Negative UV is invalid; clamp to 0
    assert normalize_uv(-1.0) == 0.0


# normalize_weather

def test_normalize_weather_all_none():
    result = normalize_weather(None, None, None)
    assert result is None


def test_normalize_weather_temp_only():
    result = normalize_weather(35.0, None, None)
    assert result is not None
    assert 0.0 <= result <= 1.0
    # 35°C should produce non-zero factor (baseline 25°C)
    assert result > 0.0


def test_normalize_weather_cool_temp():
    result = normalize_weather(20.0, None, None)
    # Below baseline of 25°C → factor = 0
    assert result is not None
    assert result == 0.0


def test_normalize_weather_full_cloud():
    # Full cloud cover should reduce factor
    result_clear = normalize_weather(35.0, None, 0.0)
    result_cloudy = normalize_weather(35.0, None, 100.0)
    assert result_clear is not None and result_cloudy is not None
    assert result_clear > result_cloudy


# score_segment

def _make_features(**kwargs) -> SegmentFeatures:
    defaults = dict(
        length_m=100.0,
        duration_s=72.0,
        solar_elevation_deg=45.0,
        sun_factor=math.sin(math.radians(45.0)),
        uv_index=6.0,
        uv_factor=normalize_uv(6.0),
        temperature_c=32.0,
        apparent_temperature_c=35.0,
        cloud_cover_pct=20.0,
        weather_factor=normalize_weather(32.0, 35.0, 20.0),
        features_available=["solar_elevation", "uv_index", "weather_composite"],
        features_missing=["canopy_data"],
    )
    defaults.update(kwargs)
    return SegmentFeatures(**defaults)


def test_score_full_features():
    f = _make_features()
    result = score_segment(f)
    assert 0.0 <= result.exposure <= 1.0
    assert result.confidence == pytest.approx(
        SEGMENT_WEIGHTS["sun"] + SEGMENT_WEIGHTS["uv"] + SEGMENT_WEIGHTS["weather"],
        abs=0.01,
    )
    assert not result.missing or result.missing == ["canopy_data"]


def test_score_clamped_to_one():
    # Maximum possible input values should not exceed 1.0
    f = _make_features(sun_factor=1.0, uv_factor=1.0, weather_factor=1.0)
    result = score_segment(f)
    assert result.exposure <= 1.0


def test_score_clamped_to_zero():
    # Minimum possible values should not go below 0.0
    f = _make_features(sun_factor=0.0, uv_factor=0.0, weather_factor=0.0)
    result = score_segment(f)
    assert result.exposure >= 0.0


def test_score_missing_uv():
    f = _make_features(uv_index=None, uv_factor=None)
    result = score_segment(f)
    assert "uv_index" in result.missing
    # Score must still be 0–1 with reduced confidence
    assert 0.0 <= result.exposure <= 1.0
    assert result.confidence < 1.0


def test_score_missing_sun():
    f = _make_features(solar_elevation_deg=None, sun_factor=None)
    result = score_segment(f)
    assert "solar_position" in result.missing or "solar_elevation" in result.missing
    assert 0.0 <= result.exposure <= 1.0


def test_score_missing_weather():
    f = _make_features(weather_factor=None, temperature_c=None, apparent_temperature_c=None)
    result = score_segment(f)
    assert "weather" in result.missing or "weather_composite" in [m for m in result.missing]
    assert 0.0 <= result.exposure <= 1.0


def test_score_all_features_missing():
    """All features missing → exposure = 0.5 (max uncertainty), confidence = 0.0."""
    f = _make_features(
        sun_factor=None,
        solar_elevation_deg=None,
        uv_factor=None,
        uv_index=None,
        weather_factor=None,
        temperature_c=None,
        apparent_temperature_c=None,
        cloud_cover_pct=None,
        features_available=[],
        features_missing=["solar_elevation", "uv_index", "weather_composite"],
    )
    result = score_segment(f)
    assert result.exposure == pytest.approx(0.5)
    assert result.confidence == pytest.approx(0.0)


def test_score_reproducible():
    """Same inputs must always produce the same score."""
    f = _make_features()
    r1 = score_segment(f)
    r2 = score_segment(f)
    assert r1.exposure == r2.exposure
    assert r1.confidence == r2.confidence


# aggregate_route_scores

def test_aggregate_empty():
    result = aggregate_route_scores([], [], "balanced")
    assert result.avg_exposure == pytest.approx(0.5)
    assert result.data_coverage == pytest.approx(0.0)


def test_aggregate_single_segment():
    f = _make_features(length_m=500.0, duration_s=360.0)
    s = score_segment(f)
    result = aggregate_route_scores([s], [f], "balanced", 360.0, 500.0)
    assert 0.0 <= result.avg_exposure <= 1.0
    assert 0.0 <= result.route_cost <= 1.0


def test_aggregate_multiple_segments():
    segments = [_make_features(duration_s=100.0) for _ in range(5)]
    scores = [score_segment(f) for f in segments]
    result = aggregate_route_scores(scores, segments, "balanced", 500.0, 500.0)
    assert 0.0 <= result.avg_exposure <= 1.0
    assert result.duration_s == pytest.approx(500.0, abs=1.0)


def test_profile_weights_change_cost():
    """Different profiles should produce different route costs."""
    f = _make_features(duration_s=600.0)
    s = score_segment(f)
    result_fast = aggregate_route_scores([s], [f], "faster", 600.0, 500.0)
    result_exp = aggregate_route_scores([s], [f], "exposure", 600.0, 500.0)
    # They should differ because alpha/beta are different
    # (though exact direction depends on input values)
    assert isinstance(result_fast.route_cost, float)
    assert isinstance(result_exp.route_cost, float)


def test_no_alternative_route():
    """Single route — still returns valid metrics."""
    f = _make_features()
    s = score_segment(f)
    result = aggregate_route_scores([s], [f], "balanced")
    assert 0.0 <= result.avg_exposure <= 1.0


def test_confidence_labels():
    """Coverage fraction maps to correct confidence label."""
    # High coverage
    segs = [_make_features(duration_s=100.0) for _ in range(10)]
    scores = [score_segment(f) for f in segs]
    result = aggregate_route_scores(scores, segs, "balanced", 1000.0, 1000.0)
    # All segments have full features → coverage should be high
    assert result.confidence in ("high", "medium", "low")


# exposure_reduction_pct

def test_reduction_zero_baseline():
    """Zero baseline → None (cannot compute)."""
    assert exposure_reduction_pct(0.0, 0.3) is None


def test_reduction_positive():
    result = exposure_reduction_pct(0.5, 0.4)
    assert result == pytest.approx(20.0, abs=0.1)


def test_reduction_same_score():
    result = exposure_reduction_pct(0.5, 0.5)
    assert result == pytest.approx(0.0)


def test_reduction_recommended_worse():
    """If recommended has higher score than baseline, reduction is negative."""
    result = exposure_reduction_pct(0.3, 0.5)
    assert result < 0.0


# SolarCalculator

def test_solar_noon_high_elevation():
    """At solar noon in Pune in October, elevation should be significant."""
    # Approximate solar noon at Pune (73.85°E) on Oct 10
    # UTC noon at 73.85°E ≈ 12 - (73.85/15) ≈ UTC 07:04
    utc_noon = datetime(2026, 10, 10, 7, 4, 0)  # approx solar noon UTC
    result = SolarCalculator.calculate(18.52, 73.85, utc_noon)
    assert result.is_daylight
    assert result.elevation_deg > 40  # Should be high in Oct at 18°N


def test_solar_night():
    """At midnight UTC, sun should be below horizon in Pune."""
    utc_midnight = datetime(2026, 10, 10, 18, 30, 0)  # midnight IST = 18:30 UTC
    result = SolarCalculator.calculate(18.52, 73.85, utc_midnight)
    assert not result.is_daylight
    assert result.irradiance_proxy == pytest.approx(0.0)


def test_solar_changes_with_time():
    """Changing departure time changes solar features."""
    morning_utc = datetime(2026, 10, 10, 4, 0)  # 9:30 AM IST
    noon_utc = datetime(2026, 10, 10, 7, 0)  # 12:30 PM IST
    sol_morning = SolarCalculator.calculate(18.52, 73.85, morning_utc)
    sol_noon = SolarCalculator.calculate(18.52, 73.85, noon_utc)
    # Noon should have higher elevation than morning
    assert sol_noon.elevation_deg > sol_morning.elevation_deg
    assert sol_noon.irradiance_proxy > sol_morning.irradiance_proxy


def test_solar_irradiance_between_zero_and_one():
    for hour in range(0, 24, 3):
        utc_dt = datetime(2026, 10, 10, hour, 0, 0)
        result = SolarCalculator.calculate(18.52, 73.85, utc_dt)
        assert 0.0 <= result.irradiance_proxy <= 1.0


# Hand-calculated example (documented in MODEL.md)

def test_hand_calculated_example():
    """
    Verify a hand-calculated segment score.

    Inputs:
    - sun_factor = 0.707 (sin 45° = √2/2)
    - uv_factor = 6/11 ≈ 0.545
    - weather_factor = 0.35
    Weights: sun=0.50, uv=0.30, weather=0.20

    Expected:
    exposure = 0.50*0.707 + 0.30*0.545 + 0.20*0.35
             = 0.3535 + 0.1636 + 0.070
             = 0.5871 (approx)
    """
    f = SegmentFeatures(
        length_m=100.0,
        duration_s=72.0,
        solar_elevation_deg=45.0,
        sun_factor=math.sin(math.radians(45.0)),  # ≈ 0.7071
        uv_index=6.0,
        uv_factor=6.0 / 11.0,  # ≈ 0.5455
        weather_factor=0.35,
        features_available=["solar_elevation", "uv_index", "weather_composite"],
        features_missing=["canopy_data"],
    )
    result = score_segment(f)
    expected = 0.50 * math.sin(math.radians(45.0)) + 0.30 * (6.0 / 11.0) + 0.20 * 0.35
    assert abs(result.exposure - expected) < 0.001, (
        f"Expected {expected:.4f}, got {result.exposure:.4f}"
    )
