import os
import logging
import numpy as np
import rasterio
import pandas as pd
import geopandas as gpd
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from shapely.geometry import Point
from shapely import wkt
from scipy.interpolate import griddata
from rasterio.transform import from_origin

from src.services.raster_service import process_ndvi_zones
from src.services.provider_dji import DJIProvider

logger = logging.getLogger(__name__)

@dataclass
class DronePoint:
    lat: float
    lon: float
    ndvi: float
    ndre: float
    alt: float = 0.0
    file_name: str = ""

class DroneProcessingService:
    def __init__(self):
        self.provider = DJIProvider()

    def process_directory(self, dir_path: str) -> List[DronePoint]:
        """Оркестрация обработки снимков DJI с нормализацией."""
        file_groups = self.provider.group_files_by_prefix(dir_path)
        points = []
        
        for base, bands in file_groups.items():
            # Нам нужен хотя бы один файл для GPS
            any_file = next(iter(bands.values()))
            meta = self.provider.extract_dji_meta(any_file)
            if meta["lat"] == 0.0: continue

            ndvi, ndre = 0.0, 0.0
            try:
                # 1. Нормализованный расчет NDVI (NIR & RED)
                if 'NIR' in bands and 'RED' in bands:
                    nir = self.provider.get_normalized_band(bands['NIR'])
                    red = self.provider.get_normalized_band(bands['RED'])
                    
                    # Индекс на массивах
                    ndvi_arr = (nir - red) / (nir + red + 1e-10)
                    # Берем медиану по кадру (центр обычно чище)
                    ndvi = float(np.median(ndvi_arr))
                
                # 2. Нормализованный расчет NDRE (NIR & RE)
                if 'NIR' in bands and 'RE' in bands:
                    nir = self.provider.get_normalized_band(bands['NIR'])
                    re = self.provider.get_normalized_band(bands['RE'])
                    ndre_arr = (nir - re) / (nir + re + 1e-10)
                    ndre = float(np.median(ndre_arr))
            except Exception as e:
                logger.error(f"Error processing {base}: {e}")

            # Фильтр: отсекаем совсем пустые или ошибочные значения
            if ndvi > 0.05 or ndre > 0.05:
                points.append(DronePoint(
                    lat=meta["lat"], lon=meta["lon"], alt=meta["alt"],
                    ndvi=ndvi, ndre=ndre,
                    file_name=base
                ))
        
        logger.info(f"[DIAG] Групп: {len(file_groups)} | Точек с индексами: {len(points)}")
        return points

    def create_grid_and_zone(self, points: List[DronePoint], field_wkt: str, output_tif: str):
        """Создает метрическую сетку (EPSG:3035) и выделяет 4 зоны по перцентилям."""
        if not points: return []
        
        df = pd.DataFrame([p.__dict__ for p in points])
        field_geom = wkt.loads(field_wkt)
        
        # 1. Проекция в EPSG:3035 для точных расчетов в метрах
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        gdf_m = gdf.to_crs(epsg=3035)
        
        # Границы сетки (с запасом 20м)
        minx, miny, maxx, maxy = gdf_m.total_bounds
        minx -= 20; miny -= 20; maxx += 20; maxy += 20
        
        # Разрешение сетки - 2 метра (оптимально для техники)
        res_m = 2.0
        width = int((maxx - minx) / res_m)
        height = int((maxy - miny) / res_m)
        
        # 2. Интерполяция (GridData)
        # Композитный индекс: 70% NDVI + 30% NDRE
        gdf_m['health'] = 0.7 * gdf_m['ndvi'] + 0.3 * gdf_m['ndre']
        
        gx = np.linspace(minx, maxx, width)
        gy = np.linspace(maxy, miny, height)
        grid_x, grid_y = np.meshgrid(gx, gy)
        
        points_xy = np.column_stack((gdf_m.geometry.x, gdf_m.geometry.y))
        grid_values = griddata(points_xy, gdf_m['health'], (grid_x, grid_y), method='linear')
        grid_values = np.nan_to_num(grid_values, nan=0.0)

        # 3. Сохранение в TIF
        transform = from_origin(minx, maxy, res_m, res_m)
        with rasterio.open(
            output_tif, 'w', driver='GTiff', height=height, width=width,
            count=1, dtype='float32', crs='EPSG:3035', transform=transform, nodata=0
        ) as dst:
            dst.write(grid_values, 1)

        # 4. Зонирование (Вызываем существующий сервис, но передаем запрос на 4 зоны)
        # Мы адаптируем process_ndvi_zones чтобы он понимал EPSG:3035
        return self._process_vra_zones(output_tif, field_wkt)

    def _process_vra_zones(self, tif_path: str, field_wkt: str) -> List[Dict]:
        """
        Специализированное зонирование для VRA: 4 зоны по перцентилям.
        """
        # Импортируем внутри чтобы избежать циклических зависимостей
        from src.services.raster_service import process_ndvi_zones
        
        # Временно вызываем старый метод, но с параметром num_zones=4
        # Позже мы обновим и сам raster_service
        return process_ndvi_zones(tif_path, field_wkt, num_zones=4)

    def calculate_vra_rates(self, zones: List[Dict], total_fertilizer_kg: float) -> List[Dict]:
        """Расчет доз внесения с балансом массы."""
        from src.services.core_math import calculate_vra_redistribution
        
        # Убеждаемся что зоны имеют площади
        for z in zones:
            geom = wkt.loads(z['geometry_wkt'])
            z['area_raw'] = geom.area # В EPSG:3035 это уже квадратные метры
            
        return calculate_vra_redistribution(zones, total_fertilizer_kg)
