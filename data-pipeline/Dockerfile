# 1. Base Image: Use a lightweight, official Python runtime
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. System Dependencies: Install underlying C-libraries needed for spatial data (GeoPandas/PostGIS)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy ONLY requirements first to leverage Docker cache for dependencies
COPY requirements.txt .

# 5. Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your Python scripts into the container
COPY . .

# 7. Execution: What should the container do when it turns on?
# (We will default to your ingestion script, but Cloud Run can override this)
CMD ["python", "ingest_route.py"]