"""
HeatPath backend configuration.
All values loaded from environment variables (see .env.example).
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Routing
    valhalla_base_url: str = os.getenv(
        "VALHALLA_BASE_URL", "https://valhalla1.openstreetmap.de"
    )

    # Weather
    open_meteo_base_url: str = os.getenv(
        "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1"
    )

    # Geocoding
    nominatim_base_url: str = os.getenv(
        "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
    )
    nominatim_user_agent: str = os.getenv(
        "NOMINATIM_USER_AGENT",
        "HeatPath/1.0 (WeMakeDevs hackathon; contact: heatpath@example.com)",
    )

    # Backend
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:4173"
        ).split(",")
    ]

    # Pilot area — Pune Shivajinagar/Deccan
    pilot_lat_min: float = float(os.getenv("PILOT_LAT_MIN", "18.490"))
    pilot_lat_max: float = float(os.getenv("PILOT_LAT_MAX", "18.545"))
    pilot_lon_min: float = float(os.getenv("PILOT_LON_MIN", "73.820"))
    pilot_lon_max: float = float(os.getenv("PILOT_LON_MAX", "73.880"))
    pilot_center_lat: float = float(os.getenv("PILOT_CENTER_LAT", "18.5204"))
    pilot_center_lon: float = float(os.getenv("PILOT_CENTER_LON", "73.8567"))
    pilot_timezone: str = os.getenv("PILOT_TIMEZONE", "Asia/Kolkata")

    # HTTP client timeouts (seconds)
    http_timeout: float = 20.0

    # App version
    version: str = "1.0.0"
    app_name: str = "HeatPath"

    # AWS configuration
    aws_region: str = os.getenv("AWS_REGION", "ap-south-1")
    aws_s3_bucket_name: str | None = os.getenv("AWS_S3_BUCKET_NAME")
    aws_cloudwatch_log_group: str | None = os.getenv("AWS_CLOUDWATCH_LOG_GROUP")


settings = Settings()
