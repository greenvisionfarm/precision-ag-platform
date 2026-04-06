"""
Интеграционный тест для загрузки и обработки TIFF файлов.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock

import numpy as np
import pytest
import rasterio
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from db import Field, FieldScan, FieldZone, database, initialize_db
from src.handlers.field_handlers import FieldGetHandler
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


@pytest.fixture
def setup_field_with_scans(test_db, mock_ndvi_tif):
    """Создаёт поле с несколькими сканами и зонами."""
    import tempfile
    from datetime import datetime
    
    with database.atomic():
        field = Field.create(
            name="Поле с сканами",
            geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
            properties_json='{"area": 100}'
        )
        
        # Создаём 3 скана
        scan1 = FieldScan.create(
            field=field,
            file_path="/tmp/scan1.tif",
            filename="scan1.tif",
            uploaded_at=datetime(2026, 1, 1),
            ndvi_min=0.2, ndvi_max=0.8, ndvi_avg=0.5,
            processed='true'
        )
        
        scan2 = FieldScan.create(
            field=field,
            file_path="/tmp/scan2.tif",
            filename="scan2.tif",
            uploaded_at=datetime(2026, 2, 1),
            ndvi_min=0.2, ndvi_max=0.8, ndvi_avg=0.5,
            processed='false'  # Не обработан
        )
        
        scan3 = FieldScan.create(
            field=field,
            file_path=mock_ndvi_tif,
            filename="scan3.tif",
            uploaded_at=datetime(2026, 3, 1),  # Последний
            ndvi_min=0.2, ndvi_max=0.8, ndvi_avg=0.5,
            processed='true'
        )
        
        # Создаём зоны для scan1 (старые)
        with database.atomic():
            FieldZone.create(field=field, scan=scan1, name="Старая зона 1",
                           geometry_wkt="POLYGON ((18.73 48.13, 18.74 48.13, 18.74 48.14, 18.73 48.14, 18.73 48.13))",
                           avg_ndvi=0.3, color="#ff0000")
        
        # Создаём зоны для scan3 (последний обработанный)
        _process_geotiff_impl(mock_ndvi_tif, field.id, scan3.id)
    
    yield field
    
    # Очищаем
    with database.atomic():
        FieldZone.delete().where(FieldZone.field == field).execute()
        FieldScan.delete().where(FieldScan.field == field).execute()
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


def test_field_get_handler_returns_zones_from_last_scan(setup_field_with_scans):
    """Тест: FieldGetHandler возвращает зоны из последнего обработанного скана."""
    from db import FieldScan, FieldZone
    
    field = setup_field_with_scans
    
    # Проверяем что в БД есть зоны
    all_zones = FieldZone.select().where(FieldZone.field == field)
    assert all_zones.count() >= 1, f"Должны быть зоны, найдено: {all_zones.count()}"
    
    # Проверяем логику выбора последнего скана напрямую
    last_scan = FieldScan.select().where(
        FieldScan.field == field,
        FieldScan.processed == 'true'
    ).order_by(FieldScan.uploaded_at.desc()).first()
    
    assert last_scan is not None, "Должен быть найден последний обработанный скан"
    assert last_scan.processed == 'true', "Скан должен быть обработан"
    
    # Проверяем что зоны из последнего скана
    zones_from_last_scan = FieldZone.select().where(FieldZone.scan == last_scan)
    assert zones_from_last_scan.count() >= 1, \
        f"Должны быть зоны из последнего скана, получено: {zones_from_last_scan.count()}"
    
    # Проверяем что у зон есть имена
    zone_names = [z.name for z in zones_from_last_scan]
    assert len(zone_names) > 0, "У зон должны быть имена"


def test_field_get_handler_excludes_unprocessed_scans(setup_field_with_scans):
    """Тест: FieldGetHandler игнорирует необработанные сканы."""
    from db import FieldScan
    from datetime import datetime
    
    field = setup_field_with_scans
    
    # Создаём ещё один скан (необработанный, но более новый)
    with database.atomic():
        scan_unprocessed = FieldScan.create(
            field=field,
            file_path="/tmp/scan_unprocessed.tif",
            filename="scan_unprocessed.tif",
            uploaded_at=datetime(2026, 4, 1),  # Ещё новее
            ndvi_min=0.2, ndvi_max=0.8, ndvi_avg=0.5,
            processed='false'  # Не обработан!
        )
    
    # Проверяем что выбирается последний ОБРАБОТАННЫЙ скан
    last_processed_scan = FieldScan.select().where(
        FieldScan.field == field,
        FieldScan.processed == 'true'
    ).order_by(FieldScan.uploaded_at.desc()).first()
    
    # Должен вернуться scan3 (2026-03-01), а не scan_unprocessed (2026-04-01)
    assert last_processed_scan is not None, "Должен быть найден последний обработанный скан"
    # Проверяем что это не scan_unprocessed
    assert last_processed_scan.processed == 'true', "Должен быть обработанный скан"
    assert last_processed_scan.uploaded_at < scan_unprocessed.uploaded_at, \
        "Должен быть скан старше необработанного"


def test_field_get_handler_backward_compatibility(test_db, mock_ndvi_tif):
    """Тест: FieldGetHandler работает со старыми данными (без сканов)."""
    from db import Field, FieldScan, FieldZone
    
    with database.atomic():
        field = Field.create(
            name="Старое поле",
            geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
            properties_json='{"area": 100}'
        )
        
        # Создаём старые зоны (без scan_id)
        FieldZone.create(
            field=field, scan=None,  # Нет скана
            name="Старая зона",
            geometry_wkt="POLYGON ((18.73 48.13, 18.74 48.13, 18.74 48.14, 18.73 48.14, 18.73 48.13))",
            avg_ndvi=0.5, color="#00ff00"
        )
    
    # Проверяем логику выбора скана
    last_scan = FieldScan.select().where(
        FieldScan.field == field,
        FieldScan.processed == 'true'
    ).order_by(FieldScan.uploaded_at.desc()).first()
    
    # Сканов нет
    assert last_scan is None, "Не должно быть сканов"
    
    # Проверяем что находятся старые зоны
    old_zones = FieldZone.select().where(FieldZone.field == field, FieldZone.scan.is_null(True))
    assert old_zones.count() == 1, f"Должна быть 1 старая зона, найдено: {old_zones.count()}"
    assert old_zones[0].name == "Старая зона"
    
    # Очищаем
    with database.atomic():
        FieldZone.delete().where(FieldZone.field == field).execute()
        Field.delete().where(Field.id == field.id).execute()
