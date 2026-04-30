Utah Mixed Epic (UME) - Route Intelligence Dashboard

Overview

The Utah Mixed Epic (UME) Route Intelligence Dashboard is a geospatial web app that helps analyze, visualize, and improve bikepacking route data. Made for ultra-endurance cycling, it goes further than basic GPX line rendering by adding more route detail and calculating a custom Technicality Score using elevation changes, land cover, and official road and trail surface types.

Technical Architecture

This repository has three main parts: a Python spatial data pipeline, a .NET REST API, and a React frontend that uses MapLibre GL.

1. Geospatial Data Pipeline (Python / PostGIS)

The data pipeline takes raw GPX data and turns it into detailed, useful points.

* CRS Enforcement and Densification: Raw routes are converted to EPSG:26912 (NAD83 / UTM Zone 12N) so that all distance and slope calculations use metric units. The route is then split into points every 100 meters.
* USGS Elevation Integration: Elevation data is collected using the py3dep library with the USGS 3D Elevation Program (3DEP). Slope is calculated and then smoothed with a 5-point rolling average to reduce GPS noise.
* UGRC / SGID Integration: The pipeline uses the Utah Geospatial Resource Center (UGRC) State Geographic Information Datasource (SGID). It matches route points to sgid_roads and sgid_trails within 25 meters to get trail names and CARTOCODE surface types.
* NLCD Land Cover: If a point is not on a mapped trail, the pipeline uses local National Land Cover Database (NLCD) data to provide surface types like Barren or Shrub/Scrub.
* Technicality Scoring: A proprietary difficulty score (1-10) is assigned to each 100m segment by interpolating the smoothed slope percentage and applying multipliers based on the SGID surface data, allowing the system to accurately identify high-fatigue "hike-a-bike" sectors.

2. Backend API (.NET 8)

The backend provides a fast, lightweight interface to serve the enriched route data to the client.

* Framework: Built on ASP.NET Core with Swagger/OpenAPI support for documentation and testing.
* Performance: Gzip Response Compression is used to send large GeoJSON files quickly over the network.
* Configuration: A permissive CORS policy (AllowAll) is set up to make local development easy.

3. Frontend Visualization (React / MapLibre GL)

The client-side app shows the intelligence data for users to analyze.

* UGRC Discover Base Maps: The map viewer connects to the UGRC Discover API (discover.agrc.utah.gov) and uses high-quality state topographic raster tiles as the base map.
* Dynamic Route Rendering: The app uses MapLibre GL to draw the densified route. It goes through the coordinates to create a connected LineString FeatureCollection.
* Data-Driven Styling: The route uses data-driven styling, showing a color gradient from green to dark red based on each segment's techScore. This gives users instant visual feedback on route difficulty.

Environment Setup

Database Configuration

The data pipeline needs a running PostGIS instance. Set up a .env file in the /data-pipeline directory with these variables:

* DATABASE_URL: Connection string for the PostGIS database.
* GPX_ROUTE_PATH: Local path to the raw input GPX file.
* NLCD_RASTER_PATH: Local path to the NLCD GeoTIFF file.

Running the Application

1. Database Enrichment: Run the pipeline to densify the route and send it to PostGIS. Use: python data-pipeline/densify_and_enrich.py
2. API: Start the .NET server from the /api/src directory with: dotnet run
3. Frontend: Install dependencies and start the Vite development server from the /frontend directory using: npm install && npm run dev
