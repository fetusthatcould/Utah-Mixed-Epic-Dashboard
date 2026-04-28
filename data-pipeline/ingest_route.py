import geopandas as gpd
from sqlalchemy import create_engine
import os

# --- CONFIGURATION ---

DB_URL = "postgresql://postgres:geospatial@localhost:5432/ume_db"
engine = create_engine(DB_URL)

def ingest_sgid_layers():
    """Ingest reference layers from UGRC with headers to bypass 403 Forbidden"""
    layers = {
        "sgid_roads": "https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahRoads/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson",
        "sgid_trails": "https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/TrailsAndPathways/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    }
    
    for table_name, url in layers.items():
        print(f"Downloading {table_name}...")
        gdf = gpd.read_file(url)
        # Ensure it matches the route CRS
        gdf = gdf.to_crs(epsg=26912)
        gdf.to_postgis(table_name, engine, if_exists='replace', index=True)
        print(f"Success: {table_name} loaded.")

def ingest_gpx_route(file_path):
    """Ingest the specific UME course"""
    print(f"Loading track points from {file_path}...")
    
    # We use 'track_points' to get individual nodes for point-based analysis
    gdf_points = gpd.read_file(file_path, layer='track_points')
    
    # Standardize to UTM Zone 12N
    gdf_points = gdf_points.to_crs(epsg=26912)
    
    # Optional: Filter columns to keep the DB clean
    # We keep elevation and track_fid for ordering
    cols_to_keep = ['ele', 'track_fid', 'geometry']
    gdf_points = gdf_points[cols_to_keep]
    
    # Push to PostGIS
    gdf_points.to_postgis("raw_route_points", engine, if_exists='replace', index=True)
    print(f"Success: {len(gdf_points)} points loaded into raw_route_points.")

if __name__ == "__main__":
    # 1. Load reference data
    ingest_sgid_layers()
    
    # 2. Load the specific course (Funeral Potato route)
    gpx_path = r"ume-gis-dashboard\data\UPDATED_2025_Utah_Mixed_Epic__Funeral_Potato.gpx"
    if os.path.exists(gpx_path):
        ingest_gpx_route(gpx_path)
    else:
        print(f"Error: File not found at {gpx_path}")