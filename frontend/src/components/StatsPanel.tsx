import React, { useMemo } from 'react';
import type { RacePoint } from '../types'; 

interface StatsPanelProps {
  data: RacePoint[];
}

const StatsPanel: React.FC<StatsPanelProps> = ({ data }) => {
  const stats = useMemo(() => {
    if (!data || data.length === 0) return null;

    let eleGainMeters = 0;
    let singletrackCount = 0;
    let primitiveCount = 0;
    let gravelCount = 0;
    let pavedCount = 0;
    let unmappedCount = 0;
    let totalTechScore = 0;

    for (let i = 1; i < data.length; i++) {
      const prev = data[i - 1];
      const curr = data[i];

      // Elevation Gain (Only add positive changes)
      const eleDiff = curr.elevationM - prev.elevationM;
      if (eleDiff > 0) eleGainMeters += eleDiff;

      // Technicality
      totalTechScore += curr.techScore;

      // Surface Breakdown Logic
      if (curr.isSingletrack) {
        singletrackCount++;
      } else if (curr.trailName === 'Unmapped Connection') {
        unmappedCount++;
      } else if (curr.roadSurface >= 7) {
        primitiveCount++;
      } else if (curr.roadSurface >= 5) {
        gravelCount++;
      } else {
        pavedCount++; // 1-4 are paved/highways
      }
    }

    // Math & Conversions
    // 100 meters per point -> convert to miles
    const distMiles = (data.length * 100) / 1609.34; 
    // Meters to Feet
    const gainFeet = eleGainMeters * 3.28084;
    const avgTech = totalTechScore / data.length;

    const totalCategorized = singletrackCount + primitiveCount + gravelCount + pavedCount + unmappedCount;
    const toPct = (count: number) => ((count / Math.max(totalCategorized, 1)) * 100).toFixed(1);

    return {
      distMiles: distMiles.toFixed(1),
      gainFeet: Math.round(gainFeet).toLocaleString(),
      avgTech: avgTech.toFixed(1),
      surfaces: {
        singletrack: toPct(singletrackCount),
        primitive: toPct(primitiveCount),
        gravel: toPct(gravelCount),
        paved: toPct(pavedCount),
        unmapped: toPct(unmappedCount)
      }
    };
  }, [data]);

  if (!stats) {
    return (
      <div style={{ padding: '20px', color: '#666', fontFamily: 'sans-serif' }}>
        Awaiting course data...
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto', fontFamily: 'sans-serif' }}>
      <h2 style={{ margin: 0, fontSize: '1.25rem', borderBottom: '1px solid #ccc', paddingBottom: '10px' }}>
        Course Analytics
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
        <div style={{ background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '0.85rem', color: '#666', textTransform: 'uppercase' }}>Distance</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats.distMiles} mi</div>
        </div>
        <div style={{ background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '0.85rem', color: '#666', textTransform: 'uppercase' }}>Elevation Gain</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats.gainFeet} ft</div>
        </div>
      </div>

      <div style={{ background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
        <div style={{ fontSize: '0.85rem', color: '#666', textTransform: 'uppercase', marginBottom: '5px' }}>Avg Technicality</div>
        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: Number(stats.avgTech) > 6 ? '#e65100' : '#fbc02d' }}>
          {stats.avgTech} / 10
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: '1rem', marginBottom: '15px', color: '#333' }}>Surface Breakdown</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <SurfaceItem label="Singletrack" pct={stats.surfaces.singletrack} color="#c62828" />
          <SurfaceItem label="Primitive / 4WD" pct={stats.surfaces.primitive} color="#e65100" />
          <SurfaceItem label="Gravel" pct={stats.surfaces.gravel} color="#fbc02d" />
          <SurfaceItem label="Paved" pct={stats.surfaces.paved} color="#2e7d32" />
          <SurfaceItem label="Unmapped / Off-Piste" pct={stats.surfaces.unmapped} color="#111" />
        </ul>
      </div>
    </div>
  );
};

// Helper component for the progress bars
const SurfaceItem = ({ label, pct, color }: { label: string; pct: string; color: string }) => (
  <li style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#444' }}>
      <span>{label}</span>
      <span style={{ fontWeight: 'bold' }}>{pct}%</span>
    </div>
    <div style={{ width: '100%', height: '8px', background: '#e0e0e0', borderRadius: '4px', overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width 0.5s ease-out' }} />
    </div>
  </li>
);

export default StatsPanel;