import type { RouteResult, WeatherInfo, SolarInfo } from '../services/api';


function exposureClass(score: number): string {
  if (score < 0.35) return 'exposure-low';
  if (score < 0.60) return 'exposure-medium';
  return 'exposure-high';
}

function exposureLabel(score: number): string {
  if (score < 0.35) return 'Low';
  if (score < 0.60) return 'Moderate';
  return 'High';
}

function routeClass(label: string): string {
  if (label === 'Fastest') return 'fastest';
  if (label === 'Heat-aware') return 'heat-aware';
  return 'alternative';
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m}`;
  return `${Math.floor(m / 60)}h ${m % 60}`;
}


interface RouteCardProps {
  route: RouteResult;
  isSelected: boolean;
  onClick: () => void;
}

export function RouteCard({ route, isSelected, onClick }: RouteCardProps) {
  const cls = [
    'route-card fade-in',
    routeClass(route.label),
    isSelected ? 'selected' : '',
    route.is_recommended ? 'recommended' : '',
  ].filter(Boolean).join(' ');

  const expClass = exposureClass(route.avg_exposure_score);
  const expPct = Math.round(route.avg_exposure_score * 100);

  return (
    <div
      className={cls}
      onClick={onClick}
      id={`route-card-${route.route_index}`}
      role="button"
      aria-pressed={isSelected}
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}
    >
      {/* Header */}
      <div className="route-card-header">
        <div className="route-label-row">
          <div className={`route-dot ${routeClass(route.label)}`} />
          <span className="route-label">{route.label}</span>
          {route.is_recommended && (
            <span className="recommended-badge">★ Recommended</span>
          )}
        </div>
        <span className={`confidence-badge ${route.data_confidence}`}>
          {route.data_confidence === 'high' ? '✓' : route.data_confidence === 'medium' ? '~' : '⚠'} {route.data_confidence}
        </span>
      </div>

      {/* Score reduction (for recommended non-fastest route) */}
      {route.model_score_reduction_pct != null && route.model_score_reduction_pct > 0 && (
        <div className="score-reduction">
          ↓ {route.model_score_reduction_pct.toFixed(1)}% lower model score vs fastest
        </div>
      )}

      {/* Metrics */}
      <div className="route-metrics">
        <div className="metric-item">
          <span className="metric-value">{route.distance_km.toFixed(1)}</span>
          <span className="metric-unit">km</span>
        </div>
        <div className="metric-item">
          <span className="metric-value">{formatDuration(route.duration_s)}</span>
          <span className="metric-unit">min walk</span>
        </div>
        <div className="metric-item">
          {route.extra_minutes_vs_fastest != null ? (
            <>
              <span className="metric-value" style={{ color: route.extra_minutes_vs_fastest > 0 ? 'var(--warning)' : 'var(--success)' }}>
                +{route.extra_minutes_vs_fastest.toFixed(1)}
              </span>
              <span className="metric-unit">extra min</span>
            </>
          ) : (
            <>
              <span className="metric-value" style={{ color: 'var(--route-fastest)' }}>⚡</span>
              <span className="metric-unit">fastest</span>
            </>
          )}
        </div>
      </div>

      {/* Exposure bar */}
      <div className={`exposure-row ${expClass}`}>
        <div className="exposure-label-row">
          <span className="exposure-label">Estimated Exposure Proxy</span>
          <span className="exposure-value">{exposureLabel(route.avg_exposure_score)} ({expPct}%)</span>
        </div>
        <div className="exposure-bar-track">
          <div
            className="exposure-bar-fill"
            style={{ width: `${expPct}%` }}
            role="progressbar"
            aria-valuenow={expPct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Data source badge */}
      {route.data_source === 'sample' && (
        <div className="info-panel warning" style={{ marginBottom: 8, fontSize: 10 }}>
          ⚠ Demo data — not live. Scores are pre-computed fixtures.
        </div>
      )}

      {/* Explanation (expanded when selected) */}
      {isSelected && (
        <p className="explanation-text fade-in">{route.explanation}</p>
      )}
    </div>
  );
}


interface WeatherStripProps {
  weather: WeatherInfo;
  solar: SolarInfo | null;
}

export function WeatherStrip({ weather, solar }: WeatherStripProps) {
  return (
    <div className="weather-strip fade-in">
      {weather.temperature_c != null && (
        <div className="weather-item">
          <span className="icon">🌡️</span>
          <span className="val">{weather.temperature_c.toFixed(0)}°C</span>
          {weather.apparent_temperature_c != null && (
            <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>
              (feels {weather.apparent_temperature_c.toFixed(0)}°)
            </span>
          )}
        </div>
      )}
      {weather.uv_index != null && (
        <div className="weather-item">
          <span className="icon">☀️</span>
          <span className="val">UV {weather.uv_index.toFixed(1)}</span>
        </div>
      )}
      {weather.cloud_cover_pct != null && (
        <div className="weather-item">
          <span className="icon">☁️</span>
          <span className="val">{weather.cloud_cover_pct.toFixed(0)}%</span>
        </div>
      )}
      {solar && (
        <div className="weather-item">
          <span className="icon">{solar.is_daylight ? '🔆' : '🌙'}</span>
          <span className="val">
            {solar.is_daylight ? `${solar.elevation_deg.toFixed(0)}° elev` : 'Night'}
          </span>
        </div>
      )}
      <div className="weather-item" style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>
        ~1 km grid
      </div>
    </div>
  );
}
