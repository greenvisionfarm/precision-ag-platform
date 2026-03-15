import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ПРИНУДИТЕЛЬНО УСТАНАВЛИВАЕМ ОКРУЖЕНИЕ ТЕСТОВ
os.environ['FIELD_MAPPER_ENV'] = 'test'

import pytest
import json
import socket
from unittest.mock import patch

import db
import app 
from app import make_app
from src.services.gis_service import calculate_accurate_area
from db import Field, Owner, initialize_db

from tornado.httpclient import AsyncHTTPClient, HTTPError
from shapely.geometry import shape

def find_unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@pytest.fixture(scope='function')
def test_db():
    # Удаляем старый файл тестовой базы, если он остался
    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)
    
    # Инициализируем чистую базу
    initialize_db()
    db.database.connect(reuse_if_open=True)
    yield db.database
    db.database.close()
    
    # Удаляем после теста (по желанию)
    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)

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
    data = json.loads(res.body)["data"]
    field = next(x for x in data if x["id"] == fid)
    assert field["name"] == "R"
    assert field["land_status"] == "A"

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

async def test_api_field_get(http_server_client):
    client, base_url = http_server_client
    # 1. Создаем поле
    p = {"name": "Detail Test", "geometry": {"type": "Polygon", "coordinates": [[[19,48], [19.01,48], [19.01,48.01], [19,48.01], [19,48]]]}}
    res_f = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(p))
    fid = json.loads(res_f.body)["id"]
    
    # 2. Получаем детали
    res = await client.fetch(f"{base_url}/api/field/{fid}")
    data = json.loads(res.body)
    
    assert data["id"] == fid
    assert data["name"] == "Detail Test"
    assert "geometry" in data
    assert "area" in data
    assert data["geometry"]["type"] == "Polygon"

async def test_api_field_updates_all_actions(http_server_client):
    client, base_url = http_server_client
    # Создаем поле
    p = {"name": "Update Test", "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}
    res = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(p))
    fid = json.loads(res.body)["id"]

    # 1. Rename
    await client.fetch(f"{base_url}/api/field/rename/{fid}", method='PUT', body=json.dumps({"new_name": "NewName"}))
    
    # 2. Update Details
    await client.fetch(f"{base_url}/api/field/update_details/{fid}", method='PUT', body=json.dumps({"land_status": "Owned", "parcel_number": "P-1"}))
    
    # 3. Update Geometry
    new_geom = {"type": "Polygon", "coordinates": [[[0,0],[2,0],[2,2],[0,2],[0,0]]]}
    await client.fetch(f"{base_url}/api/field/update_geometry/{fid}", method='PUT', body=json.dumps({"geometry": new_geom}))

    # Проверяем результат
    res = await client.fetch(f"{base_url}/api/field/{fid}")
    data = json.loads(res.body)
    assert data["name"] == "NewName"
    assert data["land_status"] == "Owned"
    assert data["parcel_number"] == "P-1"
    assert data["geometry"]["coordinates"][0][1] == [2, 0]

async def test_api_not_found_handling(http_server_client):
    client, base_url = http_server_client
    # Запрос несуществующего поля
    with pytest.raises(HTTPError) as e:
        await client.fetch(f"{base_url}/api/field/9999")
    assert e.value.code == 404

    # Удаление несуществующего владельца
    with pytest.raises(HTTPError) as e:
        await client.fetch(f"{base_url}/api/owner/delete/9999", method='DELETE')
    assert e.value.code == 404

async def test_kmz_export(http_server_client):
    client, base_url = http_server_client
    # 1. Создаем поле
    p = {"name": "Test Field", "geometry": {"type": "Polygon", "coordinates": [[[18.7,48.2], [18.8,48.2], [18.8,48.3], [18.7,48.3], [18.7,48.2]]]}}
    res_f = await client.fetch(f"{base_url}/api/field/add", method='POST', body=json.dumps(p))
    fid = json.loads(res_f.body)["id"]
    
    # 2. Пробуем скачать KMZ с параметрами
    url = f"{base_url}/api/field/export/kmz/{fid}?height=110&overlap_h=85&overlap_w=75"
    res = await client.fetch(url)
    
    assert res.code == 200
    assert res.headers["Content-Type"] == "application/vnd.google-earth.kmz"
    assert "attachment" in res.headers["Content-Disposition"]
    assert "Test_Field_110m.kmz" in res.headers["Content-Disposition"]    # Проверяем, что это ZIP (первые байты PK)
    assert res.body.startswith(b'PK')

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
