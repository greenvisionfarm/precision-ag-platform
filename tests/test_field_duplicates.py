import json
import pytest
from shapely.geometry import Polygon, mapping

@pytest.mark.asyncio
async def test_field_duplicate_detection(http_server_client, auth_headers):
    """Тест на обнаружение дубликатов полей по геометрии."""
    client, base = http_server_client
    
    # Геометрия поля
    geom = Polygon([(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0), (0, 0)])
    field_data = {
        "name": "Оригинальное поле",
        "geometry": mapping(geom)
    }
    
    # 1. Создаем первое поле
    response = await client.fetch(
        f"{base}/api/field/add", 
        method="POST", 
        body=json.dumps(field_data), 
        headers=auth_headers
    )
    assert response.code == 200
    field_id = json.loads(response.body)["id"]
    
    # 2. Пытаемся создать такое же поле (100% совпадение)
    response2 = await client.fetch(
        f"{base}/api/field/add", 
        method="POST", 
        body=json.dumps(field_data), 
        headers=auth_headers,
        raise_error=False
    )
    assert response2.code == 400
    assert "уже существует" in json.loads(response2.body)["error"]
    
    # 3. Пытаемся создать очень похожее поле (95% совпадение)
    geom_similar = Polygon([(0, 0), (0, 0.01001), (0.01, 0.01), (0.01, 0), (0, 0)])
    field_data_similar = {
        "name": "Похожее поле",
        "geometry": mapping(geom_similar)
    }
    response3 = await client.fetch(
        f"{base}/api/field/add", 
        method="POST", 
        body=json.dumps(field_data_similar), 
        headers=auth_headers,
        raise_error=False
    )
    assert response3.code == 400
    assert "уже существует" in json.loads(response3.body)["error"]
    
    # 4. Создаем поле в другом месте (нет пересечения)
    geom_new = Polygon([(1, 1), (1, 1.01), (1.01, 1.01), (1.01, 1), (1, 1)])
    field_data_new = {
        "name": "Новое поле",
        "geometry": mapping(geom_new)
    }
    response4 = await client.fetch(
        f"{base}/api/field/add", 
        method="POST", 
        body=json.dumps(field_data_new), 
        headers=auth_headers
    )
    assert response4.code == 200
