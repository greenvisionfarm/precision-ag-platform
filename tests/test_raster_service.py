"""
Тесты для raster_service - обработка NDVI и создание зон.
"""
import os
import pytest
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import box, mapping

from src.services.raster_service import process_ndvi_zones


@pytest.fixture
def sample_tiff_path(tmp_path):
    """Создаёт тестовый GeoTIFF с фиктивными NDVI данными."""
    tiff_path = tmp_path / "test_ndvi.tif"
    
    # Создаём простой растр 100x100 с градиентом NDVI
    width, height = 100, 100
    bounds = (18.72, 48.20, 18.74, 48.22)  # Координаты в Венгрии
    
    # Генерируем данные с тремя различными зонами NDVI
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    
    # Создаём три зоны с разным NDVI
    ndvi_data = np.zeros((height, width), dtype=np.float32)
    ndvi_data[yy < 0.33] = 0.3  # Низкая зона
    ndvi_data[(yy >= 0.33) & (yy < 0.66)] = 0.5  # Средняя зона
    ndvi_data[yy >= 0.66] = 0.8  # Высокая зона
    
    # Добавляем немного шума
    ndvi_data += np.random.normal(0, 0.05, ndvi_data.shape)
    ndvi_data = np.clip(ndvi_data, -1, 1)
    
    # Сохраняем как GeoTIFF
    transform = from_bounds(*bounds, width, height)
    with rasterio.open(
        tiff_path, 'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=ndvi_data.dtype,
        crs='EPSG:4326',
        transform=transform,
        nodata=-9999
    ) as dst:
        dst.write(ndvi_data, 1)
    
    return str(tiff_path)


@pytest.fixture
def sample_field_geometry():
    """Геометрия тестового поля."""
    # Полигон в тех же координатах что и тестовый растр
    return box(18.72, 48.20, 18.74, 48.22).wkt


class TestProcessNdviZones:
    """Тесты для функции process_ndvi_zones."""

    def test_basic_zoning(self, sample_tiff_path, sample_field_geometry):
        """Базовый тест: создание 3 зон из NDVI растра."""
        zones = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=3)
        
        assert len(zones) == 3, "Должно быть создано 3 зоны"
        
        # Проверяем структуру каждой зоны
        for zone in zones:
            assert "name" in zone
            assert "geometry_wkt" in zone
            assert "avg_ndvi" in zone
            assert "color" in zone
            
        # Проверяем что зоны имеют разные средние NDVI
        ndvi_values = [z["avg_ndvi"] for z in zones]
        assert len(set(ndvi_values)) == 3, "Зоны должны иметь разные средние NDVI"
        
        # Проверяем что NDVI в правильном диапазоне
        for zone in zones:
            assert -1.0 <= zone["avg_ndvi"] <= 1.0, f"NDVI {zone['avg_ndvi']} вне диапазона"

    def test_zone_names(self, sample_tiff_path, sample_field_geometry):
        """Тест имён зон: Низкая, Средняя, Высокая."""
        zones = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=3)
        
        expected_names = ["Низкая", "Средняя", "Высокая"]
        actual_names = [z["name"] for z in zones]
        
        assert actual_names == expected_names, f"Ожидались имена {expected_names}, получены {actual_names}"

    def test_zone_colors(self, sample_tiff_path, sample_field_geometry):
        """Тест цветов зон."""
        zones = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=3)
        
        expected_colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]
        actual_colors = [z["color"] for z in zones]
        
        assert actual_colors == expected_colors, f"Ожидались цвета {expected_colors}, получены {actual_colors}"

    def test_ndvi_ordering(self, sample_tiff_path, sample_field_geometry):
        """Тест порядка зон: NDVI должен возрастать от Низкой к Высокой."""
        zones = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=3)
        
        ndvi_values = [z["avg_ndvi"] for z in zones]
        
        # Проверяем что NDVI возрастает
        assert ndvi_values[0] < ndvi_values[1] < ndvi_values[2], \
            f"NDVI должен возрастать: {ndvi_values}"

    def test_geometry_wkt_valid(self, sample_tiff_path, sample_field_geometry):
        """Тест валидности WKT геометрии зон."""
        from shapely import wkt
        
        zones = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=3)
        
        for zone in zones:
            geom = wkt.loads(zone["geometry_wkt"])
            assert geom.is_valid, f"Геометрия зоны {zone['name']} невалидна"
            assert geom.area > 0, f"Площадь зоны {zone['name']} равна 0"

    def test_insufficient_data(self, tmp_path):
        """Тест: мало данных для кластеризации."""
        # Создаём очень маленький растр
        tiff_path = tmp_path / "tiny.tif"
        width, height = 5, 5
        bounds = (18.72, 48.20, 18.74, 48.22)
        
        # Пустые данные (все NoData)
        ndvi_data = np.full((height, width), -9999, dtype=np.float32)
        
        transform = from_bounds(*bounds, width, height)
        with rasterio.open(
            tiff_path, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=ndvi_data.dtype,
            crs='EPSG:4326',
            transform=transform,
            nodata=-9999
        ) as dst:
            dst.write(ndvi_data, 1)
        
        field_geom = box(18.72, 48.20, 18.74, 48.22).wkt
        zones = process_ndvi_zones(str(tiff_path), field_geom, num_zones=3)
        
        assert len(zones) == 0, "При недостатке данных должно вернуться 0 зон"

    def test_custom_num_zones(self, sample_tiff_path, sample_field_geometry):
        """Тест пользовательского количества зон."""
        zones_2 = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=2)
        zones_5 = process_ndvi_zones(sample_tiff_path, sample_field_geometry, num_zones=5)
        
        assert len(zones_2) == 2, f"Должно быть 2 зоны, получено {len(zones_2)}"
        # После морфологической обработки некоторые зоны могут объединиться
        assert len(zones_5) >= 1, f"Должна быть хотя бы 1 зона, получено {len(zones_5)}"

    def test_large_raster_downsampling(self, tmp_path):
        """Тест: большой растр уменьшается для производительности."""
        tiff_path = tmp_path / "large.tif"
        
        # Создаём большой растр 2000x2000
        width, height = 2000, 2000
        bounds = (18.72, 48.20, 18.74, 48.22)
        
        # Простые данные
        ndvi_data = np.random.uniform(0.3, 0.8, (height, width)).astype(np.float32)
        
        transform = from_bounds(*bounds, width, height)
        with rasterio.open(
            tiff_path, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=ndvi_data.dtype,
            crs='EPSG:4326',
            transform=transform,
            nodata=-9999
        ) as dst:
            dst.write(ndvi_data, 1)
        
        field_geom = box(18.72, 48.20, 18.74, 48.22).wkt
        zones = process_ndvi_zones(str(tiff_path), field_geom, num_zones=3)
        
        # Должны создаться зоны несмотря на большой размер
        # После морфологической обработки может остаться 1-3 зоны
        assert len(zones) >= 1, f"Должна быть хотя бы 1 зона, получено {len(zones)}"
