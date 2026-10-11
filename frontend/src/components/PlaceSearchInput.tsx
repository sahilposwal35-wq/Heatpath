import { useState, useEffect, useRef } from 'react';
import { api, type GeocodeResult } from '../services/api';

interface PlaceSearchInputProps {
  id: string;
  label: string;
  icon: string;
  value: { lat: number; lon: number } | null;
  placeName?: string;
  onChange: (coords: { lat: number; lon: number } | null, name?: string) => void;
  isMapSelecting: boolean;
  onToggleMapSelect: () => void;
  placeholder?: string;
}

export default function PlaceSearchInput({
  id,
  label,
  icon,
  value,
  placeName,
  onChange,
  isMapSelecting,
  onToggleMapSelect,
  placeholder = 'Type a place or address...',
}: PlaceSearchInputProps) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync displayed text when placeName or value changes externally
  useEffect(() => {
    if (placeName) {
      setQuery(placeName);
    } else if (value) {
      setQuery(`${value.lat.toFixed(4)}, ${value.lon.toFixed(4)}`);
    } else {
      setQuery('');
    }
  }, [placeName, value]);

  // Click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search when query changes
  useEffect(() => {
    if (!isOpen || query.trim().length < 2) {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    // Don't search if query equals the currently selected place name
    if (placeName && query === placeName) {
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const results = await api.searchPlaces(query);
        setSuggestions(results);
      } catch (err) {
        console.warn('Geocoding error:', err);
      } finally {
        setLoading(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [query, isOpen, placeName]);

  const handleSelect = (item: GeocodeResult) => {
    setQuery(item.name);
    setIsOpen(false);
    setSelectedIndex(-1);
    onChange({ lat: item.lat, lon: item.lon }, item.name);
  };

  const handleClear = () => {
    setQuery('');
    setSuggestions([]);
    setIsOpen(false);
    onChange(null, undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
        handleSelect(suggestions[selectedIndex]);
      } else if (suggestions.length > 0) {
        handleSelect(suggestions[0]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="input-group place-search-group" ref={containerRef}>
      <label className="input-label" htmlFor={id}>
        <span className="icon">{icon}</span> {label}
      </label>

      <div className={`search-input-wrapper ${value ? 'has-value' : ''} ${isMapSelecting ? 'map-selecting' : ''}`}>
        <input
          id={id}
          type="text"
          className="place-search-input"
          placeholder={isMapSelecting ? 'Click on the map to set location...' : placeholder}
          value={query}
          onChange={e => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => {
            if (query.trim().length >= 2) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />

        {loading && <span className="search-spinner" aria-label="Searching..." />}

        {query && !loading && (
          <button
            type="button"
            className="clear-search-btn"
            onClick={handleClear}
            title="Clear place"
          >
            ✕
          </button>
        )}

        <button
          type="button"
          className={`map-pick-btn ${isMapSelecting ? 'active' : ''}`}
          onClick={onToggleMapSelect}
          title={isMapSelecting ? 'Cancel map picking' : 'Click to pick location on map'}
        >
          {isMapSelecting ? '🎯 Tap Map' : '🗺️ Map'}
        </button>
      </div>

      {isOpen && suggestions.length > 0 && (
        <ul className="place-suggestions-list" role="listbox">
          {suggestions.map((item, idx) => (
            <li
              key={`${item.name}-${item.lat}-${item.lon}-${idx}`}
              className={`suggestion-item ${selectedIndex === idx ? 'selected' : ''}`}
              onClick={() => handleSelect(item)}
              role="option"
              aria-selected={selectedIndex === idx}
            >
              <div className="suggestion-icon">📍</div>
              <div className="suggestion-content">
                <div className="suggestion-name">{item.name}</div>
                <div className="suggestion-address">{item.display_name}</div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {isOpen && !loading && query.trim().length >= 2 && suggestions.length === 0 && (
        <div className="no-suggestions">No Pune places found. Try another landmark or tap the map.</div>
      )}
    </div>
  );
}
