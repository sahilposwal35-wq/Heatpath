import { useState, useCallback } from 'react';
import './index.css';
import HeatMap from './components/HeatMap';
import PlaceSearchInput from './components/PlaceSearchInput';
import { RouteCard, WeatherStrip } from './components/RouteCard';
import { api, type RouteResponse } from './services/api';

// ── Example locations ─────────────────────────────────────────────────────────

const QUICK_LOCATIONS = [
  { name: 'Shivajinagar → Deccan', origin: { lat: 18.5204, lon: 73.8399 }, dest: { lat: 18.5074, lon: 73.8479 } },
  { name: 'FC College → Nal Stop', origin: { lat: 18.5220, lon: 73.8440 }, dest: { lat: 18.5060, lon: 73.8310 } },
  { name: 'Pune Station → Shivajinagar', origin: { lat: 18.5293, lon: 73.8743 }, dest: { lat: 18.5204, lon: 73.8399 } },
];

type Profile = 'faster' | 'balanced' | 'exposure';
type ClickMode = 'origin' | 'dest' | null;

const PROFILES: { key: Profile; icon: string; name: string; desc: string }[] = [
  { key: 'faster', icon: '⚡', name: 'Faster', desc: 'Minimize walk time' },
  { key: 'balanced', icon: '⚖️', name: 'Balanced', desc: 'Time & exposure' },
  { key: 'exposure', icon: '🌡️', name: 'Lower Exposure', desc: 'Prefer cooler paths' },
];

// Default datetime = now + 10 minutes, in local time
function defaultDepartureTime(): string {
  const d = new Date(Date.now() + 10 * 60 * 1000);
  // Format as datetime-local input value
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Convert local datetime input to ISO 8601 with IST offset
function toISOWithIST(localStr: string): string {
  return `${localStr}:00+05:30`;
}

export default function App() {
  const [origin, setOrigin] = useState<{ lat: number; lon: number } | null>(null);
  const [destination, setDestination] = useState<{ lat: number; lon: number } | null>(null);
  const [originName, setOriginName] = useState<string>('');
  const [destName, setDestName] = useState<string>('');
  const [departureTime, setDepartureTime] = useState(defaultDepartureTime());
  const [profile, setProfile] = useState<Profile>('balanced');
  const [clickMode, setClickMode] = useState<ClickMode>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RouteResponse | null>(null);
  const [selectedRouteIdx, setSelectedRouteIdx] = useState<number | null>(null);

  // ── Map click handlers ──────────────────────────────────────────────────────
  const handleOriginSet = useCallback((lat: number, lon: number) => {
    setOrigin({ lat, lon });
    setOriginName(`Map Pin (${lat.toFixed(4)}, ${lon.toFixed(4)})`);
    setClickMode(null);
    setResponse(null);
  }, []);

  const handleDestSet = useCallback((lat: number, lon: number) => {
    setDestination({ lat, lon });
    setDestName(`Map Pin (${lat.toFixed(4)}, ${lon.toFixed(4)})`);
    setClickMode(null);
    setResponse(null);
  }, []);

  // ── Quick location ──────────────────────────────────────────────────────────
  const applyQuick = (q: typeof QUICK_LOCATIONS[0]) => {
    setOrigin(q.origin);
    setDestination(q.dest);
    const parts = q.name.split(' → ');
    setOriginName(parts[0] || q.name);
    setDestName(parts[1] || '');
    setResponse(null);
    setClickMode(null);
  };

  // ── Find routes ─────────────────────────────────────────────────────────────
  const findRoutes = async () => {
    if (!origin || !destination) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    setSelectedRouteIdx(null);
    try {
      const res = await api.findRoutes({
        origin,
        destination,
        departure_time: toISOWithIST(departureTime),
        profile,
      });
      setResponse(res);
      // Auto-select recommended route
      const recIdx = res.routes.findIndex(r => r.is_recommended);
      setSelectedRouteIdx(recIdx >= 0 ? recIdx : 0);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch routes. Check that the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const canFind = !!origin && !!destination && !loading;
  const isSettingOrigin = clickMode === 'origin';
  const isSettingDest = clickMode === 'dest';

  return (
    <div className="app-layout">
      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        {/* Header */}
        <div className="sidebar-header">
          <div className="logo-row">
            <div className="logo-icon">🔥</div>
            <span className="logo-name">HeatPath</span>
          </div>
          <p className="logo-tagline">
            Choose a practical walking route with lower estimated heat exposure
          </p>
        </div>

        {/* Body */}
        <div className="sidebar-body">

          {/* ── Quick locations ─────────────────────────────────────────────── */}
          <div className="form-section">
            <p className="form-section-title">Quick locations (Pune)</p>
            <div className="quick-locations">
              {QUICK_LOCATIONS.map(q => (
                <button
                  key={q.name}
                  className="quick-btn"
                  onClick={() => applyQuick(q)}
                  id={`quick-${q.name.replace(/[^a-z]/gi, '-').toLowerCase()}`}
                >
                  {q.name}
                </button>
              ))}
            </div>
          </div>

          <div className="divider" />

          {/* ── Origin ─────────────────────────────────────────────────────── */}
          <div className="form-section">
            <p className="form-section-title">Route</p>

            <PlaceSearchInput
              id="origin-search"
              label="Origin"
              icon="🟢"
              value={origin}
              placeName={originName}
              onChange={(coords, name) => {
                setOrigin(coords);
                setOriginName(name || '');
                setClickMode(null);
                setResponse(null);
              }}
              isMapSelecting={isSettingOrigin}
              onToggleMapSelect={() => setClickMode(isSettingOrigin ? null : 'origin')}
              placeholder="Search place (e.g. FC College, Station, Deccan)..."
            />

            <PlaceSearchInput
              id="dest-search"
              label="Destination"
              icon="🟠"
              value={destination}
              placeName={destName}
              onChange={(coords, name) => {
                setDestination(coords);
                setDestName(name || '');
                setClickMode(null);
                setResponse(null);
              }}
              isMapSelecting={isSettingDest}
              onToggleMapSelect={() => setClickMode(isSettingDest ? null : 'dest')}
              placeholder="Search destination (e.g. Nal Stop, Shaniwar Wada)..."
            />

            {/* Map instruction */}
            <div className={`map-instruction ${!clickMode ? 'hidden' : ''}`}>
              🗺️ Click anywhere on the map to set your {clickMode === 'origin' ? 'origin' : 'destination'}
            </div>
          </div>

          {/* ── Departure time ──────────────────────────────────────────────── */}
          <div className="input-group">
            <label className="input-label" htmlFor="departure-time">
              <span className="icon">🕐</span> Departure time (IST)
            </label>
            <input
              id="departure-time"
              type="datetime-local"
              className="input-field"
              value={departureTime}
              onChange={e => setDepartureTime(e.target.value)}
            />
          </div>

          {/* ── Profile ────────────────────────────────────────────────────── */}
          <div className="input-group">
            <label className="input-label">
              <span className="icon">🎛️</span> Preference
            </label>
            <div className="profile-grid">
              {PROFILES.map(p => (
                <button
                  key={p.key}
                  id={`profile-${p.key}`}
                  className={`profile-btn ${profile === p.key ? 'active' : ''}`}
                  onClick={() => setProfile(p.key)}
                >
                  <span className="p-icon">{p.icon}</span>
                  <span className="p-name">{p.name}</span>
                  <span className="p-desc">{p.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ── Find button ─────────────────────────────────────────────────── */}
          <button
            id="find-routes-btn"
            className="find-btn"
            onClick={findRoutes}
            disabled={!canFind}
          >
            {loading ? (
              <>
                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                Finding routes…
              </>
            ) : (
              <>🔍 Find Routes</>
            )}
          </button>

          {/* ── Error ──────────────────────────────────────────────────────── */}
          {error && (
            <div className="info-panel error fade-in" role="alert">
              ⚠ {error}
            </div>
          )}

          {/* ── Results ────────────────────────────────────────────────────── */}
          {response && (
            <div className="results-section fade-in">
              <div className="results-header">
                <span className="results-title">
                  {response.routes.length} routes found
                </span>
                <span className={`data-status-badge ${response.routes[0]?.data_source === 'sample' ? 'sample' : 'live'}`}>
                  {response.routes[0]?.data_source === 'sample' ? '⚠ Demo data' : '● Live'}
                </span>
              </div>

              {/* Weather strip */}
              {response.weather && (
                <WeatherStrip weather={response.weather} solar={response.solar_at_origin} />
              )}
              {!response.weather && (
                <div className="info-panel warning" style={{ fontSize: 11 }}>
                  Weather data unavailable — scores use solar and model defaults only.
                </div>
              )}

              {/* Route cards */}
              {response.routes.map((route, idx) => (
                <RouteCard
                  key={idx}
                  route={route}
                  isSelected={selectedRouteIdx === idx}
                  onClick={() => setSelectedRouteIdx(selectedRouteIdx === idx ? null : idx)}
                />
              ))}

              {/* Score formula disclosure */}
              <div className="info-panel" style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
                ℹ️ Scores are relative model proxies — not measured temperatures or medical guidance.
                Model: segment_exposure = clamp(0.5×sun + 0.3×UV + 0.2×weather, 0, 1).
                Building/canopy data not available for this pilot area.
              </div>
            </div>
          )}

          {/* ── Placeholder when no results ────────────────────────────────── */}
          {!response && !loading && !error && (
            <div className="info-panel fade-in" style={{ textAlign: 'center', padding: 20 }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>🗺️</div>
              <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
                Select origin &amp; destination,<br />then tap <strong>Find Routes</strong>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                Pilot area: Pune, Maharashtra
              </div>
            </div>
          )}
        </div>

        {/* Attribution */}
        <div className="attribution-bar">
          Map © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors (ODbL) ·
          Routing: <a href="https://github.com/valhalla/valhalla" target="_blank" rel="noreferrer">Valhalla</a> ·
          Weather: <a href="https://open-meteo.com" target="_blank" rel="noreferrer">Open-Meteo</a> (CC BY 4.0)
        </div>
      </aside>

      {/* ── Map ──────────────────────────────────────────────────────────────── */}
      <HeatMap
        origin={origin}
        destination={destination}
        routes={response?.routes ?? []}
        selectedRouteIdx={selectedRouteIdx}
        isSettingOrigin={isSettingOrigin}
        isSettingDest={isSettingDest}
        onOriginSet={handleOriginSet}
        onDestSet={handleDestSet}
      />
    </div>
  );
}
