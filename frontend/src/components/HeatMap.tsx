import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { RouteResult } from '../services/api';

// Fix Leaflet default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const originIcon = L.divIcon({
  className: '',
  html: `<div style="
    width:18px;height:18px;border-radius:50%;
    background:#22c55e;border:3px solid white;
    box-shadow:0 0 12px #22c55e80;
  "></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

const destIcon = L.divIcon({
  className: '',
  html: `<div style="
    width:18px;height:18px;border-radius:50%;
    background:#fb923c;border:3px solid white;
    box-shadow:0 0 12px #fb923c80;
  "></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

interface MapClickHandlerProps {
  isSettingOrigin: boolean;
  isSettingDest: boolean;
  onOriginSet: (lat: number, lon: number) => void;
  onDestSet: (lat: number, lon: number) => void;
}

function MapClickHandler({
  isSettingOrigin, isSettingDest, onOriginSet, onDestSet
}: MapClickHandlerProps) {
  useMapEvents({
    click(e) {
      if (isSettingOrigin) onOriginSet(e.latlng.lat, e.latlng.lng);
      else if (isSettingDest) onDestSet(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

const ROUTE_COLORS: Record<string, string> = {
  'Fastest': '#38bdf8',
  'Heat-aware': '#fb923c',
};

function getRouteColor(label: string, idx: number): string {
  if (ROUTE_COLORS[label]) return ROUTE_COLORS[label];
  const colors = ['#a78bfa', '#34d399', '#f472b6'];
  return colors[idx % colors.length];
}

interface HeatMapProps {
  origin: { lat: number; lon: number } | null;
  destination: { lat: number; lon: number } | null;
  routes: RouteResult[];
  selectedRouteIdx: number | null;
  isSettingOrigin: boolean;
  isSettingDest: boolean;
  onOriginSet: (lat: number, lon: number) => void;
  onDestSet: (lat: number, lon: number) => void;
}

export default function HeatMap({
  origin, destination, routes,
  selectedRouteIdx,
  isSettingOrigin, isSettingDest,
  onOriginSet, onDestSet,
}: HeatMapProps) {
  const PILOT_CENTER: [number, number] = [18.5204, 73.8567];

  return (
    <div className="map-container">
      <MapContainer
        center={PILOT_CENTER}
        zoom={14}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        {/* Dark map tiles */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          maxZoom={19}
        />

        <MapClickHandler
          isSettingOrigin={isSettingOrigin}
          isSettingDest={isSettingDest}
          onOriginSet={onOriginSet}
          onDestSet={onDestSet}
        />

        {/* Route polylines */}
        {routes.map((route, idx) => {
          const color = getRouteColor(route.label, idx);
          const isSelected = selectedRouteIdx === idx;
          const isRecommended = route.is_recommended;
          // Convert [lon, lat] → [lat, lon] for Leaflet
          const positions: [number, number][] = route.geometry.map(
            ([lon, lat]) => [lat, lon]
          );
          return (
            <Polyline
              key={`route-${idx}`}
              positions={positions}
              color={color}
              weight={isSelected || isRecommended ? 5 : 3}
              opacity={isSelected ? 1.0 : isRecommended ? 0.9 : 0.55}
              dashArray={isSelected ? undefined : (isRecommended ? undefined : '6 4')}
            />
          );
        })}

        {/* Origin marker */}
        {origin && (
          <Marker position={[origin.lat, origin.lon]} icon={originIcon}>
            <Popup>
              <div style={{ color: '#0f172a', fontSize: 12 }}>
                <strong>Origin</strong><br />
                {origin.lat.toFixed(5)}, {origin.lon.toFixed(5)}
              </div>
            </Popup>
          </Marker>
        )}

        {/* Destination marker */}
        {destination && (
          <Marker position={[destination.lat, destination.lon]} icon={destIcon}>
            <Popup>
              <div style={{ color: '#0f172a', fontSize: 12 }}>
                <strong>Destination</strong><br />
                {destination.lat.toFixed(5)}, {destination.lon.toFixed(5)}
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      {/* Map legend */}
      {routes.length > 0 && (
        <div className="map-legend">
          <h4>Routes</h4>
          {routes.map((route, idx) => (
            <div key={idx} className="legend-item">
              <div
                className="legend-line"
                style={{ background: getRouteColor(route.label, idx) }}
              />
              <span style={{ color: 'var(--text-secondary)', fontSize: 11.5 }}>
                {route.label}
                {route.is_recommended && ' ★'}
              </span>
            </div>
          ))}
          <div className="legend-item" style={{ marginTop: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: '#22c55e', border: '1.5px solid white'
            }} />
            <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>Origin</span>
          </div>
          <div className="legend-item">
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: '#fb923c', border: '1.5px solid white'
            }} />
            <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>Destination</span>
          </div>
        </div>
      )}
    </div>
  );
}
