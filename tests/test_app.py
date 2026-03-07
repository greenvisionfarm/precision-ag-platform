import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import geopandas as gpd
from shapely.geometry import Polygon
import io
import zipfile
import socket
import tempfile
from unittest.mock import patch
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError

from app import make_app
from db import Field, Owner, get_database

def find_unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@pytest.fixture
def app():
    return make_app()

@pytest.fixture(scope='function')
def test_db():
    db_instance = get_database(':memory:')
    with patch('db.database', db_instance):
        with patch('app.database', db_instance):
            db_instance.connect()
            db_instance.create_tables([Owner, Field])
            yield db_instance
            db_instance.drop_tables([Owner, Field])
            db_instance.close()

@pytest.fixture
def sample_field_data():
    return {
        "name": "Test Field",
        "geometry_wkt": "POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))",
        "properties_json": json.dumps({"area_sq_m": 10000})
    }

@pytest.fixture
async def http_server_client(app, test_db):
    port = find_unused_port()
    server = app.listen(port)
    client = AsyncHTTPClient()
    yield client, f"http://localhost:{port}"
    client.close()
    server.stop()

# --- ТЕСТЫ ---

async def test_spa_entry_point(http_server_client):
    """Проверка, что главная страница SPA доступна."""
    client, base_url = http_server_client
    response = await client.fetch(f"{base_url}/")
    assert response.code == 200
    assert "Field Mapper" in response.body.decode('utf-8')

async def test_api_fields_empty(http_server_client):
    """Проверка API полей на пустой БД."""
    client, base_url = http_server_client
    response = await client.fetch(f"{base_url}/api/fields")
    assert response.code == 200
    assert json.loads(response.body)["features"] == []

async def test_add_owner(http_server_client):
    client, base_url = http_server_client
    body = json.dumps({"name": "Ivan"})
    request = HTTPRequest(f"{base_url}/api/owner/add", method='POST', body=body)
    response = await client.fetch(request)
    assert response.code == 200
    assert Owner.get().name == "Ivan"

async def test_update_field_details(http_server_client, sample_field_data):
    """Тест обновления статуса и кадастрового номера."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    
    payload = json.dumps({
        "land_status": "Аренда",
        "parcel_number": "123/456"
    })
    request = HTTPRequest(f"{base_url}/api/field/update_details/{field.id}", method='PUT', body=payload)
    response = await client.fetch(request)
    assert response.code == 200
    
    updated = Field.get(Field.id == field.id)
    assert updated.land_status == "Аренда"
    assert updated.parcel_number == "123/456"

async def test_delete_field(http_server_client, sample_field_data):
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    request = HTTPRequest(f"{base_url}/api/field/delete/{field.id}", method='DELETE')
    await client.fetch(request)
    assert Field.select().count() == 0
