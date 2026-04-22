
import numpy as np
import rasterio
import rasterio.mask
from rasterio import features
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from sklearn.cluster import KMeans
from scipy import ndimage
import logging
from shapely import wkt
from rasterio.transform import Affine
from rasterio.windows import from_bounds
from rasterio.mask import mask as raster_mask
import pyproj
from shapely.ops import transform as shapely_transform

logger = logging.getLogger(__name__)

def process_ndvi_zones(tif_path, field_geometry_wkt, num_zones=3):
    """
    Анализирует NDVI растр и разбивает его на агрегированные зоны.
    Поддерживает KMeans (3 зоны) и Percentiles (4 зоны для VRA).
    """
    field_geom = wkt.loads(field_geometry_wkt)

    with rasterio.open(tif_path) as src:
        raster_crs = src.crs.to_string()
        
        # Если растр в EPSG:3035, а геометрия в 4326 - трансформируем геометрию
        if raster_crs == "EPSG:3035":
            project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform
            field_geom_proj = shapely_transform(project, field_geom)
        else:
            field_geom_proj = field_geom

        # 1. Чтение и маскирование
        try:
            out_image, out_transform = raster_mask(src, [field_geom_proj], crop=True)
            data = out_image[0]
        except Exception as e:
            logger.warning(f"Raster mask failed: {e}. Falling back to full read.")
            data = src.read(1)
            out_transform = src.transform

        # 2. Фильтрация данных
        # Для DJI Mavic 3M почва обычно < 0.2
        valid_mask = (data > 0.1) & (data <= 1.0)
        valid_data = data[valid_mask]

        if len(valid_data) < 100:
            logger.error("Not enough valid data for zoning")
            return []

        # 3. Классификация
        labels = np.full(data.shape, -1, dtype=np.int16)
        
        if num_zones == 4:
            # VRA Strategy: 4 зоны по перцентилям (P20, P50, P80)
            p20 = np.percentile(valid_data, 20)
            p50 = np.percentile(valid_data, 50)
            p80 = np.percentile(valid_data, 80)
            
            labels[valid_mask] = 0
            labels[valid_mask & (data > p20)] = 1
            labels[valid_mask & (data > p50)] = 2
            labels[valid_mask & (data > p80)] = 3
            
            names = ["Очень низкая", "Низкая", "Средняя", "Высокая"]
            colors = ["#ff0000", "#ffa500", "#ffff00", "#008000"]
        else:
            # Стандартная стратегия: KMeans (3 зоны)
            kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=10).fit(valid_data.reshape(-1, 1))
            centers = kmeans.cluster_centers_.flatten()
            rank_map = {old: new for new, old in enumerate(np.argsort(centers))}
            labels[valid_mask] = np.array([rank_map[l] for l in kmeans.predict(valid_data.reshape(-1, 1))])
            
            names = ["Низкая", "Средняя", "Высокая"]
            colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]

        # 4. Генерализация (сглаживание шума)
        # Убираем "соль и перец" через медианный фильтр
        labels = ndimage.median_filter(labels, size=9)

        # 5. Векторизация
        simplify_tolerance = 2.0 if raster_crs == "EPSG:3035" else 0.00005
        island_threshold = field_geom_proj.area * 0.01 
        
        results = []
        # Собираем зоны по порядку от худшей к лучшей
        for i in range(num_zones):
            mask = (labels == i).astype(np.uint8)
            shapes_gen = features.shapes(mask, mask=mask, transform=out_transform)
            
            polys = []
            for s, v in shapes_gen:
                poly = shape(s)
                if poly.is_valid and poly.area > island_threshold:
                    polys.append(poly)
            
            if not polys: continue
            
            zone_union = unary_union(polys).intersection(field_geom_proj)
            if zone_union.is_empty or zone_union.area < island_threshold: continue
            
            # Считаем среднее значение индекса в зоне
            zone_idx_mask = (labels == i) & valid_mask
            avg_val = float(np.mean(data[zone_idx_mask])) if np.any(zone_idx_mask) else 0.0
            
            # Обратная трансформация в 4326 для БД
            if raster_crs == "EPSG:3035":
                back_project = pyproj.Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True).transform
                final_geom = shapely_transform(back_project, zone_union)
            else:
                final_geom = zone_union

            results.append({
                "name": names[i],
                "geometry_wkt": final_geom.simplify(0.00001).wkt,
                "avg_ndvi": avg_val,
                "color": colors[i]
            })

        return results
