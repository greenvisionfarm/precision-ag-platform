import sys
import os
# Добавляем корень проекта в sys.path, чтобы импорты работали корректно
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

# --- Вспомогательная функция для получения свободного порта ---
def find_unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

# --- Фикстуры для тестов ---

@pytest.fixture
def app():
    """Фикстура для создания экземпляра приложения Tornado."""
    return make_app()

@pytest.fixture(scope='function')
def test_db():
    """
    Фикстура для создания и очистки изолированной in-memory SQLite базы данных для каждого теста.
    """
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
    """Фикстура, предоставляющая тестовые данные для одного поля."""
    return {
        "name": "Test Field 1",
        "geometry_wkt": "POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))",
        "properties_json": json.dumps({"area_sq_m": 10000, "type": "farm"})
    }

@pytest.fixture
def create_shapefile_zip() -> bytes:
    """
    Фикстура для создания фиктивного shapefile в ZIP-архиве в памяти.
    """
    p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    p2 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])
    gdf = gpd.GeoDataFrame({'id': [1, 2]}, geometry=[p1, p2], crs="EPSG:4326")
    gdf['name'] = ['Field A', 'Field B']

    with tempfile.TemporaryDirectory() as tmpdir:
        shapefile_path = os.path.join(tmpdir, "test_shapefile.shp")
        gdf.to_file(shapefile_path, driver='ESRI Shapefile')
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)
        zip_buffer.seek(0)
        return zip_buffer.read()

@pytest.fixture
async def http_server_client(app, test_db):
    """
    Запускает Tornado сервер на свободном порту и предоставляет http-клиент.
    """
    port = find_unused_port()
    server = app.listen(port)
    client = AsyncHTTPClient()
    
    yield client, f"http://localhost:{port}"
    
    client.close()
    server.stop()

# --- Тесты ---

async def test_main_page(http_server_client):
    """Тест доступности главной страницы."""
    client, base_url = http_server_client
    response = await client.fetch(f"{base_url}/")
    assert response.code == 200
    assert "Карта Полей" in response.body.decode('utf-8')

async def test_fields_list_page(http_server_client):
    """Тест доступности страницы со списком полей."""
    client, base_url = http_server_client
    response = await client.fetch(f"{base_url}/fields_list")
    assert response.code == 200
    assert "Список полей" in response.body.decode('utf-8')

async def test_owners_page(http_server_client):
    """Тест доступности страницы владельцев."""
    client, base_url = http_server_client
    response = await client.fetch(f"{base_url}/owners")
    assert response.code == 200
    assert "Управление Владельцами" in response.body.decode('utf-8')

async def test_api_endpoints_when_db_is_empty(http_server_client):
    """Тест API эндпоинтов, когда база данных пуста."""
    client, base_url = http_server_client
    
    response_fields = await client.fetch(f"{base_url}/api/fields")
    assert response_fields.code == 200
    data_fields = json.loads(response_fields.body)
    assert data_fields == {"type": "FeatureCollection", "features": []}

    response_data = await client.fetch(f"{base_url}/api/fields_data")
    assert response_data.code == 200
    assert json.loads(response_data.body) == {"data": []}

    response_owners = await client.fetch(f"{base_url}/api/owners")
    assert response_owners.code == 200
    assert json.loads(response_owners.body) == {"data": []}

async def test_add_owner_success(http_server_client):
    """Тест успешного добавления владельца."""
    client, base_url = http_server_client
    owner_name = "Иван Иванов"
    request_body = json.dumps({"name": owner_name})
    
    request = HTTPRequest(
        f"{base_url}/api/owner/add",
        method='POST',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    response = await client.fetch(request)
    assert response.code == 200
    assert "успешно добавлен" in json.loads(response.body)["message"]
    assert Owner.select().count() == 1
    assert Owner.get().name == owner_name

async def test_add_owner_duplicate(http_server_client):
    """Тест ошибки при добавлении дубликата владельца."""
    client, base_url = http_server_client
    Owner.create(name="Duplicate")
    
    request_body = json.dumps({"name": "Duplicate"})
    request = HTTPRequest(
        f"{base_url}/api/owner/add",
        method='POST',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    
    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 400
    assert "уже существует" in json.loads(e.value.response.body)["error"]

async def test_fields_data_with_owner(http_server_client, sample_field_data):
    """Тест отображения имени владельца в списке полей."""
    client, base_url = http_server_client
    owner = Owner.create(name="John Doe")
    Field.create(**sample_field_data, owner=owner)

    response = await client.fetch(f"{base_url}/api/fields_data")
    assert response.code == 200
    data = json.loads(response.body)["data"]
    assert len(data) == 1
    assert data[0]["owner"] == "John Doe"
    assert data[0]["area"] == "1.00 га" # 10000 / 10000

async def test_delete_field(http_server_client, sample_field_data):
    """Тест успешного удаления поля."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    assert Field.select().count() == 1

    request = HTTPRequest(f"{base_url}/api/field/delete/{field.id}", method='DELETE')
    response = await client.fetch(request)
    
    response_json = json.loads(response.body)
    assert "успешно удалено" in response_json["message"]
    assert Field.select().count() == 0

async def test_upload_success(http_server_client, create_shapefile_zip):
    """Тест успешной загрузки корректного ZIP-архива с shapefile."""
    client, base_url = http_server_client
    zip_bytes = create_shapefile_zip
    
    boundary = '---boundary---'
    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
    body = (
        f'--{boundary}\r\n'
        'Content-Disposition: form-data; name="shapefile_zip"; filename="test.zip"\r\n'
        'Content-Type: application/zip\r\n\r\n'
    ).encode('utf-8') + zip_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')

    request = HTTPRequest(f"{base_url}/upload", method='POST', headers=headers, body=body)
    response = await client.fetch(request)

    assert response.code == 200
    assert Field.select().count() == 2

async def test_rename_field_success(http_server_client, sample_field_data):
    """Тест успешного переименования поля."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    
    new_name = "Renamed Field"
    request_body = json.dumps({"new_name": new_name})
    request = HTTPRequest(
        f"{base_url}/api/field/rename/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    response = await client.fetch(request)

    assert response.code == 200
    updated_field = Field.get(Field.id == field.id)
    assert updated_field.name == new_name

async def test_assign_owner_success(http_server_client, sample_field_data):
    """Тест успешного назначения владельца полю."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    owner = Owner.create(name="New Owner")
    
    request_body = json.dumps({"owner_id": owner.id})
    request = HTTPRequest(
        f"{base_url}/api/field/assign_owner/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    response = await client.fetch(request)
    assert response.code == 200
    
    updated_field = Field.get(Field.id == field.id)
    assert updated_field.owner.id == owner.id

async def test_unassign_owner(http_server_client, sample_field_data):
    """Тест сброса владельца поля (установка в None)."""
    client, base_url = http_server_client
    owner = Owner.create(name="Old Owner")
    field = Field.create(**sample_field_data, owner=owner)
    
    request_body = json.dumps({"owner_id": ""}) # Пустая строка или null
    request = HTTPRequest(
        f"{base_url}/api/field/assign_owner/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    response = await client.fetch(request)
    assert response.code == 200
    
    updated_field = Field.get(Field.id == field.id)
    assert updated_field.owner is None

async def test_assign_owner_invalid_id(http_server_client, sample_field_data):
    """Тест ошибки при назначении несуществующего владельца."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    
    request_body = json.dumps({"owner_id": 9999})
    request = HTTPRequest(
        f"{base_url}/api/field/assign_owner/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    
    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 400
    assert "Владелец не найден" in json.loads(e.value.response.body)["error"]

async def test_add_field_manually_success(http_server_client):
    """Тест успешного ручного добавления поля."""
    client, base_url = http_server_client
    
    # Геометрия 1x1 градус (примерно 111x111 км в метрах, но в EPSG:3857 будет больше)
    geometry = {
        "type": "Polygon",
        "coordinates": [[[30, 50], [31, 50], [31, 51], [30, 51], [30, 50]]]
    }
    field_name = "Manual Field"
    request_body = json.dumps({
        "geometry": geometry,
        "name": field_name
    })
    
    request = HTTPRequest(
        f"{base_url}/api/field/add",
        method='POST',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    response = await client.fetch(request)
    assert response.code == 200
    
    data = json.loads(response.body)
    assert "успешно добавлено" in data["message"]
    
    # Проверяем в БД
    field_id = data["id"]
    field = Field.get(Field.id == field_id)
    assert field.name == field_name
    
    properties = json.loads(field.properties_json)
    assert "area_sq_m" in properties
    assert properties["area_sq_m"] > 0
    assert properties["source"] == "manual_draw"

async def test_add_field_manually_missing_geometry(http_server_client):
    """Тест ошибки при отсутствии геометрии в запросе."""
    client, base_url = http_server_client
    
    request_body = json.dumps({"name": "No Geometry Field"})
    request = HTTPRequest(
        f"{base_url}/api/field/add",
        method='POST',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    
    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 400
    assert "Геометрия обязательна" in json.loads(e.value.response.body)["error"]

async def test_update_field_geometry_success(http_server_client, sample_field_data):
    """Тест успешного обновления геометрии поля и пересчета площади."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    
    # Новая геометрия (в два раза больше по размеру)
    new_geometry = {
        "type": "Polygon",
        "coordinates": [[[30, 50], [32, 50], [32, 52], [30, 52], [30, 50]]]
    }
    
    request_body = json.dumps({"geometry": new_geometry})
    request = HTTPRequest(
        f"{base_url}/api/field/update_geometry/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    response = await client.fetch(request)
    assert response.code == 200
    
    # Проверяем изменения в БД
    updated_field = Field.get(Field.id == field.id)
    properties = json.loads(updated_field.properties_json)
    
    # Площадь должна была измениться (старая была для POLGYON((30 10...)) из фикстуры)
    original_properties = json.loads(sample_field_data["properties_json"])
    assert properties["area_sq_m"] != original_properties["area_sq_m"]
    assert properties["area_sq_m"] > 0

async def test_update_field_geometry_not_found(http_server_client):
    """Тест ошибки 404 при попытке обновить геометрию несуществующего поля."""
    client, base_url = http_server_client
    
    geometry = {
        "type": "Polygon",
        "coordinates": [[[30, 50], [31, 50], [31, 51], [30, 51], [30, 50]]]
    }
    request_body = json.dumps({"geometry": geometry})
    request = HTTPRequest(
        f"{base_url}/api/field/update_geometry/9999",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )
    
    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 404
    assert "Поле не найдено" in json.loads(e.value.response.body)["error"]
