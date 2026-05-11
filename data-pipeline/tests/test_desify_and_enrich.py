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
    
    # 1. ARRANGE: 5 points exactly 100 meters apart (UTM Zone 12N)
    points = [ Point(0, 0), Point(100, 0), Point(200, 0), Point(300, 0), Point(400, 0) ]

    # Inject a massive, unrealistic elevation spike at the 3rd point (9000 meters)
    raw_elevations = [1000, 1005, 9000, 1010, 1015]

    gdf = gpd.GeoDataFrame({
        'point_order': [1, 2, 3, 4, 5],
        'elevation_m': raw_elevations,
        'geometry': points
    }, crs="EPSG:26912")

    # 2. ACT: Run the dataframe through your math function
    try:
        result_gdf = calculate_slope(gdf)
    except Exception as e:
        pytest.fail(f"Test Failed: calculate_slope crashed on spike data! Error: {e}")

    # 3. ASSERT: Verify the business logic
    spike_row = result_gdf.loc[result_gdf['point_order'] == 3]
    spike_slope = spike_row['slope_pct_smooth'].iloc[0]

    # Assert that your rolling average / smoothing logic capped this 
    # to something reasonable (e.g., less than a 50% grade), instead of a 7,995% slope.
    assert spike_slope < 50, f"Spike filter failed! The smoothed slope was mathematically impossible: {spike_slope}%"
    assert len(result_gdf) == 5, "The function unexpectedly dropped rows instead of smoothing them."


# ---------------------------------------------------
# TEST 2: The Network Logic (Mocked API)
# ---------------------------------------------------
# NOTE: If you use 'py3dep' inside fetch_elevation, change 'requests.get' to 'densify_and_enrich.py3dep.get_map' or similar.
@patch('densify_and_enrich.requests.get') # We intercept the network call here
def test_fetch_elevation_handles_api_success(mock_api_call):
    """
    Tests that fetch_elevation properly assigns data to the DataFrame 
    when the USGS API returns a valid response, without actually hitting the internet.
    """
    
    # 1. ARRANGE: Fake DataFrame
    points = [ Point(0, 0), Point(100, 0) ]
    gdf = gpd.GeoDataFrame({'point_order': [1, 2], 'geometry': points}, crs="EPSG:26912")
    
    # Fake the API response (assuming it returns JSON or similar structured data)
    mock_response = MagicMock()
    mock_response.json.return_value = {"elevations": [1000, 1005]} # Adjust to match USGS response format
    mock_response.status_code = 200
    mock_api_call.return_value = mock_response

    # 2. ACT
    try:
        result_gdf = fetch_elevation(gdf)
    except Exception as e:
        pytest.fail(f"Test Failed: fetch_elevation crashed during execution! Error: {e}")

    # 3. ASSERT
    assert mock_api_call.called, "The API was never called by the function."
    assert 'elevation_m' in result_gdf.columns, "The elevation column was not added to the DataFrame."