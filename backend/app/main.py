"""
HeatPath FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router

app = FastAPI(
    title=settings.app_name,
    description=(
        "HeatPath — Personalized Heat-Exposure Routing for Indian Cities. "
        "WeMakeDevs Environmental Hacks, Track 02: Heat & Water. "
        "Provides pedestrian route alternatives with relative heat-exposure proxy scores. "
        "Scores are model estimates, not measured temperatures or medical advice."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],  # wide for hackathon; restrict in prod
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    print(f"✓ {settings.app_name} v{settings.version} started")
    print(f"  Routing: {settings.valhalla_base_url}")
    print(f"  Weather: {settings.open_meteo_base_url}")
    print(f"  Pilot area: {settings.pilot_center_lat}, {settings.pilot_center_lon}")
    print(f"  API docs: http://{settings.backend_host}:{settings.backend_port}/docs")
