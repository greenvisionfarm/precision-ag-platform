import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
import os

# Импорты из твоего проекта
from src.services.core_math import calculate_index_from_arrays, calculate_vra_redistribution
from src.services.raster_service import process_ndvi_zones

# Фикстура для создания временного GeoTIFF в памяти (точнее, временного файла)
@pytest.fixture
def mock_geotiff(tmp_path):
    path = tmp_path / "test_field.tif"
    # Создаем градиентное поле (имитируем реальную вариативность NDVI)
    # 100x100 пикселей, значения от 0.1 до 0.9
    rows, cols = 100, 100
    data = np.linspace(0.1, 0.9, rows * cols).reshape(rows, cols).astype(np.float32)
    
    # Добавим немного "шума" для реалистичности кластеризации
    data += np.random.normal(0, 0.05, (rows, cols))
    data = np.clip(data, 0.1, 0.9).astype(np.float32)
    
    with rasterio.open(
        path, 'w', driver='GTiff', height=rows, width=cols, count=1,
        dtype=np.float32, crs='EPSG:4326',
        transform=from_origin(30.0, 50.0, 0.0001, 0.0001)
    ) as dst:
        dst.write(data, 1)
    return str(path)

# 1. Тест математики индексов
def test_ndvi_math_sanity():
    # NIR > Red -> Положительный NDVI
    # Используем значения > 100, так как в core_math.py стоит фильтр (val > 100)
    nir = np.array([250, 450, 650], dtype=np.uint16)
    red = np.array([150, 150, 150], dtype=np.uint16)
    res = calculate_index_from_arrays(nir, red)
    # (250-150)/(250+150) = 100/400 = 0.25
    # (450-150)/(450+150) = 300/600 = 0.5
    # (650-150)/(650+150) = 500/800 = 0.625
    # Mean = (0.25 + 0.5 + 0.625) / 3 = 0.458
    assert 0.4 < res < 0.5
    assert -1.0 <= res <= 1.0
    
    # Red > NIR -> Отрицательный NDVI
    nir_low = np.array([150, 150], dtype=np.uint16)
    red_high = np.array([200, 300], dtype=np.uint16)
    res_neg = calculate_index_from_arrays(nir_low, red_high)
    assert res_neg < 0

# 2. Тест зонирования (Diversity)
def test_zoning_diversity(mock_geotiff):
    # Координаты квадрата, покрывающего наш растр
    field_wkt = "POLYGON ((30.0 50.0, 30.01 50.0, 30.01 49.99, 30.0 49.99, 30.0 50.0))"
    zones = process_ndvi_zones(mock_geotiff, field_wkt, num_zones=3)
    
    # Проверяем, что создано ровно 3 зоны (как запрашивали)
    assert len(zones) == 3
    
    # Проверяем, что средние NDVI в зонах распределены логично (Низкая < Средняя < Высокая)
    # В process_ndvi_zones имена фиксированы: "Низкая", "Средняя", "Высокая"
    z_map = {z['name']: z['avg_ndvi'] for z in zones}
    assert z_map['Низкая'] < z_map['Средняя'] < z_map['Высокая']

# 3 & 4. Тест VRA (Баланс масс и безопасность)
def test_vra_logic():
    # Исходные зоны: по 10 га каждая
    zones = [
        {"name": "Низкая", "area_raw": 10.0},
        {"name": "Средняя", "area_raw": 10.0},
        {"name": "Высокая", "area_raw": 10.0}
    ]
    total_target = 3000.0 # Целевой объем: 3 тонны
    
    results = calculate_vra_redistribution(zones, total_target)
    
    # Считаем фактическую массу: SUM(area * rate)
    actual_total = sum(z['rate_kg_ha'] * z['area_raw'] for z in results)
    
    # Проверка 3: Сохранение массы (погрешность < 1%)
    assert abs(actual_total - total_target) < (total_target * 0.01)
    
    # Проверка 4: Физические границы и логика
    for z in results:
        assert z['rate_kg_ha'] >= 0, "Норма не может быть < 0"
        assert z['rate_kg_ha'] <= 1000, "Превышен MAX_SAFE_RATE"
        
    low_rate = next(z['rate_kg_ha'] for z in results if z['name'] == "Низкая")
    high_rate = next(z['rate_kg_ha'] for z in results if z['name'] == "Высокая")
    # По стратегии "Низкая зона = больше удобрений" (коэффициент 1.2 vs 0.8)
    assert low_rate > high_rate

# 5. Тест на устойчивость к плохим данным (Robustness)
def test_pipeline_robustness_with_nans():
    # Массивы с нулями (имитация NoData или черных краев)
    nir = np.array([0, 0, 0], dtype=np.uint16)
    red = np.array([100, 100, 100], dtype=np.uint16)
    
    # Не должно падать, должно вернуть 0.0 (безопасное значение)
    res = calculate_index_from_arrays(nir, red)
    assert res == 0.0
