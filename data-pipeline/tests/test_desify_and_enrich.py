import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from unittest.mock import patch, MagicMock

# Import YOUR exact functions
from densify_and_enrich import calculate_slope, fetch_elevation

# ---------------------------------------------------
# TEST 1: The Math Logic (No internet required)
# ---------------------------------------------------
def test_calculate_slope_filters_gps_spike():
    """
    Tests that a massive GPS multipath elevation spike is successfully 
    filtered or smoothed out by calculate_slope().
    """
    
    points = [Point(x * 100, 0) for x in range(10)] # 0m, 100m, 200m ... 9000m
    
    # 10 elevations. The spike is safely in the middle at index 5.
    raw_elevations = [1000, 1005, 1010, 1015, 1020, 9000, 1025, 1030, 1035, 1040]

    gdf = gpd.GeoDataFrame({
        'point_order': list(range(1, 11)),
        'elevation_m': raw_elevations,
        'geometry': points
    }, crs="EPSG:26912")

    # ACT: Run the dataframe through your math function
    try:
        result_gdf = calculate_slope(gdf)
    except Exception as e:
        pytest.fail(f"Test Failed: calculate_slope crashed on spike data! Error: {e}")

  # Assert against the 6th point (where the 9000 spike happened)
    spike_row = result_gdf.loc[result_gdf['point_order'] == 6]
    spike_slope = spike_row['slope_pct_smooth'].iloc[0]

    assert not pd.isna(spike_slope), "Slope evaluated to NaN! The rolling window might be too large."
    assert spike_slope < 50, f"Spike filter failed! Slope was: {spike_slope}%"

# ---------------------------------------------------
# TEST 2: The Network Logic (Mocked API)
# ---------------------------------------------------
# NOTE: If you use 'py3dep' inside fetch_elevation, change 'requests.get' to 'densify_and_enrich.py3dep.get_map' or similar.
@patch('densify_and_enrich.py3dep.elevation_bycoords') # We intercept the network call heres
def test_fetch_elevation_handles_api_success(mock_api_call):
    """
    Tests that fetch_elevation properly assigns data to the DataFrame 
    when the USGS API returns a valid response, without actually hitting the internet.
    """
    
    # 1. ARRANGE: Fake DataFrame
    points = [ Point(0, 0), Point(100, 0) ]
    gdf = gpd.GeoDataFrame({'point_order': [1, 2], 'geometry': points}, crs="EPSG:26912")
    
    # py3dep directly returns a list of elevations, NOT an HTTP response.
    # So we simply tell the mock to return exactly what the script expects.
    mock_api_call.return_value = [1000, 1005] 
    
    # 2. ACT
    try:
        result_gdf = fetch_elevation(gdf)
    except Exception as e:
        pytest.fail(f"Test Failed: fetch_elevation crashed during execution! Error: {e}")

    # 3. ASSERT
    assert mock_api_call.called, "The API was never called by the function."
    assert 'elevation_m' in result_gdf.columns, "The elevation column was not added to the DataFrame."
    
    # Optional: Verify the values actually matched!
    assert result_gdf['elevation_m'].iloc[0] == 1000
    assert result_gdf['elevation_m'].iloc[1] == 1005

   