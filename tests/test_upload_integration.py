"""
Интеграционный тест для загрузки и обработки TIFF файлов.
"""
import os
import tempfile

import numpy as np
import pytest
import rasterio

from db import Field, FieldZone, database
from src.services.raster_service import process_ndvi_zones
from src.tasks import _process_geotiff_impl


@pytest.fixture
def mock_ndvi_tif():
    """Создает временный GeoTIFF файл 100x100 с тремя четкими зонами NDVI."""
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        path = tmp.name

    # Создаем данные: 3 зоны (0.2, 0.5, 0.8)
    data = np.zeros((100, 100), dtype=np.float32)
    data[:33, :] = 0.2  # Зона 1 (низкая)
    data[33:66, :] = 0.5  # Зона 2 (средняя)
    data[66:, :] = 0.8  # Зона 3 (высокая)

    # Добавляем немного шума
    data += np.random.normal(0, 0.05, (100, 100))

    # Координаты: запад, юг, восток, север
    transform = rasterio.transform.from_bounds(18.7, 48.1, 18.8, 48.2, 100, 100)

    with rasterio.open(
        path, 'w', driver='GTiff',
        height=100, width=100,
        count=1, dtype='float32',
        crs='EPSG:4326',
        transform=transform
    ) as dst:
        dst.write(data, 1)

    yield path
    # Не удаляем файл сразу — он может понадобиться для отладки
    # if os.path.exists(path):
    #     os.remove(path)


@pytest.fixture
def setup_field(test_db):
    """Создает тестовое поле в БД."""
    with database.atomic():
        field = Field.create(
            name="Тестовое поле",
            geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
            properties_json='{"area": 100}'
        )
    yield field
    # Очищаем после теста
    with database.atomic():
        FieldZone.delete().where(FieldZone.field == field).execute()
        Field.delete().where(Field.id == field.id).execute()


def test_process_ndvi_zones_returns_valid_data(mock_ndvi_tif):
    """Тест: process_ndvi_zones возвращает правильную структуру данных."""
    field_wkt = "POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))"

    zones = process_ndvi_zones(mock_ndvi_tif, field_wkt, num_zones=3)

    assert len(zones) == 3
    
    # Проверяем структуру каждой зоны
    for zone in zones:
        assert 'name' in zone, "Зона должна иметь поле 'name'"
        assert 'geometry_wkt' in zone, "Зона должна иметь поле 'geometry_wkt'"
        assert 'avg_ndvi' in zone, "Зона должна иметь поле 'avg_ndvi'"
        assert 'color' in zone, "Зона должна иметь поле 'color'"
        
        # Проверяем типы данных
        assert isinstance(zone['name'], str)
        assert isinstance(zone['geometry_wkt'], str)
        assert isinstance(zone['avg_ndvi'], float)
        assert isinstance(zone['color'], str)
        
        # Проверяем диапазон NDVI
        assert -1.0 <= zone['avg_ndvi'] <= 1.0, f"NDVI {zone['avg_ndvi']} вне диапазона"

    # Проверяем сортировку (от низкой к высокой)
    ndvi_values = [z['avg_ndvi'] for z in zones]
    assert ndvi_values == sorted(ndvi_values), "Зоны должны быть отсортированы по NDVI"


def test_process_geotiff_task_creates_zones(mock_ndvi_tif, setup_field):
    """Тест: process_geotiff_task создаёт зоны в БД."""
    result = _process_geotiff_impl(mock_ndvi_tif, setup_field.id)
    
    # Проверяем результат
    assert result is True, "Задача должна завершиться успешно"
    
    # Проверяем что зоны созданы в БД
    zones = list(FieldZone.select().where(FieldZone.field == setup_field))
    assert len(zones) == 3, f"Должно быть создано 3 зоны, создано: {len(zones)}"
    
    # Проверяем данные каждой зоны
    for zone in zones:
        assert zone.name in ["Низкая", "Средняя", "Высокая"], f"Неверное имя зоны: {zone.name}"
        assert zone.geometry_wkt is not None, "geometry_wkt не должен быть None"
        assert zone.avg_ndvi is not None, "avg_ndvi не должен быть None"
        assert -1.0 <= zone.avg_ndvi <= 1.0, f"NDVI {zone.avg_ndvi} вне диапазона"
        assert zone.color is not None, "color не должен быть None"


def test_process_geotiff_task_saves_valid_ndvi_values(mock_ndvi_tif, setup_field):
    """Тест: NDVI значения сохраняются корректно."""
    result = _process_geotiff_impl(mock_ndvi_tif, setup_field.id)
    
    assert result is True
    
    zones = list(FieldZone.select().where(FieldZone.field == setup_field).order_by(FieldZone.avg_ndvi))
    
    # Проверяем что значения NDVI соответствуют ожидаемым (с учётом шума)
    assert 0.15 <= zones[0].avg_ndvi <= 0.25, f"Низкая зона: {zones[0].avg_ndvi}"
    assert 0.45 <= zones[1].avg_ndvi <= 0.55, f"Средняя зона: {zones[1].avg_ndvi}"
    assert 0.75 <= zones[2].avg_ndvi <= 0.85, f"Высокая зона: {zones[2].avg_ndvi}"
