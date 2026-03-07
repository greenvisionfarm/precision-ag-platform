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
from tornado.testing import AsyncHTTPTestCase # get_unused_port удален

from app import make_app # Добавляем импорт make_app
from db import Field, get_database # Добавляем импорт Field и get_database

# Указываем pytest, что все тесты в этом файле асинхронные (режим auto)
# pytest_plugins = "pytest_asyncio" # Теперь это настраивается в conftest.py

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
            db_instance.create_tables([Field])
            yield db_instance
            db_instance.drop_tables([Field]) # Добавляем очистку таблиц
            db_instance.close()

@pytest.fixture
def sample_field_data():
    """Фикстура, предоставляющая тестовые данные для одного поля."""
    return {
        "name": "Test Field 1",
        "geometry_wkt": "POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))",
        "properties_json": json.dumps({"area": 100, "type": "farm"})
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
    port = find_unused_port() # Используем нашу новую функцию
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

async def test_api_endpoints_when_db_is_empty(http_server_client):
    """Тест API эндпоинтов, когда база данных пуста."""
    client, base_url = http_server_client
    
    response_fields = await client.fetch(f"{base_url}/api/fields")
    assert response_fields.code == 200
    data_fields = json.loads(response_fields.body)
    print(f"Actual GeoJSON response: {data_fields}") # Для отладки
    assert data_fields == {"type": "FeatureCollection", "features": []}

    response_data = await client.fetch(f"{base_url}/api/fields_data")
    assert response_data.code == 200
    assert json.loads(response_data.body) == {"data": []}

async def test_api_endpoints_with_data(http_server_client, sample_field_data):
    """Тест API эндпоинтов, когда в базе данных есть данные."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)

    response = await client.fetch(f"{base_url}/api/fields")
    assert response.code == 200
    data = json.loads(response.body)
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["name"] == sample_field_data["name"]

async def test_delete_field(http_server_client, sample_field_data):
    """Тест успешного удаления поля."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)
    assert Field.select().count() == 1

    request = HTTPRequest(f"{base_url}/api/field/delete/{field.id}", method='DELETE')
    response = await client.fetch(request)
    
    response_json = json.loads(response.body)
    assert response_json["message"] == f"Поле с ID {field.id} успешно удалено."
    
    # Проверяем, что поле действительно удалено из БД
    assert Field.select().count() == 0

async def test_delete_nonexistent_field(http_server_client):
    """Тест удаления несуществующего поля."""
    client, base_url = http_server_client
    request = HTTPRequest(f"{base_url}/api/field/delete/999", method='DELETE')
    
    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 404

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
    response_json = json.loads(response.body)
    assert "успешно загружены" in response_json["message"]
    assert Field.select().count() == 2

async def test_upload_invalid_zip(http_server_client):
    """Тест загрузки ZIP-архива без .shp файла."""
    client, base_url = http_server_client
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("test.txt", "this is not a shapefile")
    zip_bytes = zip_buffer.read()

    boundary = '---boundary---'
    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
    body = (
        f'--{boundary}\r\n'
        'Content-Disposition: form-data; name="shapefile_zip"; filename="invalid.zip"\r\n'
        'Content-Type: application/zip\r\n\r\n'
    ).encode('utf-8') + zip_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')

    request = HTTPRequest(f"{base_url}/upload", method='POST', headers=headers, body=body)

    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 500
    response_data = json.loads(e.value.response.body)
    assert "File is not a zip file" in response_data["error"]

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
    response_json = json.loads(response.body)
    assert response_json["message"] == f"Поле с ID {field.id} успешно переименовано."

    # Проверяем, что имя поля действительно изменилось в БД
    updated_field = Field.get(Field.id == field.id)
    assert updated_field.name == new_name

async def test_rename_field_not_found(http_server_client):
    """Тест переименования несуществующего поля."""
    client, base_url = http_server_client
    new_name = "NonExistent Field"
    request_body = json.dumps({"new_name": new_name})
    request = HTTPRequest(
        f"{base_url}/api/field/rename/999",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )

    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 404
    response_data = json.loads(e.value.response.body)
    assert "не найдено" in response_data["error"]

async def test_rename_field_invalid_json(http_server_client, sample_field_data):
    """Тест переименования поля с неверным JSON."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)

    request = HTTPRequest(
        f"{base_url}/api/field/rename/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body="this is not json"
    )

    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 400
    response_data = json.loads(e.value.response.body)
    assert "Неверный формат JSON" in response_data["error"]

async def test_rename_field_missing_name(http_server_client, sample_field_data):
    """Тест переименования поля без указания нового имени."""
    client, base_url = http_server_client
    field = Field.create(**sample_field_data)

    request_body = json.dumps({"some_other_key": "value"}) # Отсутствует 'new_name'
    request = HTTPRequest(
        f"{base_url}/api/field/rename/{field.id}",
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=request_body
    )

    with pytest.raises(HTTPError) as e:
        await client.fetch(request)
    assert e.value.code == 400
    response_data = json.loads(e.value.response.body)
    assert "Новое имя поля не может быть пустым" in response_data["error"]
