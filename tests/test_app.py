import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import socket
from unittest.mock import patch

# ПРИНУДИТЕЛЬНО ПЕРЕКЛЮЧАЕМ БАЗУ ДО ИМПОРТА APP
import db
db.database = db.get_database(':memory:')

import app # Теперь app.database будет ссылаться на ту же memory базу
from app import make_app, calculate_accurate_area
from db import Field, Owner

from tornado.httpclient import AsyncHTTPClient, HTTPError
from shapely.geometry import shape

def find_unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@pytest.fixture(scope='function')
def test_db():
    db.database.connect(reuse_if_open=True)
    db.database.create_tables([Owner, Field])
    yield db.database
    db.database.drop_tables([Owner, Field])
    db.database.close()

@pytest.fixture
async def http_server_client(test_db):
    application = make_app()
    port = find_unused_port()
    server = application.listen(port)
    client = AsyncHTTPClient()
    yield client, f"http://localhost:{port}"
    client.close()
    server.stop()

# --- ТЕСТЫ ---

def test_accurate_area_calculation():
    geojson_poly = {"type": "Polygon", "coordinates": [[[19.0, 48.0], [19.00135, 48.0], [19.00135, 48.0009], [19.0, 48.0009], [19.0, 48.0]]]}
    poly = shape(geojson_poly)
    area = calculate_accurate_area(poly)
    assert 9000 < area < 11000 

async def test_api_field_lifecycle(http_server_client):
    client, base_url = http_server_client
    payload = {"name": "LC", "geometry": {"type": "Polygon", "coordinates": [[[19,48], [19.01,48], [19.01,48.01], [19,48.01], [19,48]]]}}
    res = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(payload))
    fid = json.loads(res.body)["id"]
    await client.fetch(f"{base_url}/api/field/rename/{fid}", method='PUT', body=json.dumps({"new_name": "R"}))
    await client.fetch(f"{base_url}/api/field/update_details/{fid}", method='PUT', body=json.dumps({"land_status": "A", "parcel_number": "1"}))
    res = await client.fetch(f"{base_url}/api/fields_data")
    data = json.loads(res.body)["data"][0]
    assert data["name"] == "R"
    assert data["land_status"] == "A"

async def test_owner_assignment(http_server_client):
    client, base_url = http_server_client
    await client.fetch(f"{base_url}/api/owner/add", method='POST', body=json.dumps({"name": "Jan"}))
    res_o = await client.fetch(f"{base_url}/api/owners")
    oid = json.loads(res_o.body)["data"][0]["id"]
    p = {"name": "F", "geometry": {"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]}}
    res_f = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(p))
    fid = json.loads(res_f.body)["id"]
    await client.fetch(f"{base_url}/api/field/assign_owner/{fid}", method='PUT', body=json.dumps({"owner_id": oid}))
    res = await client.fetch(f"{base_url}/api/fields_data")
    data = json.loads(res.body)["data"]
    field = next(x for x in data if x["id"] == fid)
    assert field["owner"] == "Jan"

async def test_static_routes(http_server_client):
    client, base_url = http_server_client
    for p in ["/", "/sw.js", "/manifest.json"]:
        r = await client.fetch(f"{base_url}{p}")
        assert r.code == 200

async def test_error_handling(http_server_client):
    client, base_url = http_server_client
    with pytest.raises(HTTPError) as e:
        await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps({"name": "X"}))
    assert e.value.code == 400
