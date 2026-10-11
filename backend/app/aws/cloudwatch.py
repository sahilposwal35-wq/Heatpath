"""
AWS CloudWatch logging & telemetry integration for HeatPath.

Provides structured logging to Amazon CloudWatch Logs for pedestrian route
queries and exposure calculations. Falls back gracefully to standard console
logging if AWS credentials or network are unavailable.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger("heatpath.aws")

_cloudwatch_client = None
_sequence_token = None
_stream_initialized = False


def get_cloudwatch_client():
    """Lazily initialize and return boto3 logs client if configured."""
    global _cloudwatch_client
    if _cloudwatch_client is None:
        try:
            import boto3
            _cloudwatch_client = boto3.client(
                "logs",
                region_name=settings.aws_region,
            )
        except Exception as e:
            logger.debug(f"CloudWatch client could not be initialized: {e}")
            _cloudwatch_client = False
    return _cloudwatch_client if _cloudwatch_client is not False else None


def log_route_query_to_cloudwatch(
    origin: tuple[float, float],
    destination: tuple[float, float],
    profile: str,
    num_routes: int,
    best_route_label: str,
    time_saved_or_score_diff: dict[str, Any],
) -> bool:
    """
    Log a structured route calculation event to CloudWatch Logs.
    Returns True if successfully pushed to CloudWatch, False otherwise.
    """
    event_payload = {
        "event": "route_calculation",
        "app": settings.app_name,
        "version": settings.version,
        "origin": {"lat": origin[0], "lon": origin[1]},
        "destination": {"lat": destination[0], "lon": destination[1]},
        "profile": profile,
        "num_routes_found": num_routes,
        "recommended_route": best_route_label,
        "metrics": time_saved_or_score_diff,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Always log locally
    logger.info(f"[HeatPath Metric] {json.dumps(event_payload)}")

    log_group = settings.aws_cloudwatch_log_group
    if not log_group:
        return False

    client = get_cloudwatch_client()
    if not client:
        return False

    stream_name = time.strftime("heatpath-%Y%m%d", time.gmtime())

    try:
        global _stream_initialized
        if not _stream_initialized:
            try:
                client.create_log_group(logGroupName=log_group)
            except client.exceptions.ResourceAlreadyExistsException:
                pass
            try:
                client.create_log_stream(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                )
            except client.exceptions.ResourceAlreadyExistsException:
                pass
            _stream_initialized = True

        log_event = {
            "timestamp": int(time.time() * 1000),
            "message": json.dumps(event_payload),
        }

        kwargs = {
            "logGroupName": log_group,
            "logStreamName": stream_name,
            "logEvents": [log_event],
        }

        global _sequence_token
        if _sequence_token:
            kwargs["sequenceToken"] = _sequence_token

        resp = client.put_log_events(**kwargs)
        _sequence_token = resp.get("nextSequenceToken")
        return True
    except Exception as e:
        logger.debug(f"Failed to push log event to CloudWatch: {e}")
        return False
