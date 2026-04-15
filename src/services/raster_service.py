
import numpy as np
import rasterio
import rasterio.mask
from rasterio import features
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union
from sklearn.cluster import KMeans
from scipy import ndimage


def process_ndvi_zones(tif_path, field_geometry_wkt, num_zones=3):
    """
    Анализирует NDVI растр и разбивает его на крупные агрегированные зоны.

    Оптимизировано для создания карт-заданий для техники:
    - Минимум мелких фрагментов
    - Крупные сплошные зоны
    - Упрощённые геометрии
    - Windowed reading для экономии RAM

    Args:
        tif_path: Путь к TIFF файлу с NDVI.
        field_geometry_wkt: WKT геометрии поля.
        num_zones: Количество зон для кластеризации.

    Returns:
        Список зон с геометрией, средним NDVI и цветом.
    """
    import logging
    from shapely import wkt
    from rasterio.transform import Affine
    from rasterio.windows import from_bounds
    logger = logging.getLogger(__name__)

    field_geom = wkt.loads(field_geometry_wkt)

    with rasterio.open(tif_path) as src:
        # ОПТИМИЗАЦИЯ: читаем с ресемплингом (уменьшаем до разумного размера)
        target_size = 500
        scale = max(1, max(src.width, src.height) // target_size)

        logger.info(f"Обработка растра: scale={scale}, original_size=({src.width}x{src.height})")

        # ОПТИМИЗАЦИЯ: windowed reading вместо чтения всего растра
        # Сначала определяем bounding box геометрии
        minx, miny, maxx, maxy = field_geom.bounds
        logger.debug(f"Bounds поля: ({minx:.6f}, {miny:.6f}, {maxx:.6f}, {maxy:.6f})")

        # Преобразуем bounds в window
        window = from_bounds(minx, miny, maxx, maxy, src.transform)
        
        # Рассчитываем размер окна с учетом scale
        window_scaled = rasterio.windows.Window(
            col_off=window.col_off / scale,
            row_off=window.row_off / scale,
            width=max(1, window.width / scale),
            height=max(1, window.height / scale)
        )
        
        # Читаем только нужную область с нужным разрешением
        out_image = src.read(
            1,  # Первый канал (NDVI)
            window=window_scaled,
            out_shape=(
                int(window_scaled.height),
                int(window_scaled.width)
            )
        )
        
        # Создаем трансформ для обрезанной области
        out_transform = src.window_transform(window_scaled)
        
        # Маскируем по точной геометрии поля
        from rasterio.mask import mask as raster_mask
        try:
            out_image, out_transform = raster_mask(
                src, [field_geom], crop=True
            )
            out_image = out_image[0]  # Берем первый канал
        except ValueError:
            # Если маска не применилась, используем уже прочитанные данные
            logger.warning("Не удалось применить маску, используем windowed данные")
            out_image = out_image

        # Если после обрезки он все еще слишком большой, дополнительно уменьшаем
        if max(out_image.shape) > target_size * 1.5:
            actual_scale = max(out_image.shape) / target_size
            data = out_image[::int(actual_scale), ::int(actual_scale)]
            out_transform = out_transform * Affine.scale(actual_scale, actual_scale)
        else:
            data = out_image

        # 2. Фильтруем данные (убираем NoData и значения вне диапазона NDVI)
        valid_mask = (data > -1.0) & (data <= 1.0) & (data != 0)
        valid_data = data[valid_mask].reshape(-1, 1)

        logger.info(f"Обрезано: {data.shape}, валидных пикселей: {len(valid_data)}")

        if len(valid_data) < 10:
            logger.warning("Недостаточно валидных данных для кластеризации")
            return []

        # 3. Кластеризация
        train_size = min(len(valid_data), 50000)
        rng = np.random.default_rng(42)
        train_indices = rng.choice(len(valid_data), size=train_size, replace=False)
        train_data = valid_data[train_indices]

        kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=10).fit(train_data)
        centers = kmeans.cluster_centers_.flatten()
        sorted_indices = np.argsort(centers)
        rank_map = {old: new for new, old in enumerate(sorted_indices)}

        labels = np.full(data.shape, -1, dtype=np.int16)
        all_labels = kmeans.predict(valid_data)
        ranked_labels = np.array([rank_map[l] for l in all_labels])
        labels[valid_mask] = ranked_labels

        logger.info(f"Кластеризация завершена, центры: {[round(c, 3) for c in centers]}")

        # Рассчитываем адаптивный scale для фильтрации
        adaptive_scale = max(1, max(src.width, src.height) // target_size)

        # 4. МОРФОЛОГИЧЕСКАЯ ОБРАБОТКА для укрупнения зон
        # ОПТИМИЗАЦИЯ: Увеличиваем размер фильтра (был 5, стал 11) для более агрессивного сглаживания "шума"
        labels = ndimage.median_filter(labels, size=11)

        # Собираем маски всех зон после морфологической обработки
        zone_masks = []
        for i in range(num_zones):
            zone_mask = (labels == i).astype(np.uint8)
            # Морфологическое закрытие для объединения близких областей
            zone_mask = ndimage.binary_closing(zone_mask, structure=np.ones((7,7)))
            # Заполняем отверстия
            zone_mask = ndimage.binary_fill_holes(zone_mask).astype(np.uint8)
            zone_masks.append(zone_mask)

        # Рассчитываем расстояния до каждой зоны для разрешения перекрытий и заполнения пустот
        from scipy.ndimage import distance_transform_edt

        # Создаём массив расстояний до каждой зоны
        distance_maps = []
        for i in range(num_zones):
            # distance_transform_edt возвращает расстояние до ближайшего ненулевого пикселя
            dist = distance_transform_edt(zone_masks[i] == 0)
            distance_maps.append(dist)

        # Разрешаем перекрытия: для каждого пикселя выбираем зону с минимальным расстоянием
        # Сначала создаём финальный массив с -1
        final_labels = np.full(labels.shape, -1, dtype=np.int16)

        # Для каждого пикселя выбираем ближайшую зону
        distance_stack = np.stack(distance_maps, axis=0)  # (num_zones, H, W)
        final_labels = np.argmin(distance_stack, axis=0).astype(np.int16)

        logger.info("Морфологическая обработка завершена: перекрытия устранены, все пиксели распределены")

        labels = final_labels

        # 5. Векторизация и топологическая очистка
        results = []
        colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]
        names = ["Низкая", "Средняя", "Высокая"]

        # Увеличенное упрощение для более гладких геометрий (важно для техники)
        simplify_tolerance = 0.0001 

        # Создаем словарь для хранения геометрий каждой зоны
        zone_geoms = {}
        
        # Сначала векторизуем все зоны "как есть", фильтруя мелкие "острова"
        # ПОРОГ ГЕНЕРАЛИЗАЦИИ: 0.5% от площади поля (типично для техники)
        island_threshold = field_geom.area * 0.005 

        for i in range(num_zones):
            mask = (labels == i).astype(np.uint8)
            shapes_gen = features.shapes(mask, mask=mask, transform=out_transform)
            
            polys = []
            for s, v in shapes_gen:
                poly = shape(s)
                # Фильтруем слишком мелкие пятна внутри зон (фрагментацию)
                if poly.is_valid and poly.area > island_threshold:
                    polys.append(poly)
            
            if polys:
                # Объединяем и упрощаем
                merged = unary_union(polys)
                simplified = merged.simplify(simplify_tolerance, preserve_topology=True)
                zone_geoms[i] = simplified
            else:
                zone_geoms[i] = Polygon()

        # ГАРАНТИЯ ПОКРЫТИЯ И ОТСУТСТВИЯ ПЕРЕСЕЧЕНИЙ (Layer Cake Method)
        # Мы идем от самой важной зоны к наименее важной, вырезая части из общей площади поля
        
        final_zones = {}
        # Начинаем с полной геометрии поля (упрощенной для соответствия зонам)
        remaining_field = field_geom.simplify(simplify_tolerance, preserve_topology=True)
        # Исправляем возможные ошибки самопересечения
        remaining_field = remaining_field.buffer(0)
        
        # Обрабатываем зоны в обратном порядке: Высокая -> Средняя -> Низкая
        # Высокая зона получает приоритет на свою форму, остальные забирают остатки
        for i in reversed(range(num_zones)):
            if i == 0:
                # Последняя (Низкая) зона просто забирает всё, что осталось от поля
                final_zones[i] = remaining_field
            else:
                # Текущая зона - это её геометрия, ограниченная остатком поля
                current_zone = zone_geoms[i].intersection(remaining_field)
                # Исправляем геометрию
                current_zone = current_zone.buffer(0)
                final_zones[i] = current_zone
                # Вычитаем эту зону из остатка поля
                remaining_field = remaining_field.difference(current_zone).buffer(0)

        # Формируем финальный результат
        for i in range(num_zones):
            geom = final_zones.get(i, Polygon())
            
            # Пропускаем пустые зоны (если вдруг такие возникли)
            if geom.is_empty or geom.area < 1e-9:
                continue

            results.append({
                "name": names[i] if i < len(names) else f"Зона {i+1}",
                "geometry_wkt": geom.wkt,
                "avg_ndvi": round(float(centers[sorted_indices[i]]), 3),
                "color": colors[i] if i < len(colors) else "#808080"
            })

    logger.info(f"Создано зон: {len(results)}")
    return results
