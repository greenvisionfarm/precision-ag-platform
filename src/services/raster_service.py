
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


def _validate_zone_geometry(geom, zone_name, field_area):
    """Validate zone geometry and fix common issues."""
    if geom is None or geom.is_empty:
        logger.warning(f"Zone '{zone_name}': empty geometry, skipping")
        return None

    if not geom.is_valid:
        logger.warning(f"Zone '{zone_name}': invalid geometry, attempting buffer(0)")
        geom = geom.buffer(0)
        if geom.is_empty or not geom.is_valid:
            logger.warning(f"Zone '{zone_name}': geometry still invalid after buffer(0)")
            return None

    # Check for unreasonable area (> 150% of field or < 0.1% of field)
    area_ratio = geom.area / field_area if field_area > 0 else 0
    if area_ratio > 1.5:
        logger.warning(f"Zone '{zone_name}': area ratio {area_ratio:.2f} > 1.5, clipping to field")
        return None
    if area_ratio < 0.001:
        logger.warning(f"Zone '{zone_name}': area ratio {area_ratio:.4f} < 0.1%, too small")
        return None

    return geom


def process_ndvi_zones(tif_path, field_geometry_wkt, num_zones=3):
    """
    Анализирует NDVI растр и разбивает его на агрегированные зоны.
    Поддерживает KMeans (3 зоны) и Percentiles (4 зоны для VRA).
    """
    field_geom = wkt.loads(field_geometry_wkt)

    with rasterio.open(tif_path) as src:
        raster_crs = src.crs.to_string()
        pixel_size_x = abs(src.transform.a)
        pixel_size_y = abs(src.transform.e)

        logger.info(f"Raster CRS: {raster_crs}, pixel size: {pixel_size_x:.6f} x {pixel_size_y:.6f}")

        # Если растр в EPSG:3035, а геометрия в 4326 - трансформируем геометрию
        if raster_crs == "EPSG:3035":
            project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform
            field_geom_proj = shapely_transform(project, field_geom)
        else:
            field_geom_proj = field_geom

        field_area = field_geom_proj.area
        logger.info(f"Field area in CRS units: {field_area:.2f}")

        # 1. Чтение и маскирование
        try:
            out_image, out_transform = raster_mask(src, [field_geom_proj], crop=True)
            data = out_image[0]
            logger.info(f"Raster masked: shape={data.shape}, transform={out_transform}")
        except Exception as e:
            logger.warning(f"Raster mask failed: {e}. Falling back to full read.")
            data = src.read(1)
            out_transform = src.transform

        # 2. Фильтрация данных
        valid_mask = (data > 0.1) & (data <= 1.0)
        valid_data = data[valid_mask]

        if len(valid_data) < 100:
            logger.error(f"Not enough valid data for zoning: {len(valid_data)} valid pixels")
            return []

        logger.info(f"Valid pixels: {len(valid_data)} / {data.size} ({100*len(valid_data)/data.size:.1f}%)")

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
            logger.info(f"VRA zones: P20={p20:.3f}, P50={p50:.3f}, P80={p80:.3f}")
        else:
            # Стандартная стратегия: KMeans (3 зоны)
            kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=10).fit(valid_data.reshape(-1, 1))
            centers = kmeans.cluster_centers_.flatten()
            rank_map = {old: new for new, old in enumerate(np.argsort(centers))}
            labels[valid_mask] = np.array([rank_map[l] for l in kmeans.predict(valid_data.reshape(-1, 1))])

            names = ["Низкая", "Средняя", "Высокая"]
            colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]
            logger.info(f"KMeans centers: {sorted(centers)}")

        # 4. Генерализация (сглаживание шума)
        # Убираем "соль и перец" через медианный фильтр
        labels = ndimage.median_filter(labels, size=9)

        # 5. Векторизация
        # Используем размер пикселя для расчета допусков
        if raster_crs == "EPSG:3035":
            simplify_tolerance = max(pixel_size_x, pixel_size_y) * 2.0
            island_threshold = field_area * 0.005  # 0.5% of field area
        else:
            simplify_tolerance = max(pixel_size_x, pixel_size_y) * 2.0
            island_threshold = field_area * 0.005

        logger.info(f"Vectorization: simplify={simplify_tolerance:.6f}, island_threshold={island_threshold:.2f}")

        results = []
        zone_polys = []  # Track all zone polygons for overlap detection

        # Собираем зоны по порядку от худшей к лучшей
        for i in range(num_zones):
            mask = (labels == i).astype(np.uint8)
            shapes_gen = features.shapes(mask, mask=mask, transform=out_transform)

            polys = []
            for s, v in shapes_gen:
                poly = shape(s)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_valid and poly.area > island_threshold:
                    polys.append(poly)

            if not polys:
                logger.warning(f"Zone {i} ('{names[i]}'): no valid polygons")
                continue

            zone_union = unary_union(polys).intersection(field_geom_proj)
            if zone_union.is_empty:
                logger.warning(f"Zone {i} ('{names[i]}'): empty after intersection")
                continue

            # Validate zone geometry
            zone_union = _validate_zone_geometry(zone_union, names[i], field_area)
            if zone_union is None:
                continue

            # Check for overlap with existing zones
            for j, existing_poly in enumerate(zone_polys):
                overlap = zone_union.intersection(existing_poly)
                if overlap.area > 0:
                    overlap_ratio = overlap.area / zone_union.area
                    if overlap_ratio > 0.1:
                        logger.warning(
                            f"Zone {i} ('{names[i]}') overlaps {overlap_ratio:.1%} with zone {j}"
                        )
                        # Remove overlap
                        zone_union = zone_union.difference(existing_poly)
                        if zone_union.is_empty:
                            logger.warning(f"Zone {i}: became empty after removing overlap")
                            break

            if zone_union.is_empty:
                continue

            zone_polys.append(zone_union)

            # Считаем среднее значение индекса в зоне
            zone_idx_mask = (labels == i) & valid_mask
            avg_val = float(np.mean(data[zone_idx_mask])) if np.any(zone_idx_mask) else 0.0

            # Обратная трансформация в 4326 для БД
            if raster_crs == "EPSG:3035":
                back_project = pyproj.Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True).transform
                final_geom = shapely_transform(back_project, zone_union)
            else:
                final_geom = zone_union

            # Simplify with tolerance appropriate for the data
            final_geom = final_geom.simplify(simplify_tolerance, preserve_topology=True)

            # Final validation
            if not final_geom.is_valid:
                final_geom = final_geom.buffer(0)

            area_ha = final_geom.area * 111320 * 111320 / 10000 if raster_crs == "EPSG:4326" else field_area / 10000
            logger.info(f"Zone {i} ('{names[i]}'): NDVI={avg_val:.3f}, area_ratio={final_geom.area/field_area:.2%}")

            results.append({
                "name": names[i],
                "geometry_wkt": final_geom.wkt,
                "avg_ndvi": avg_val,
                "color": colors[i]
            })

        # Final overlap check
        total_area = sum(
            wkt.loads(z["geometry_wkt"]).area for z in results
        )
        logger.info(f"Total zones: {len(results)}, total area ratio: {total_area/field_area:.2%}")

        return results
