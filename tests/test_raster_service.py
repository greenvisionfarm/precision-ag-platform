import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
import os
import tempfile
from src.services.raster_service import process_ndvi_zones

@pytest.fixture
def mock_ndvi_tif():
    """Создает временный GeoTIFF файл 100x100 с тремя четкими зонами NDVI."""
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        path = tmp.name
    
    # Создаем данные: 3 зоны (0.2, 0.5, 0.8)
    data = np.zeros((100, 100), dtype=np.float32)
    data[:33, :] = 0.2  # Зона 1
    data[33:66, :] = 0.5 # Зона 2
    data[66:, :] = 0.8  # Зона 3
    
    # Добавим немного шума
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
    if os.path.exists(path):
        os.remove(path)

def test_process_ndvi_zones_logic(mock_ndvi_tif):
    # Поле: внутри [18.7, 18.8] и [48.1, 48.2]
    field_wkt = "POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))"
    
    zones = process_ndvi_zones(mock_ndvi_tif, field_wkt, num_zones=3)
    
    assert len(zones) == 3
    # Проверяем, что зоны отсортированы по NDVI (от низкого к высокому)
    assert zones[0]['avg_ndvi'] < zones[1]['avg_ndvi'] < zones[2]['avg_ndvi']
    
    # Проверяем наличие обязательных полей
    for zone in zones:
        assert 'geometry_wkt' in zone
        assert 'color' in zone
        assert zone['avg_ndvi'] > 0
