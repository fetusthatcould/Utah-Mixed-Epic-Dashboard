// src/types.ts
export interface RacePoint {
  pointOrder: number;
  elevationM: number;
  slopePctSmooth: number;
  techScore: number;
  trailName: string;
  roadSurface: number;
  isSingletrack: boolean;
  geoJson: string;
}