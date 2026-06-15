
import numpy as np
import rasterio
import rasterio.mask
from rasterio import features
from rasterio.transform import Affine
from shapely.geometry import shape
from shapely.ops import unary_union
from sklearn.cluster import KMeans
from scipy import ndimage
import logging
from shapely import wkt
import pyproj
from shapely.ops import transform as shapely_transform

logger = logging.getLogger(__name__)

MAX_PROCESSED_PIXELS = 5_000_000


def _validate_zone_geometry(geom, zone_name, field_area):
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = geom.buffer(0)
        if geom.is_empty or not geom.is_valid:
            return None
    area_ratio = geom.area / field_area if field_area > 0 else 0
    if area_ratio > 1.5 or area_ratio < 0.001:
        return None
    return geom


def process_ndvi_zones(tif_path, field_geometry_wkt, num_zones=3):
    field_geom = wkt.loads(field_geometry_wkt)

    with rasterio.open(tif_path) as src:
        raster_crs = src.crs.to_string() if src.crs else "EPSG:4326"
        full_h, full_w = src.shape
        nodata = src.nodata

        logger.info(f"Raster: {full_w}x{full_h}, CRS={raster_crs}, nodata={nodata}")

        # Трансформация геометрии в CRS растра
        field_geom_proj = field_geom
        if raster_crs != "EPSG:4326":
            try:
                project = pyproj.Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True).transform
                field_geom_proj = shapely_transform(project, field_geom)
            except Exception as e:
                logger.warning(f"CRS transform failed: {e}")

        field_area = field_geom_proj.area

        # Downsampling
        total = full_h * full_w
        downsample = 1
        if total > MAX_PROCESSED_PIXELS:
            downsample = max(1, int(np.ceil(np.sqrt(total / MAX_PROCESSED_PIXELS))))
        ds_h = full_h // downsample
        ds_w = full_w // downsample
        logger.info(f"Processing at {ds_w}x{ds_h} (downsample={downsample})")

        # Читаем растр сразу уменьшенным
        if downsample > 1:
            data = src.read(1, out_shape=(ds_h, ds_w))
            # Масштабируем transform
            out_transform = src.transform * Affine.scale(downsample, downsample)
        else:
            try:
                out_image, out_transform = rasterio.mask.mask(src, [field_geom_proj], crop=True)
                data = out_image[0]
            except Exception as e:
                logger.warning(f"Mask failed: {e}, reading full")
                data = src.read(1)
                out_transform = src.transform

        logger.info(f"Data ready: shape={data.shape}, transform={out_transform}")

        # Фильтрация
        non_zero = data[(data != 0)]
        if nodata is not None:
            non_zero = non_zero[non_zero != nodata]

        data_min = float(np.min(non_zero)) if len(non_zero) > 0 else 0
        data_max = float(np.max(non_zero)) if len(non_zero) > 0 else 0
        logger.info(f"Data range: {data_min:.4f} - {data_max:.4f}")

        if data_max > 1.5:
            data = data.astype(np.float64)
            if data_max > 0:
                data = data / data_max

        valid_mask = (data > 0.05) & (data <= 1.0)
        if nodata is not None:
            valid_mask &= (data != nodata)
        valid_data = data[valid_mask]

        if len(valid_data) < 100:
            logger.error(f"Not enough valid data: {len(valid_data)} pixels")
            return []

        logger.info(f"Valid: {len(valid_data)} / {data.size} ({100*len(valid_data)/data.size:.1f}%)")

        # Классификация
        labels = np.full(data.shape, -1, dtype=np.int16)

        if num_zones == 4:
            p20, p50, p80 = np.percentile(valid_data, [20, 50, 80])
            labels[valid_mask] = 0
            labels[valid_mask & (data > p20)] = 1
            labels[valid_mask & (data > p50)] = 2
            labels[valid_mask & (data > p80)] = 3
            names = ["Очень низкая", "Низкая", "Средняя", "Высокая"]
            colors = ["#ff0000", "#ffa500", "#ffff00", "#008000"]
            logger.info(f"VRA: P20={p20:.3f}, P50={p50:.3f}, P80={p80:.3f}")
        else:
            MAX_SAMPLE = 200_000
            sample = valid_data if len(valid_data) <= MAX_SAMPLE else valid_data[np.random.choice(len(valid_data), MAX_SAMPLE, replace=False)]
            kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=5).fit(sample.reshape(-1, 1))
            centers = kmeans.cluster_centers_.flatten()
            rank_map = {old: new for new, old in enumerate(np.argsort(centers))}
            labels[valid_mask] = np.array([rank_map[l] for l in kmeans.predict(valid_data.reshape(-1, 1))])
            names = ["Низкая", "Средняя", "Высокая"]
            colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]
            logger.info(f"KMeans centers: {sorted(centers)}")

        # Сглаживание: крупный медианный фильтр + удаление мелких компонентов
        labels = ndimage.median_filter(labels, size=7)

        # Удаляем мелкие компоненты
        min_component_size = max(50, data.size // 20_000)
        for zone_id in range(num_zones):
            cleaned, num_features = ndimage.label(labels == zone_id)
            for feat_id in range(1, num_features + 1):
                component = (cleaned == feat_id)
                if component.sum() < min_component_size:
                    labels[component] = -1
        logger.info(f"Post-morphology: min_component={min_component_size}px")

        # Векторизация
        pixel_size = max(abs(out_transform.a), abs(out_transform.e))
        simplify_tolerance = pixel_size * 0.5
        island_threshold = field_area * 0.0005 if field_area > 0 else 0

        back_project = None
        if raster_crs != "EPSG:4326":
            try:
                back_project = pyproj.Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True).transform
            except Exception:
                pass

        # Phase 1: Collect zone polygons in raster CRS, compute avg values
        raw_zones = []
        for i in range(num_zones):
            mask = (labels == i).astype(np.uint8)
            if mask.sum() == 0:
                continue

            shapes_gen = features.shapes(mask, mask=mask, transform=out_transform)

            polys = []
            for s, v in shapes_gen:
                poly = shape(s)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_valid and (island_threshold == 0 or poly.area > island_threshold):
                    polys.append(poly)

            if not polys:
                continue

            zone_union = unary_union(polys).intersection(field_geom_proj)
            if zone_union.is_empty:
                continue

            zone_union = _validate_zone_geometry(zone_union, names[i], field_area)
            if zone_union is None:
                continue

            zone_idx_mask = (labels == i) & valid_mask
            avg_val = float(np.mean(data[zone_idx_mask])) if np.any(zone_idx_mask) else 0.0

            raw_zones.append((i, zone_union, avg_val))

        # Phase 2: Transform all zones to EPSG:4326 first, then remove overlaps
        projected = []
        for i, zone_poly, avg_val in raw_zones:
            if back_project:
                try:
                    geom_4326 = shapely_transform(back_project, zone_poly)
                except Exception:
                    geom_4326 = zone_poly
            else:
                geom_4326 = zone_poly
            projected.append((i, geom_4326, avg_val))

        results = []
        kept_polys = []

        smooth_m = pixel_size * 0.3
        if back_project:
            deg_per_m = 1.0 / 111_000.0
            smooth_deg = smooth_m * deg_per_m
        else:
            smooth_deg = smooth_m

        for i, geom_4326, avg_val in projected:
            geom_4326 = geom_4326.buffer(smooth_deg, quad_segs=8).buffer(-smooth_deg, quad_segs=8)
            if not geom_4326.is_valid:
                geom_4326 = geom_4326.buffer(0)
            if geom_4326.is_empty:
                continue

            for existing_poly in kept_polys:
                overlap = geom_4326.intersection(existing_poly)
                if overlap.area > 0 and overlap.area / geom_4326.area > 0.1:
                    geom_4326 = geom_4326.difference(existing_poly)
                    if geom_4326.is_empty:
                        break

            if geom_4326.is_empty:
                continue

            kept_polys.append(geom_4326)
            logger.info(f"Zone {i} ('{names[i]}'): NDVI={avg_val:.3f}")

            results.append({
                "name": names[i],
                "geometry_wkt": geom_4326.wkt,
                "avg_ndvi": avg_val,
                "color": colors[i]
            })

        logger.info(f"Result: {len(results)} zones")
        return results
