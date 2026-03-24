import io
import json
import zipfile

import pytest
from tornado.httpclient import HTTPError


@pytest.mark.asyncio
async def test_bulk_kmz_export(http_server_client):
    """
    Test the bulk KMZ export endpoint:
    1. Create multiple fields.
    2. Request /api/field/export/kmz/all.
    3. Verify ZIP response headers and content.
    """
    client, base_url = http_server_client

    # 1. Create Field 1
    # Simple polygon
    p1 = {
        "name": "Field A (North)", 
        "geometry": {
            "type": "Polygon", 
            "coordinates": [[[0,0], [0,1], [1,1], [1,0], [0,0]]]
        }
    }
    res1 = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(p1))
    assert res1.code == 200

    # 2. Create Field 2
    # Ensure name has characters that need slugification
    p2 = {
        "name": "Field B / South & East", 
        "geometry": {
            "type": "Polygon", 
            "coordinates": [[[2,2], [2,3], [3,3], [3,2], [2,2]]]
        }
    }
    res2 = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(p2))
    assert res2.code == 200

    # 3. Request Bulk Export
    export_url = f"{base_url}/api/field/export/kmz/all"
    response = await client.fetch(export_url)

    # 4. Verify Headers
    assert response.code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "all_fields_kmz_" in response.headers["Content-Disposition"]
    assert ".zip" in response.headers["Content-Disposition"]

    # 5. Verify ZIP Content
    zip_buffer = io.BytesIO(response.body)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        file_names = zf.namelist()
        
        # Check that we have 2 files
        assert len(file_names) == 2
        
        # Check filenames are slugified correctly
        # "Field A (North)" -> "Field_A_North.kmz" (approximately, depending on implementation)
        # "Field B / South & East" -> "Field_B_South_East.kmz"
        
        # Note: slugify implementation usually replaces non-alphanumeric with underscores or dashes
        # Let's just check if substrings exist to be safe against exact slugify implementation details
        assert any("Field_A_North" in name for name in file_names)
        # "Field B / South & East" -> "Field_B__South__East" (double underscores due to removed chars)
        assert any("Field_B" in name and "South" in name and "East" in name for name in file_names)

        # Verify files are valid KMZ (check for PK signature inside)
        for name in file_names:
            with zf.open(name) as kmz_file:
                content = kmz_file.read()
                assert content.startswith(b'PK'), f"{name} is not a valid zip/kmz file"

@pytest.mark.asyncio
async def test_bulk_kmz_export_empty_db(http_server_client):
    """
    Test bulk export when no fields exist.
    Should return 404 with error message.
    """
    client, base_url = http_server_client
    
    # Ensure DB is empty
    
    export_url = f"{base_url}/api/field/export/kmz/all"
    
    with pytest.raises(HTTPError) as e:
        await client.fetch(export_url)
    
    assert e.value.code == 404
