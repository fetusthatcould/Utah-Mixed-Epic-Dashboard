"""
Utah Mixed Epic (UME) - Route Enrichment Pipeline
Processes raw GPX/LineString data to generate high-resolution points (100m intervals) 
enriched with elevation, land cover (NLCD), and SGID road/trail attributes.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import numpy as np
import py3dep
import rasterio
import logging
from typing import Optional, List, Tuple

# --- CONFIGURATION ---
CONFIG = {
    "DB_URL": "postgresql://postgres:geospatial@localhost:5432/ume_db",
    "NLCD_PATH": r"ume-gis-dashboard\data\Annual_NLCD_LndCov_2024_CU_C1V1_03aeeaf5-16c8-44eb-88e8-1bd94bd97738.tiff",
    "STEP_METERS": 100,
    "BATCH_SIZE": 5000,
    "SNAPPING_DISTANCE": 25,  # Meters to search for nearest road/trail
}

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_engine() -> Engine:
    """Creates the SQLAlchemy engine for PostGIS connection."""
    return create_engine(CONFIG["DB_URL"])

def densify_route(engine: Engine, step_meters: int = 100) -> Optional[gpd.GeoDataFrame]:
    """
    Interpolates points along the raw route at fixed intervals.
    
    Args:
        engine: PostGIS connection engine.
        step_meters: Distance between points in meters.
        
    Returns:
        GeoDataFrame of points or None if no route is found.
    """
    logging.info("Step 1: Loading raw route from database...")
    query = "SELECT * FROM raw_route"
    gdf = gpd.read_postgis(query, engine, geom_col='geometry')
    
    if gdf.empty:
        logging.error("No routes found in 'raw_route' table.")
        return None

    # Process the first LineString found
    line = gdf.geometry.iloc[0] 
    logging.info(f"Route length: {line.length:.0f} meters")
     
    # Generate distances for interpolation
    distances = np.arange(0, line.length, step_meters)
    points = [line.interpolate(dist) for dist in distances]
    
    points_gdf = gpd.GeoDataFrame(
        {'point_order': range(len(points))}, 
        geometry=points, 
        crs=gdf.crs
    )
    
    logging.info(f"Generated {len(points_gdf)} points.")
    return points_gdf

def fetch_elevation(gdf: gpd.GeoDataFrame, batch_size: int = 5000) -> gpd.GeoDataFrame:
    """
    Retrieves elevation data from USGS via py3dep.
    
    Args:
        gdf: GeoDataFrame containing points.
        batch_size: Number of points per API request to prevent timeouts.
    """
    logging.info(f"Step 3: Fetching elevation from USGS (Batch size: {batch_size})...")
    
    # py3dep requires WGS84 for coordinate sampling
    points_4326 = gdf.to_crs(epsg=4326)
    coords = list(zip(points_4326.geometry.x, points_4326.geometry.y))
    
    all_elevations = []
    total_points = len(coords)
    
    for i in range(0, total_points, batch_size):
        batch = coords[i : i + batch_size]
        logging.info(f"  Processing batch {i//batch_size + 1}...")
        try:
            # Using 'tep' source as per regional availability
            elev = py3dep.elevation_bycoords(batch, source="tep")
            all_elevations.extend(elev)
        except Exception as e:
            logging.warning(f"  Elevation batch error: {e}. Filling with NaN.")
            all_elevations.extend([np.nan] * len(batch))
            
    gdf['elevation_m'] = all_elevations
    return gdf

def fetch_sgid_data(gdf: gpd.GeoDataFrame, engine: Engine) -> gpd.GeoDataFrame:
    """
    Spatial join against SGID (State Geographic Information Database) tables 
    to identify road surfaces and trail names.
    """
    logging.info("Step 5: Enriching with SGID Roads and Trails...")
    
    # Temp table for database-side spatial join
    gdf.to_postgis("temp_points", engine, if_exists='replace', index=True)
    
    # Snap to nearest trail/road within the configured buffer (25m)
    query = f"""
    SELECT DISTINCT ON (p.point_order)
        p.point_order,
        COALESCE(t."PrimaryName", r."FULLNAME", 'Unmapped Connection') as trail_name,
        r."CARTOCODE" as road_surface,
        (t."PrimaryName" IS NOT NULL) as is_singletrack
    FROM temp_points p
    LEFT JOIN sgid_roads r ON ST_DWithin(p.geometry, r.geometry, {CONFIG['SNAPPING_DISTANCE']})
    LEFT JOIN sgid_trails t ON ST_DWithin(p.geometry, t.geometry, {CONFIG['SNAPPING_DISTANCE']})
    ORDER BY p.point_order, ST_Distance(p.geometry, t.geometry) ASC;
    """
    
    sgid_df = pd.read_sql(query, engine)
    gdf = gdf.merge(sgid_df, on='point_order', how='left')
    
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS temp_points;"))
        
    return gdf

def fetch_land_cover_local(gdf: gpd.GeoDataFrame, raster_path: str) -> gpd.GeoDataFrame:
    """
    Samples land cover data from a local NLCD GeoTIFF.
    """
    logging.info("Step 4: Sampling local NLCD data...")
    
    try:
        with rasterio.open(raster_path) as src:
            # Reproject points to match Raster CRS (usually EPSG:5070)
            points_in_raster_crs = gdf.to_crs(src.crs)
            coords = [(pt.x, pt.y) for pt in points_in_raster_crs.geometry]
            
            sampled_values = [val[0] for val in src.sample(coords)]
            gdf['land_cover_code'] = sampled_values
            
    except Exception as e:
        logging.error(f"NLCD Sampling Failed: {e}")
        gdf['land_cover_code'] = 0
        
    return gdf

def calculate_slope(gdf: gpd.GeoDataFrame, step_meters: int = 100) -> gpd.GeoDataFrame:
    """Calculates percent slope and applies a 5-point rolling average to smooth GPS jitter."""
    gdf['elev_diff'] = gdf['elevation_m'].diff()
    gdf['slope_pct'] = (gdf['elev_diff'] / step_meters) * 100
    
    # Smooth over 500m window (5 points @ 100m)
    gdf['slope_pct_smooth'] = gdf['slope_pct'].rolling(window=5, center=True).mean()
    return gdf

def add_technicality_score(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Assigns a difficulty score (1-10) based on slope and surface type.
    Crucial for identifying 'hike-a-bike' or high-fatigue sectors.
    """
    logging.info("Step 7: Calculating Technicality Scores...")
    
    # Linear interpolation of slope to a 1-10 scale
    gdf['slope_factor'] = np.interp(
        gdf['slope_pct_smooth'].fillna(0), 
        [0, 3, 7, 12, 15], 
        [1, 3, 6, 10, 10]
    )

    def get_surface_multiplier(row):
        # 1. Singletrack Tax
        if pd.notnull(row['trail_name']) and row['is_singletrack']:
            return 2.5 
            
        # 2. Road Surface Mapping
        surface_map = {
            'Paved': 0.5, 'Gravel': 1.2, 'Dirt': 1.5, 
            'Primitive': 2.5, 'Impassable': 5.0
        }
        if row['road_surface'] in surface_map:
            return surface_map[row['road_surface']]
            
        # 3. NLCD Fallback (e.g., 31=Barren, 52=Shrub/Scrub)
        nlcd_map = {31: 1.5, 52: 1.2, 90: 1.3}
        return nlcd_map.get(row['land_cover_code'], 1.0)

    gdf['surface_mult'] = gdf.apply(get_surface_multiplier, axis=1)
    gdf['tech_score'] = (gdf['slope_factor'] * gdf['surface_mult']).clip(1, 10)
    
    return gdf

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    db_engine = get_engine()
    
    try:
        # 1. Geometry Processing
        enriched_gdf = densify_route(db_engine, CONFIG["STEP_METERS"])
        if enriched_gdf is None: exit(1)

        # 2. Enrichment Sequence
        enriched_gdf = fetch_elevation(enriched_gdf, CONFIG["BATCH_SIZE"]).fillna(0)
        enriched_gdf = fetch_land_cover_local(enriched_gdf, CONFIG["NLCD_PATH"])
        enriched_gdf = fetch_sgid_data(enriched_gdf, db_engine)

        # 3. Physics & Difficulty Logic
        enriched_gdf = calculate_slope(enriched_gdf, CONFIG["STEP_METERS"])
        enriched_gdf = add_technicality_score(enriched_gdf)

        # 4. Final Data Cleanup
        final_gdf = enriched_gdf.dropna(subset=['elevation_m', 'slope_pct_smooth'])
        logging.info(f"Cleanup complete: {len(final_gdf)} valid points.")

        # 5. Database Commit
        logging.info("Pushing enriched data to 'ume_enriched_points'...")
        with db_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE ume_enriched_points;"))
            final_gdf.to_postgis("ume_enriched_points", conn, if_exists='append', index=False)
        
        logging.info("Pipeline executed successfully.")

    except Exception as e:
        logging.critical(f"Pipeline Failed: {e}", exc_info=True)