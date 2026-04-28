import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { RacePoint } from '../App';

interface MapViewerProps {
  data: RacePoint[];
  hoveredIndex: number | null;
}

const UGRC_KEY = 'nerve-radar-lake-second';

const MapViewer: React.FC<MapViewerProps> = ({ data, hoveredIndex }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);

  // 1. Initialize the Map and UGRC Layer
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'ugrc-topo': {
            type: 'raster',
            tiles: [
              `https://discover.agrc.utah.gov/login/path/${UGRC_KEY}/tiles/terrain_basemap/{z}/{x}/{y}`
            ],
            tileSize: 256,
            attribution: '© UGRC'
          }
        },
        layers: [
          {
            id: 'ugrc-topo-layer',
            type: 'raster',
            source: 'ugrc-topo'
          }
        ]
      },
      center: [-111.0937, 40.5884],
      zoom: 9
    });
  }, []);

  // 2. Draw the Route once data arrives
  useEffect(() => {
    const m = map.current;
    if (!m || data.length === 0) return;

    const drawRoute = () => {
      if (m.getSource('ume-route')) return;

      const features = [];
      for (let i = 0; i < data.length - 1; i++) {
        const startCoord = JSON.parse(data[i].geoJson).coordinates;
        const endCoord = JSON.parse(data[i + 1].geoJson).coordinates;
        
        features.push({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: [startCoord, endCoord] },
          properties: { techScore: data[i].techScore }
        });
      }

      m.addSource('ume-route', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features } as any
      });

      m.addLayer({
        id: 'route-core',
        type: 'line',
        source: 'ume-route',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': [
            'interpolate', ['linear'], ['get', 'techScore'],
            1, '#2e7d32',
            5, '#fbc02d',
            8, '#e65100',
            10, '#c62828'
          ],
          'line-width': ['interpolate', ['linear'], ['zoom'], 10, 3, 15, 6]
        }
      });

      const firstCoord = JSON.parse(data[0].geoJson).coordinates;
      m.flyTo({ center: firstCoord as [number, number], zoom: 11 });
    };

    if (m.isStyleLoaded()) {
      drawRoute();
    } else {
      m.once('styledata', drawRoute);
    }
  }, [data]);

  return <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />;
};

export default MapViewer;