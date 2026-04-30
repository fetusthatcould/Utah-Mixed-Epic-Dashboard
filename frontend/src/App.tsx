import React, { useEffect, useState } from 'react';
import axios from 'axios';
import MapViewer from './components/MapViewer';
import StatsPanel  from './components/StatsPanel';
//import ElevationProfile from './components/ElevationProfile';
import type { RacePoint } from './types'; 
import './index.css';

// Ensure this matches your local .NET API port
const API_URL = 'http://localhost:5117/api/Route/intelligence';


const App: React.FC = () => {
  const [routeData, setRouteData] = useState<RacePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  useEffect(() => {
    const fetchRoute = async () => {
      try {
        const response = await axios.get<RacePoint[]>(API_URL);
        setRouteData(response.data);
      } catch (error) {
        console.error('Failed to fetch route data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchRoute();
  }, []);

  if (loading) return <div className="loading">Loading Utah Mixed Epic Course Data...</div>;

  return (
    <div className="dashboard-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#f4f4f9' }}>
      <header style={{ padding: '15px 20px', background: '#1a1a1a', color: 'white' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Race Intelligence Dashboard</h1>
      </header>
      
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 3, position: 'relative' }}>
          <MapViewer data={routeData} hoveredIndex={hoveredIndex} />
        </div>
        <div style={{ flex: 1, minWidth: '300px', borderLeft: '2px solid #ddd' }}>
         <StatsPanel data={routeData} />
        </div>
      </div>

      <div style={{ height: '250px', borderTop: '2px solid #ddd', background: 'white' }}>
        {/* <ElevationProfile data={routeData} onHover={setHoveredIndex} /> */}
      </div>
    </div>
  );
};

export default App;