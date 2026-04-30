import geopandas as gpd
from sqlalchemy import create_engine
import os

# --- CONFIGURATION ---

DB_URL = "postgresql://postgres:geospatial@localhost:5432/ume_db"
engine = create_engine(DB_URL)

def ingest_gpx_route(file_path):
    """Ingest the specific UME course and extract its bounding box."""
    print(f"Loading track points from {file_path}...")
    
    # Read the GPX file (which is natively in EPSG:4326 / WGS84)
    gdf_points = gpd.read_file(file_path, layer='track_points')
    
    # 1. Calculate the bounding box BEFORE reprojecting
    # total_bounds returns an array: [minx, miny, maxx, maxy]
    bounds = gdf_points.total_bounds
    
    # Format for the ArcGIS REST API (comma-separated string)
    bbox_string = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}"
    print(f"Calculated Route Bounding Box: {bbox_string}")
    
    # Standardize to UTM Zone 12N for the database
    gdf_points = gdf_points.to_crs(epsg=26912)
    
    # Filter columns to keep the DB clean
    cols_to_keep = ['ele', 'track_fid', 'geometry']
    gdf_points = gdf_points[cols_to_keep]
    
    # Push to PostGIS
    gdf_points.to_postgis("raw_route_points", engine, if_exists='replace', index=True)
    print(f"Success: {len(gdf_points)} points loaded into raw_route_points.")
    
    return bbox_string

def ingest_sgid_layers(bbox_string):
    """Ingest reference layers from UGRC using a spatial envelope filter."""
    
    # 2. Append the spatial parameters to the URL
    # inSR=4326 tells the server our bounding box is in WGS84 coordinates
    spatial_filter = f"&geometry={bbox_string}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects"
    
    layers = {
        "sgid_roads": f"https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahRoads/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson{spatial_filter}",
        "sgid_trails": f"https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/TrailsAndPathways/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson{spatial_filter}"
    }
    
    # 3. Add the User-Agent header (Fixing the 403 issue gracefully)
    storage_options = {'User-Agent': 'UME-Pipeline/1.0 (Interview-Prep)'}
    
    for table_name, url in layers.items():
        print(f"Downloading {table_name}...")
        
        # Pass the storage options to GeoPandas
        gdf = gpd.read_file(url, storage_options=storage_options)
        
        # Ensure it matches the route CRS
        gdf = gdf.to_crs(epsg=26912)
        gdf.to_postgis(table_name, engine, if_exists='replace', index=True)
        print(f"Success: {table_name} loaded with {len(gdf)} features.")

if __name__ == "__main__":
    gpx_path = r"ume-gis-dashboard\data\UPDATED_2025_Utah_Mixed_Epic__Funeral_Potato.gpx"
    
    if os.path.exists(gpx_path):
        # 1. Load the course FIRST to get the bounds
        route_bbox = ingest_gpx_route(gpx_path)
        
        # 2. Pass the bounds to the UGRC layer ingest
        ingest_sgid_layers(route_bbox)
    else:
        print(f"Error: File not found at {gpx_path}")