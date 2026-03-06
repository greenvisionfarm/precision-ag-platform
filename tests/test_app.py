import pytest
import json
from unittest.mock import patch
from app import make_app
from db import initialize_db, database, Field, get_database

# Фикстура для создания тестового приложения Tornado
@pytest.fixture
def app():
    return make_app()

# Фикстура для изоляции базы данных в тестах
@pytest.fixture(autouse=True)
def test_db():
    # Используем in-memory SQLite для тестов
    test_db_instance = get_database(None) # None означает in-memory
    test_db_instance.connect()
    test_db_instance.create_tables([Field])

    # Подменяем глобальный объект базы данных в db.py и app.py
    # Это важно, чтобы приложение использовало тестовую БД
    with patch('db.database', test_db_instance):
        with patch('app.database', test_db_instance):
            yield test_db_instance
    
    test_db_instance.drop_tables([Field])
    test_db_instance.close()


@pytest.mark.gen_test
async def test_main_page(http_client, base_url):
    """Тест главной страницы."""
    response = await http_client.fetch(base_url)
    assert response.code == 200
    assert "Карта Полей" in response.body.decode('utf-8')

@pytest.mark.gen_test
async def test_fields_api_empty(http_client, base_url, test_db):
    """Тест API полей, когда база данных пуста."""
    response = await http_client.fetch(f"{base_url}/api/fields")
    assert response.code == 200
    data = json.loads(response.body)
    assert data == {"type": "FeatureCollection", "features": []}

@pytest.mark.gen_test
async def test_fields_api_with_data(http_client, base_url, test_db):
    """Тест API полей, когда в базе данных есть данные."""
    # Добавляем тестовые данные в БД
    with test_db.atomic():
        Field.create(
            name="Test Field 1",
            geometry_wkt="POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))",
            properties_json=json.dumps({"area": 100, "type": "farm"})
        )
        Field.create(
            name="Test Field 2",
            geometry_wkt="POLYGON ((50 10, 60 40, 40 40, 30 20, 50 10))",
            properties_json=json.dumps({"area": 150, "owner": "John Doe"})
        )

    response = await http_client.fetch(f"{base_url}/api/fields")
    assert response.code == 200
    data = json.loads(response.body)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 2

    # Проверяем одно из полей
    feature1 = data["features"][0]
    assert feature1["properties"]["name"] == "Test Field 1"
    assert feature1["properties"]["area"] == 100
    assert feature1["geometry"]["type"] == "Polygon"

# TODO: Добавить тесты для UploadHandler. Это потребует создания фиктивного ZIP-файла
# с компонентами Shapefile, что является более сложной задачей.
# @pytest.mark.gen_test
# async def test_upload_handler_success(http_client, base_url, test_db):
#     """Тест успешной загрузки Shapefile."""
#     # Создать фиктивный ZIP-файл
#     # Отправить POST-запрос на /upload
#     # Проверить, что данные сохранены в БД
#     pass

# @pytest.mark.gen_test
# async def test_upload_handler_invalid_zip(http_client, base_url):
#     """Тест загрузки невалидного ZIP-файла."""
#     pass
