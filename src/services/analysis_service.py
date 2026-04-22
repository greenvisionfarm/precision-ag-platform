
import numpy as np
import rasterio
from rasterio.mask import mask as raster_mask
from shapely import wkt
import logging

logger = logging.getLogger(__name__)

def compare_scans(scan1_path, scan2_path, field_geometry_wkt):
    """
    Сравнивает два NDVI скана для одного поля.
    scan1 - базовый (прошлый)
    scan2 - текущий (новый)
    """
    field_geom = wkt.loads(field_geometry_wkt)

    with rasterio.open(scan1_path) as src1, rasterio.open(scan2_path) as src2:
        # 1. Маскируем оба растра по геометрии поля, приводя их к одной сетке
        # Для этого используем общую геометрию и фиксированное разрешение
        
        # Определяем общее разрешение (выбираем более детальное)
        res_x = min(src1.res[0], src2.res[0])
        res_y = min(src1.res[1], src2.res[1])
        
        # Маскируем первый растр
        data1, transform1 = raster_mask(src1, [field_geom], crop=True)
        data1 = data1[0]
        
        # Маскируем второй растр
        data2, transform2 = raster_mask(src2, [field_geom], crop=True)
        data2 = data2[0]
        
        # Проблема: data1 и data2 могут иметь разные размеры, если они из разных источников
        # Для простоты в первой итерации мы предполагаем, что если они для одного поля, 
        # то после raster_mask с crop=True они будут ОЧЕНЬ близки по размеру.
        # Но по-хорошему нужно ресемплировать.
        
        if data1.shape != data2.shape:
            logger.warning(f"Размеры растров не совпадают: {data1.shape} vs {data2.shape}. Ресемплинг...")
            # Ресемплируем data2 к сетке data1
            from rasterio.enums import Resampling
            data2 = src2.read(
                1,
                out_shape=data1.shape,
                resampling=Resampling.bilinear,
                window=rasterio.windows.from_bounds(*field_geom.bounds, src2.transform)
            )

        # Убираем NoData (обычно 0 или значения вне [-1, 1])
        mask1 = (data1 > -1.0) & (data1 <= 1.0) & (data1 != 0)
        mask2 = (data2 > -1.0) & (data2 <= 1.0) & (data2 != 0)
        common_mask = mask1 & mask2
        
        if not np.any(common_mask):
            return {
                "error": "Нет пересекающихся данных для сравнения",
                "delta_avg": 0.0,
                "improvement_area_pct": 0.0,
                "degradation_area_pct": 0.0,
                "stable_area_pct": 0.0
            }

        diff = data2[common_mask] - data1[common_mask]
        delta_avg = np.mean(diff)
        
        # Статистика
        improved = diff > 0.05  # Значимое улучшение
        degraded = diff < -0.05 # Значимое ухудшение
        stable = ~(improved | degraded)
        
        total_pixels = len(diff)
        
        return {
            "delta_avg": float(delta_avg),
            "improvement_area_pct": float(np.sum(improved) / total_pixels * 100),
            "degradation_area_pct": float(np.sum(degraded) / total_pixels * 100),
            "stable_area_pct": float(np.sum(stable) / total_pixels * 100),
            "stats": {
                "max_increase": float(np.max(diff)),
                "max_decrease": float(np.min(diff)),
                "std_dev": float(np.std(diff))
            }
        }
