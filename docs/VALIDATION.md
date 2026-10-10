# HeatPath — Validation and Test Verification Report

**Document:** `docs/VALIDATION.md`  
**Date:** October 2026  
**Status:** All 37 backend tests passing, frontend builds cleanly (`tsc -b && vite build` 0 errors).

---

## 1. Test Suite Summary

### Backend Unit & Integration Tests (`pytest`)
- **Total tests run:** 37
- **Passed:** 37
- **Failed:** 0
- **Execution time:** ~3.1 seconds

#### Test Coverage Categories:
1. **Normalization & Clamping (5 tests):**
   - UV zero, UV max (11), UV extreme (>11), UV midpoint, UV negative clamp.
2. **Weather Normalization (4 tests):**
   - Missing weather fields, temperature-only, cool temperatures clamp to zero, full cloud cover 50% attenuation.
3. **Segment Scoring (8 tests):**
   - Full features, clamped bounds $[0, 1]$, missing UV index, missing solar angle, missing weather, all features missing (fallback uncertainty), reproducibility with identical inputs.
4. **Route Aggregation (3 tests):**
   - Empty segment list, single segment, duration-weighted multi-segment aggregation.
5. **Ranking & Profiles (3 tests):**
   - Profile weight shifts (`faster` vs `balanced` vs `exposure`), single route available without crash, confidence labelling (`high`, `medium`, `low`).
6. **Score Reduction Percentage (4 tests):**
   - Zero baseline handling, positive reduction, identical score, recommended route worse than baseline.
7. **Astronomical Solar Calculations (4 tests):**
   - Solar noon high elevation (>50° in tropics), nighttime elevation (<0°), elevation shift between morning/midday, irradiance proxy bounds $[0, 1]$.
8. **Hand-Calculated Verification (1 test):**
   - Verifies against hand-calculated values in `docs/MODEL.md`.
9. **API Integration & Smoke Tests (5 tests):**
   - `GET /health` -> 200 OK
   - `GET /api/area` -> 200 OK
   - `GET /api/data-status` -> 200 OK
   - `POST /api/routes` -> 200 OK with geometry and exposure scores
   - `POST /api/routes` with identical origin & destination -> 422 Unprocessable Entity.

---

## 2. Reproducible Origin / Destination Test Scenarios

### Scenario 1: Shivajinagar to Deccan Gymkhana (Midday 14:00 IST)
- **Origin:** Lat 18.5204, Lon 73.8399 (Shivajinagar Bus Stand)
- **Destination:** Lat 18.5074, Lon 73.8479 (Deccan Gymkhana)
- **Departure Time:** 2026-10-10T14:00:00+05:30
- **Live Weather Retrieved:** 26.8°C, Apparent 29.2°C, UV Index 1.75, Cloud Cover 2.0%
- **Solar Position:** Elevation 55.23°, Azimuth 226.62°, Irradiance Proxy 0.8215
- **Observed Routes:**
  - Route 0: 2,205 m, 27.3 min, Exposure Score 0.5467.

### Scenario 2: Shivajinagar to FC College Road (Multi-Route Comparison)
- **Origin:** Lat 18.5308, Lon 73.8475
- **Destination:** Lat 18.5173, Lon 73.8415
- **Profile:** Balanced
- **Observed Routes:**
  - **Fastest:** Distance 1,986.3 m, Duration 23.6 min, Exposure Score 0.5467, Cost 0.612.
  - **Heat-aware Candidate:** Distance 2,319.4 m, Duration 27.7 min (+4.1 min), Exposure Score 0.5467, Cost 0.697.
  - **Alternative 2:** Distance 2,343.7 m, Duration 27.9 min (+4.3 min), Exposure Score 0.5467, Cost 0.702.
- **Model Recommendation:** Fastest route selected because in current macro weather without segment canopy differences, adding 4.1 minutes does not lower relative exposure.

### Scenario 3: Time-of-Day Solar Elevation Sensitivity
Testing the identical route at 08:30 IST vs 13:00 IST vs 20:00 IST:
- **08:30 IST (Morning):** Solar elevation ~28.4° $\implies$ Lower direct sun intensity factor (0.476).
- **13:00 IST (Solar Peak):** Solar elevation ~63.1° $\implies$ Peak direct sun factor (0.892).
- **20:00 IST (Night):** Solar elevation < 0° $\implies$ Sun factor 0.0, exposure strictly governed by residual ambient temperature.

---

## 3. Frontend Production Build Verification

- **Command:** `npm run build` (`tsc -b && vite build`)
- **Result:** Success, Exit Code 0
- **Output Artifacts:**
  - `dist/index.html` (1.27 kB)
  - `dist/assets/index-C6kVTxkc.css` (27.54 kB)
  - `dist/assets/index-DwizjLqk.js` (389.20 kB)
- **TypeScript Type Checking:** 0 errors reported under strict `verbatimModuleSyntax`.
