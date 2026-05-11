import geopandas as gpd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import requests

load_dotenv()

# --- CONFIGURATION ---
# The second argument in os.getenv serves as a fallback/default if the variable isn't found
GPX_ROUTE_PATH = os.getenv("GPX_ROUTE_PATH", r"ume-gis-dashboard\data\UPDATED_2025_Utah_Mixed_Epic__Funeral_Potato.gpx")
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

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
    """Ingest reference layers from UGRC using spatial envelope and pagination."""
    
    spatial_filter = f"&geometry={bbox_string}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects"
    
    # Notice we don't put f=geojson here yet, we will construct the final URL in the loop
    layers = {
        "sgid_roads": f"https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahRoads/FeatureServer/0/query?outFields=*&where=1%3D1{spatial_filter}",
        "sgid_trails": f"https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/TrailsAndPathways/FeatureServer/0/query?outFields=*&where=1%3D1{spatial_filter}"
    }
    
    headers = {'User-Agent': 'UME-Pipeline/1.0 (Interview-Prep)'}
    for table_name, base_url in layers.items():
        print(f"Downloading {table_name} (Handling Pagination)...")
        
        all_features = []
        offset = 0
        chunk_size = 2000 # UGRC's known MaxRecordCount
        
        while True:
            # We explicitly define resultRecordCount to take control of the pagination chunk
            paginated_url = f"{base_url}&f=geojson&resultOffset={offset}&resultRecordCount={chunk_size}"
            
            response = requests.get(paginated_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise ValueError(f"UGRC API Error: {data['error']}")
                
            features = data.get("features", [])
            
            if not features:
                # Failsafe: if empty, we are done
                break
                
            all_features.extend(features)
            print(f"   ...fetched {len(features)} records (Total so far: {len(all_features)})")
            
            # The bulletproof pagination check for GeoJSON:
            if len(features) == chunk_size:
                # We hit the ceiling, so there is likely more data
                offset += chunk_size
            else:
                # We received a partial chunk, meaning we reached the end of the dataset
                break
                
        # Parse the complete list of features directly into GeoPandas
        print(f"Building GeoDataFrame for {table_name} with {len(all_features)} total features...")
        gdf = gpd.GeoDataFrame.from_features(all_features)

        if gdf.empty:
             # Defensively create the geometry column so to_crs() and to_postgis() don't crash
            gdf = gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs="EPSG:4326")
        else:
    # Only set crs if there is actual data
            gdf = gdf.set_crs("EPSG:4326")

        # Now this will safely work whether there are 1,000 roads or 0 roads
            gdf = gdf.to_crs(epsg=26912)
    
        # Explicitly set the incoming CRS (GeoJSON is always WGS84) and project
        gdf.set_crs(epsg=4326, inplace=True)
           
        
        # Push to PostGIS
        gdf.to_postgis(table_name, engine, if_exists='replace', index=True)
        print(f"Success: {table_name} loaded into database.")

if __name__ == "__main__":
    
    if os.path.exists(GPX_ROUTE_PATH):
        # 1. Load the course FIRST to get the bounds
        route_bbox = ingest_gpx_route(GPX_ROUTE_PATH)
        
        # 2. Pass the bounds to the UGRC layer ingest
        ingest_sgid_layers(route_bbox)
    else:
        print(f"Error: File not found at {GPX_ROUTE_PATH}")