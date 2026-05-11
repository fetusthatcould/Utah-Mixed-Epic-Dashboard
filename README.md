# UME Dashboard

This repository contains the full Utah Mixed Epic (UME) Dashboard application, including:

- `data-pipeline/` — Python-based data ingestion and enrichment pipeline
- `api/src/` — ASP.NET Core Web API that serves route intelligence data
- `frontend/` — React + TypeScript + Vite user interface

## Overview

The application pipeline is designed to:

1. Ingest raw GPX route data and spatial reference layers.
2. Store route and reference data in PostGIS.
3. Densify the route into fixed-interval points.
4. Enrich those points with elevation, land cover, trail, and road attributes.
5. Expose the resulting dataset through an API.
6. Render the enriched route data in a frontend map UI.

## Resource Highlights
UGRC's Giza/WMTS tile services for high-performance shaded terrain (terrain_basemap).
UGRC SGID ArcGIS REST API for dynamic, bounding-box queries of UtahRoads and TrailsAndPathways to accurately classify segments.



## Repository layout

- `data-pipeline/`
  - `ingest_route.py` — loads GPX route points into PostGIS and imports SGID road/trail reference layers.
  - `densify_and_enrich.py` — interpolates points along the route, fetches elevation, and applies enrichment.
  - `requirements.txt` — Python dependencies for the pipeline.
  - `data/` — local data storage for large files (ignored by git).

- `api/src/`
  - `Program.cs` — ASP.NET Core app setup, including CORS and Swagger.
  - `Controllers/RouteController.cs` — exposes route intelligence at `GET /api/route/intelligence`.
  - `Models/RacePoint.cs` — response model for the frontend.
  - `appsettings.json` / `appsettings.Development.json` — API configuration.

- `frontend/`
  - `package.json` — frontend dependencies and scripts.
  - `src/` — React application source.
  - `public/` — static assets.
  - `README.md` — frontend-specific documentation.

## Environment variables

The pipeline and API both rely on environment configuration. Create a `.env` file in the repository root or the appropriate working directory with values like:

```env
DATABASE_URL=postgresql://user:password@host:port/database
GPX_ROUTE_PATH=path/to/route.gpx
NLCD_RASTER_PATH=path/to/nlcd_raster.tiff
```

### Required variables

- `DATABASE_URL` — PostGIS connection string used by the Python pipeline.
- `GPX_ROUTE_PATH` — path to the GPX file to ingest.
- `NLCD_RASTER_PATH` — path to the NLCD raster file for land cover lookup.

## Data pipeline

### Install dependencies

From the repository root:

```bash
python -m pip install -r data-pipeline/requirements.txt
```

### Run the pipeline

1. Ingest the GPX route and SGID reference layers:

```bash
python data-pipeline/ingest_route.py
```

2. Densify and enrich the route points:

```bash
python data-pipeline/densify_and_enrich.py
```

The pipeline expects a PostGIS-enabled database and will load intermediate tables such as `raw_route_points` and reference layers.

## API

### Run the API

From the repository root:

```bash
cd api/src
dotnet run
```

The API is configured with a permissive CORS policy in `Program.cs` and exposes Swagger in development.

### Endpoint

- `GET /api/route/intelligence`

This endpoint returns enriched route points from the `v_ui_route_layer` database view, including fields such as:

- `PointOrder`
- `ElevationM`
- `SlopePctSmooth`
- `TechScore`
- `LandCoverType`
- `CumulativeFatigueIndex`
- `FoodScore`
- `WaterScore`
- `RoadSurface`
- `TrailName`
- `IsSingletrack`
- `GeoJson`

## Frontend

### Install dependencies

From the `frontend` folder:

```bash
cd frontend
npm install
```

### Run locally

```bash
npm run dev
```

### Build

```bash
npm run build
```

### Preview production build

```bash
npm run preview
```

## Notes

- Large data files are intentionally ignored from git.
- The frontend reads enriched route geometry from the API.
- The API is designed to serve a PostGIS-backed route intelligence dataset.

## Additional resources

- `frontend/README.md` — frontend-specific setup and notes.
- `data-pipeline/requirements.txt` — pipeline dependency list.
- `api/src/Ume.Intelligence.Api.csproj` — backend project definition.
