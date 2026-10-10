# HeatPath — Data Feasibility and Decisions Report

**Document:** `docs/DATA_FEASIBILITY.md`  
**Pilot Area:** Central Pune (Shivajinagar & Deccan Gymkhana), Maharashtra, India  
**Bounding Box:** Lat [18.490, 18.545] N, Lon [73.820, 73.880] E  
**Date:** October 2026  

---

## 1. Selected Pilot Area and Rationale

We selected **Central Pune (Shivajinagar / Deccan Gymkhana / FC College Road / JM Road)** as the pilot area for the following reasons:
1. **Network density:** Rich pedestrian connectivity with parallel arterial roads (Jangali Maharaj Road, Fergusson College Road) allowing realistic alternative walking routes between major hubs.
2. **Pedestrian relevance:** High daily pedestrian footfall (students, commuters between Shivajinagar railway/metro stations and Deccan bus station).
3. **Heat exposure significance:** Pune regularly experiences temperatures in excess of 36–40°C during summer and post-monsoon dry heat windows, where pedestrian direct-sun exposure creates acute discomfort.
4. **Data coverage:** High quality OpenStreetMap pedestrian tagging and full coverage on Open-Meteo hourly weather grids.
5. **Bounded scale:** Small enough to process without paid tile servers or massive database infrastructure.

---

## 2. Assessment of Candidate Data Sources

### Source A: OpenStreetMap & Pedestrian Routing
- **Provider:** OpenStreetMap Foundation / FOSSGIS e.V. Valhalla instance (`https://valhalla1.openstreetmap.de`).
- **License:** Open Database License (ODbL) 1.0.
- **Access Date:** October 2026.
- **Fields Used:** Pedestrian route geometry (`polyline`), distance (`meters`), duration (`seconds`), turn-by-turn maneuvers.
- **Spatial Resolution:** Street segment level (~5–100 m).
- **Temporal Resolution:** Current OSM map state.
- **Status:** **Selected**. Valhalla pedestrian profile generates valid walking routes and natural alternatives.

### Source B: Open-Meteo API
- **Provider:** Open-Meteo GmbH (`https://api.open-meteo.com/v1/forecast`).
- **License:** CC BY 4.0 for data; free for non-commercial use.
- **Access Date:** October 2026.
- **Fields Used:** `temperature_2m`, `apparent_temperature`, `cloudcover`, `uv_index`, `windspeed_10m`.
- **Spatial Resolution:** ~1 km atmospheric grid. **Crucial limitation:** this is macro-weather for the pilot zone, not street-level microclimate.
- **Temporal Resolution:** Hourly forecast and current conditions.
- **Status:** **Selected** for area atmospheric baseline.

### Source C: Solar Position (Built-in Spencer / Astronomical Algorithm)
- **Implementation:** `backend/app/solar/calculator.py` using standard spherical trigonometry.
- **Inputs:** Coordinates, date, UTC time.
- **Outputs:** Solar elevation angle (°), azimuth angle (°), daylight boolean, clear-sky irradiance proxy `max(0, sin(elevation))`.
- **License:** Open domain / MIT.
- **Status:** **Selected**. Provides deterministic, instantaneous solar geometry calculations for any specified departure time.

### Source D: Kaggle Datasets Assessment
- **Query terms assessed:** "Pune urban heat island", "India tree canopy", "Pune street temperature", "Pune land surface temperature".
- **Findings:**
  - Kaggle contains several satellite LST (Land Surface Temperature) datasets derived from Landsat or MODIS at 30 m to 1 km resolution.
  - However, Landsat LST measures radiant ground skin temperature at satellite overpass times (usually 10:30 AM once every 16 days), which does NOT reflect pedestrian air temperature or dynamic hourly shading along individual sidewalks.
  - Other city-level CSVs contain single daily historical temperature records for Pune Airport, which do not assist in segment-level walking comparisons.
- **Decision:** **Kaggle was evaluated and rejected for the real-time routing pipeline**. Introducing a coarse daily Kaggle CSV would create a false impression of microclimate precision without contributing genuine street-level signal.

### Source E: NASA POWER
- **URL:** `https://power.larc.nasa.gov/`
- **Assessment:** Spatial resolution is 0.5° × 0.5° (~55 km × ~55 km), which spans multiple cities. Far too coarse for intra-city walking comparisons.
- **Decision:** **Rejected for real-time routing**.

---

## 3. Summary Matrix

| Candidate Source | Spatial Res | Temporal Res | License | Decision | Reason |
|---|---|---|---|---|---|
| OSM / Valhalla | Street segment | Current | ODbL 1.0 | **Selected** | Direct pedestrian routing with alternatives |
| Open-Meteo | ~1 km | Hourly | CC BY 4.0 | **Selected** | Accurate macro weather & UV index |
| Solar Calculator | Exact point | Minute | MIT | **Selected** | Deterministic solar position per departure time |
| Kaggle LST | 30 m–1 km | 16-day overpass | Various | **Rejected** | Static skin temp; irrelevant for pedestrian air/shade |
| NASA POWER | ~55 km | Daily/Hourly | Public Domain | **Rejected** | Coarser than whole city |

---

## 4. Honest Data Limitations Exposed in the Product

1. **No building shadow geometry:** The MVP does not have municipal building height LIDAR models for Pune. Therefore, we do not claim exact shadow projection.
2. **No street tree canopy coverage:** Tree canopy is not universally tagged on OSM for Pune; we expose this explicitly as an omitted feature rather than fabricating greenery.
3. **Proxy definition:** Scores are strictly labelled as **"Estimated Relative Heat-Exposure Proxy"**, never as measured degrees Celsius or medical heat stress indicators.
