// API service for HeatPath backend
// All data fetching goes through this module.

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface RouteRequest {
  origin: Coordinates;
  destination: Coordinates;
  departure_time: string; // ISO 8601
  profile: 'faster' | 'balanced' | 'exposure';
}

export interface ScoreComponents {
  alpha_time: number;
  beta_exposure: number;
  gamma_distance: number;
}

export interface RouteResult {
  route_index: number;
  label: string;
  distance_m: number;
  duration_s: number;
  distance_km: number;
  duration_min: number;
  avg_exposure_score: number;
  cumulative_exposure_score: number;
  route_cost: number;
  score_components: ScoreComponents;
  data_coverage: number;
  data_confidence: 'high' | 'medium' | 'low';
  is_recommended: boolean;
  extra_minutes_vs_fastest: number | null;
  model_score_reduction_pct: number | null;
  explanation: string;
  geometry: [number, number][]; // [lon, lat] pairs
  data_source: string;
  missing_features: string[];
}

export interface WeatherInfo {
  temperature_c: number | null;
  apparent_temperature_c: number | null;
  uv_index: number | null;
  cloud_cover_pct: number | null;
  wind_speed_kmh: number | null;
  retrieved_at_utc: string;
  data_source: string;
  grid_resolution_note: string;
}

export interface SolarInfo {
  elevation_deg: number;
  azimuth_deg: number;
  is_daylight: boolean;
  irradiance_proxy: number;
  calculated_for_utc: string;
}

export interface RouteResponse {
  routes: RouteResult[];
  weather: WeatherInfo | null;
  solar_at_origin: SolarInfo | null;
  departure_time_utc: string;
  pilot_area_name: string;
  score_formula_note: string;
  attribution: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  app_name: string;
}

export interface GeocodeResult {
  name: string;
  display_name: string;
  lat: number;
  lon: number;
}

const BACKEND = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => apiFetch<HealthResponse>('/health'),

  findRoutes: (req: RouteRequest) =>
    apiFetch<RouteResponse>('/api/routes', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  getArea: () => apiFetch('/api/area'),
  getDataStatus: () => apiFetch('/api/data-status'),
  searchPlaces: (q: string) =>
    apiFetch<GeocodeResult[]>(`/api/geocode?q=${encodeURIComponent(q)}`),
};
