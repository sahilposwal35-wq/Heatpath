"""
Solar position calculator.

Uses standard spherical-trigonometry formulae. No external library required.
Accuracy: ±1–2° typical — suitable for relative exposure comparison,
not for precise shadow-casting geometry.

Reference: NOAA Solar Calculator method (public domain algorithm).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone


class SolarPosition:
    """Calculated solar position for a given location and UTC time."""

    elevation_deg: float  # degrees above horizon; negative = below horizon
    azimuth_deg: float  # degrees clockwise from North (0=N, 90=E, 180=S, 270=W)
    is_daylight: bool  # True when sun is above horizon
    irradiance_proxy: float  # 0.0–1.0 relative proxy (sin elevation, 0 when below horizon)

    def __init__(
        self,
        elevation_deg: float,
        azimuth_deg: float,
    ) -> None:
        self.elevation_deg = elevation_deg
        self.azimuth_deg = azimuth_deg
        self.is_daylight = elevation_deg > 0.0
        self.irradiance_proxy = max(0.0, math.sin(math.radians(elevation_deg)))

    def __repr__(self) -> str:
        return (
            f"SolarPosition(elev={self.elevation_deg:.1f}°, "
            f"az={self.azimuth_deg:.1f}°, "
            f"irradiance_proxy={self.irradiance_proxy:.3f})"
        )


class SolarCalculator:
    """
    Compute solar elevation and azimuth for given coordinates and UTC datetime.

    Algorithm:
    - Day angle from day-of-year.
    - Solar declination via Fourier approximation.
    - Equation of time for apparent solar time.
    - Hour angle from apparent solar time.
    - Elevation and azimuth via spherical trigonometry.

    Suitable for: relative exposure comparison between walking routes.
    Not suitable for: precise shadow-length calculation without building geometry.
    """

    @staticmethod
    def _day_of_year(dt: datetime) -> int:
        return dt.timetuple().tm_yday

    @staticmethod
    def _solar_declination_rad(day_of_year: int) -> float:
        """Approximate solar declination in radians."""
        # Spencer 1971 Fourier series (accuracy ~0.01°)
        B = 2 * math.pi * (day_of_year - 1) / 365
        decl = (
            0.006918
            - 0.399912 * math.cos(B)
            + 0.070257 * math.sin(B)
            - 0.006758 * math.cos(2 * B)
            + 0.000907 * math.sin(2 * B)
            - 0.002697 * math.cos(3 * B)
            + 0.00148 * math.sin(3 * B)
        )
        return decl  # radians

    @staticmethod
    def _equation_of_time_minutes(day_of_year: int) -> float:
        """Equation of time in minutes (Spencer 1971)."""
        B = 2 * math.pi * (day_of_year - 1) / 365
        eot = 229.18 * (
            0.000075
            + 0.001868 * math.cos(B)
            - 0.032077 * math.sin(B)
            - 0.014615 * math.cos(2 * B)
            - 0.04089 * math.sin(2 * B)
        )
        return eot  # minutes

    @classmethod
    def calculate(
        cls,
        lat_deg: float,
        lon_deg: float,
        utc_dt: datetime,
    ) -> SolarPosition:
        """
        Calculate solar position for the given coordinates and UTC datetime.

        Args:
            lat_deg: Latitude in degrees (positive = North).
            lon_deg: Longitude in degrees (positive = East).
            utc_dt: UTC datetime (timezone-aware or naive UTC).

        Returns:
            SolarPosition with elevation and azimuth in degrees.
        """
        # Ensure UTC
        if utc_dt.tzinfo is not None:
            utc_dt = utc_dt.astimezone(timezone.utc).replace(tzinfo=None)

        day = cls._day_of_year(utc_dt)
        decl = cls._solar_declination_rad(day)
        eot = cls._equation_of_time_minutes(day)

        # Fractional UTC hour
        utc_hour = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0

        # Apparent solar time (hours)
        # Longitude offset: 4 minutes per degree
        ast = utc_hour + eot / 60.0 + lon_deg / 15.0

        # Hour angle (radians): noon = 0, morning = negative, afternoon = positive
        hour_angle_rad = math.radians((ast - 12.0) * 15.0)

        lat_rad = math.radians(lat_deg)

        # Solar elevation (altitude) angle
        sin_elev = (
            math.sin(lat_rad) * math.sin(decl)
            + math.cos(lat_rad) * math.cos(decl) * math.cos(hour_angle_rad)
        )
        sin_elev = max(-1.0, min(1.0, sin_elev))
        elevation_rad = math.asin(sin_elev)
        elevation_deg = math.degrees(elevation_rad)

        # Solar azimuth (degrees from North, clockwise)
        cos_az = (math.sin(decl) - math.sin(lat_rad) * sin_elev) / (
            math.cos(lat_rad) * math.cos(elevation_rad) + 1e-9
        )
        cos_az = max(-1.0, min(1.0, cos_az))
        az_rad = math.acos(cos_az)
        azimuth_deg = math.degrees(az_rad)

        # Adjust for afternoon (hour angle > 0 → sun is west of south)
        if hour_angle_rad > 0:
            azimuth_deg = 360.0 - azimuth_deg

        return SolarPosition(elevation_deg=elevation_deg, azimuth_deg=azimuth_deg)
