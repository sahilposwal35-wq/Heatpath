# HeatPath — Implementation Plan & Status Checklist

**Project:** HeatPath — Personalized Heat-Exposure Routing for Indian Cities  
**Hackathon Track:** WeMakeDevs Environmental Hacks — Track 02: Heat & Water  
**Date:** October 2026  
**Status:** MVP Implemented, Verified, and Tested Locally

---

## 1. Project Phases & Task Checklist

### Phase A: Audit and Feasibility
- [x] Inspect workspace structure, package manifests, and environment variables.
- [x] Check Python 3.14 toolchain, Node.js v20+, npm, and system packages.
- [x] Assess candidate data sources (OSM, Open-Meteo, NASA POWER, Kaggle).
- [x] Select pilot area (Pune — Shivajinagar / Deccan Gymkhana bounding box).
- [x] Produce `docs/DATA_FEASIBILITY.md`.
- [x] Initialize `.gitignore`, `.env.example`, and `DATA_SOURCES.md`.

### Phase B: Working Route Skeleton
- [x] Create backend FastAPI structure with `/health` endpoint.
- [x] Implement OSM/Valhalla pedestrian routing integration with timeout and error handling.
- [x] Provide deterministic offline fallback fixture (`data/sample/pune_demo_routes.py`) clearly labelled as synthetic.
- [x] Create React + Vite + TypeScript frontend with Leaflet map centered on Pune.
- [x] Connect frontend origin/destination selection to route visualizer.

### Phase C: Data Pipeline & Geospatial Integration
- [x] Implement Open-Meteo API weather adapter (hourly forecast, current conditions, temperature, apparent temperature, UV index, cloud cover).
- [x] Build solar position calculator (elevation, azimuth, daylight state, irradiance proxy).
- [x] Handle missing features transparently (confidence scoring, explicit missing indicators).
- [x] Implement `/api/area` and `/api/data-status` metadata endpoints.

### Phase D: Scoring & Multi-Objective Ranking
- [x] Implement segment-level exposure scoring model with clamping `[0, 1]`.
- [x] Implement duration-weighted route aggregation for average exposure score and cumulative cost.
- [x] Implement multi-objective route cost ranking:
  - `route_cost = alpha * norm_time + beta * avg_exposure + gamma * norm_dist`
- [x] Implement profile weighting:
  - `faster` (time-prioritized)
  - `balanced` (balanced trade-off)
  - `exposure` (heat-exposure minimized)
- [x] Implement percentage score reduction formula:
  - `estimated_model_score_reduction_pct = 100 * (B - R) / B`
- [x] Generate plain-language, evidence-grounded route trade-off explanations.
- [x] Add 37 unit and API integration tests in `backend/tests/`.

### Phase E: UI Polish & Design System
- [x] Build dark-mode design system with amber heat palette, modern typography (Inter), and glassmorphism.
- [x] Implement route comparison cards with exposure bars and confidence badges.
- [x] Implement weather & solar condition strip.
- [x] Implement profile selector and departure time selector.
- [x] Build "Model & Data Disclosure" accordion exposing honest limitations and source provenance.
- [x] Test responsive layout and empty/error states.

### Phase F: AWS Architecture & Deployment Feasibility
- [x] Formulate minimal low-cost AWS deployment path:
  - Static frontend on S3 + CloudFront.
  - Backend container on AWS App Runner or ECS Fargate (or EC2 t4g.nano).
  - Processed geospatial layers on S3.
  - CloudWatch logs.
- [x] Record honest AWS deployment status (local development verified; manual AWS deployment steps documented; zero unapproved cloud expenses incurred).

### Phase G: Validation & Verification
- [x] Test 3 reproducible origin/destination route scenarios in Pune.
- [x] Compare morning, midday, and afternoon departure times.
- [x] Verify identical origin/destination validation error handling.
- [x] Run full pytest suite (37/37 passed).
- [x] Run full frontend production build (`tsc -b && vite build` passed).

### Phase H: Final Documentation & Submission Prep
- [x] Complete `README.md` with honest architecture, setup, and model details.
- [x] Complete `DATA_SOURCES.md`, `docs/ARCHITECTURE.md`, `docs/MODEL.md`, `docs/VALIDATION.md`.
- [x] Provide local Linux run instructions and demo video script.
