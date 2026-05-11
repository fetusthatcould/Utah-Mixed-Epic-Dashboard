import pytest
import os
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------
# MOCK THE ENVIRONMENT
# This prevents SQLAlchemy from trying to connect to a real 
# database when the test runner imports ingest_route.py
# ---------------------------------------------------------
os.environ["DATABASE_URL"] = "postgresql://fake_user:fake_pass@localhost:5432/fake_db"

from ingest_route import ingest_sgid_layers

@patch('ingest_route.gpd.GeoDataFrame.to_postgis') # Intercept the DB write
@patch('ingest_route.requests.get')                # Intercept the UGRC API call
def test_ingest_sgid_layers_empty_bounding_box(mock_get, mock_to_postgis, capfd):
    """
    Tests that passing a bounding box with zero roads (like the middle of the ocean)
    results in an empty DataFrame and does not crash the pagination or projection logic.
    """
    
    # 1. ARRANGE: Create a fake UGRC API response
    # We mock the response to simulate the API finding zero features in the bounding box
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "features": [] 
    }
    # Ensure raise_for_status doesn't throw an error
    mock_response.raise_for_status.return_value = None 
    mock_get.return_value = mock_response

    # A fake bounding box far outside Utah (minx, miny, maxx, maxy)
    ocean_bbox_string = "-1.0,-1.0,1.0,1.0"

    # 2. ACT: Run the function
    try:
        ingest_sgid_layers(ocean_bbox_string)
    except Exception as e:
        pytest.fail(f"Test Failed: Script crashed on an empty bounding box! Error: {e}")

    # 3. ASSERT: Verify the script's behavior
    # capfd captures the print() statements from your script
    out, err = capfd.readouterr()
    
    # Check that the pagination loop broke immediately and gracefully
    assert "Building GeoDataFrame for sgid_roads with 0 total features" in out
    
    # Verify that to_postgis was still called exactly twice (once for roads, once for trails).
    # This is CRITICAL: writing an empty dataframe is how we clear out the old tables 
    # so we don't accidentally leave previous route data in the database.
    assert mock_to_postgis.call_count == 2