# Data Sources and Attribution

**Project:** HeatPath — Personalized Heat-Exposure Routing for Indian Cities  
**Track:** WeMakeDevs Environmental Hacks — Track 02: Heat & Water  
**Document version:** 1.0 | 10 October 2026

---

## 1. OpenStreetMap (OSM) — Pedestrian Road Network

| Field | Value |
|---|---|
| **Source name** | OpenStreetMap |
| **URL** | https://www.openstreetmap.org |
| **Routing engine** | Valhalla public instance at https://valhalla1.openstreetmap.de |
| **Geocoding** | Nominatim at https://nominatim.openstreetmap.org |
| **Access date** | October 2026 |
| **License** | Open Database License (ODbL) 1.0 |
| **Attribution required** | "© OpenStreetMap contributors" — displayed in map UI |
| **Fields used** | Pedestrian route geometry (encoded polyline), segment distance (metres), walking duration (seconds), maneuver/step data |
| **Geographic coverage** | Pilot area: Pune, Maharashtra — approx. bounding box 18.490–18.545 N, 73.820–73.880 E |
| **Spatial resolution** | Individual road segments (metres) |
| **Temporal** | OSM data is continuously updated; Valhalla caches periodically |
| **Limitations** | Public Valhalla demo instance — rate-limited; may not return alternatives for very short segments; no building heights; some footways may be missing |
| **Usage terms** | Non-commercial and commercial use permitted under ODbL; attribution required |

**Overpass API Note:** Direct Overpass API calls were blocked (HTTP 406) from this environment during the build session. OSM data is accessed exclusively through the Valhalla routing engine and Nominatim geocoder, both of which are documented OSM services.

---

## 2. Open-Meteo — Weather Data

| Field | Value |
|---|---|
| **Source name** | Open-Meteo |
| **URL** | https://open-meteo.com |
| **API endpoint** | https://api.open-meteo.com/v1/forecast |
| **Access date** | October 2026 |
| **License** | Free for non-commercial use; CC BY 4.0 for data outputs |
| **Attribution required** | "Weather data from Open-Meteo.com" — displayed in data-status panel |
| **Fields used** | `temperature_2m` (°C, current/hourly), `apparent_temperature` (°C), `cloudcover` (%), `uv_index` (0–11+), `windspeed_10m` (km/h) |
| **Spatial resolution** | ~1 km grid; **not street-level**. Applied as area-wide weather context for the pilot bounding box, not per-segment microclimate |
| **Temporal resolution** | Hourly forecast; current conditions; IST (UTC+5:30) |
| **Limitations** | Grid resolution (~1 km) cannot represent individual street microclimates or building shading effects. UV index is used as a solar proxy, not a precise radiation measure for pedestrians |
| **Usage terms** | Non-commercial use: free, no API key required. Commercial use requires a subscription |

---

## 3. Solar Position — Algorithmic Calculation

| Field | Value |
|---|---|
| **Source name** | Python `math` + `datetime` standard library (no external dependency) |
| **Implementation** | Custom `SolarCalculator` class in `backend/app/solar/calculator.py` |
| **Algorithm** | Solar declination from day-of-year, hour angle from UTC time and longitude, elevation/azimuth via spherical trigonometry |
| **Inputs** | Latitude, longitude, UTC datetime |
| **Outputs** | Solar elevation (°), solar azimuth (°), daylight boolean, approximate solar irradiance proxy |
| **Accuracy** | Approximate — suitable for relative exposure comparisons (±1–2° error typical for simplified formula). Not suitable for precise shadow geometry without building heights |
| **Limitations** | Does not compute exact shadow cast by buildings or trees. A building-shade proxy requires wall height and orientation data not currently available for this pilot area |
| **License** | Public domain algorithm (spherical trigonometry) |

---

## 4. Valhalla Routing Engine

| Field | Value |
|---|---|
| **Source name** | Valhalla (open-source routing engine by Mapzen/Valhalla project) |
| **Public instance** | https://valhalla1.openstreetmap.de (hosted by openstreetmap.de) |
| **Software license** | MIT License |
| **Access date** | October 2026 |
| **Attribution** | "Routing by Valhalla / OpenStreetMap" |
| **Capabilities used** | Pedestrian routing (`pedestrian` costing), up to 3 route alternatives, encoded polyline geometry, maneuver data, distance/duration |
| **Limitations** | Public demo instance; rate limits apply; alternatives may not always be returned for very short or very constrained routes |
| **Terms** | Free for non-commercial demo use; attribution required |

---

## 5. Nominatim — Geocoding

| Field | Value |
|---|---|
| **Source name** | Nominatim (OpenStreetMap geocoder) |
| **URL** | https://nominatim.openstreetmap.org |
| **License** | ODbL (underlying data); service is free with attribution |
| **Attribution** | "Geocoding by Nominatim / OpenStreetMap" |
| **Fields used** | `lat`, `lon`, `display_name` for location search |
| **Limitations** | 1 request per second usage policy; User-Agent required |

---

## 6. Sample / Fixture Data (Synthetic — Demo Fallback)

| Field | Value |
|---|---|
| **File** | `data/sample/pune_demo_routes.json` |
| **Provenance** | **Synthetic** — generated deterministically from known Pune coordinates using the HeatPath scoring model |
| **Purpose** | Offline demo / CI fallback when external APIs are unavailable |
| **Labelling** | Always displayed as "⚠ Demo data — not live" in the UI |
| **Real data?** | No. These are pre-computed sample routes for demonstration purposes only |

---

## 7. Kaggle Assessment

Kaggle was assessed as a supplementary source. After reviewing available datasets:

- **"India Urban Heat Island"** datasets on Kaggle typically provide city-level or district-level average temperatures, not segment-level walking data.
- **"Pune buildings"** datasets were not found with usable building heights and appropriate licensing.
- **"Urban tree canopy India"** datasets were not found with per-street resolution for Pune.

**Decision:** Kaggle is not used in this project. The available Kaggle datasets for Pune did not provide the spatial resolution (individual road segments) or the field types (building heights, canopy coverage per segment) needed to improve route scoring beyond what OSM + Open-Meteo + solar calculation already provides. Using a dataset that provides a single temperature value per city per day would not contribute meaningfully to route differentiation.

---

## Attribution Summary (for UI display)

> Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL)  
> Routing by [Valhalla](https://github.com/valhalla/valhalla) / OpenStreetMap  
> Weather data from [Open-Meteo.com](https://open-meteo.com) (CC BY 4.0)  
> Geocoding by [Nominatim](https://nominatim.openstreetmap.org) / OpenStreetMap
