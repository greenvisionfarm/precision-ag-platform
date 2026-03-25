
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
    """
    import logging
    from shapely import wkt
    field_geom = wkt.loads(field_geometry_wkt)

    with rasterio.open(tif_path) as src:
        # ОПТИМИЗАЦИЯ: читаем с ресемплингом (уменьшаем до разумного размера)
        scale = max(1, max(src.width, src.height) // 500)

        # Обрезаем растр по контуру поля (с маской)
        out_image, out_transform = rasterio.mask.mask(
            src, [field_geom], crop=True,
        )

        # Если после обрезки он все еще слишком большой, уменьшаем его
        if scale > 1:
            data = out_image[0]
            # Упрощенный ресемплинг через numpy (берем каждый N-й пиксель)
            data = data[::scale, ::scale]

            # Обновляем трансформ для векторизации (умножаем на scale)
            from rasterio.transform import Affine
            out_transform = out_transform * Affine.scale(scale, scale)
        else:
            data = out_image[0]

        # 2. Фильтруем данные (убираем NoData и значения вне диапазона NDVI)
        valid_mask = (data > -1.0) & (data <= 1.0) & (data != 0)
        valid_data = data[valid_mask].reshape(-1, 1)

        if len(valid_data) < 10:
            logging.warning("Not enough valid data for clustering")
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

        # 4. МОРФОЛОГИЧЕСКАЯ ОБРАБОТКА для укрупнения зон
        # Применяем медианный фильтр для удаления шума
        labels = ndimage.median_filter(labels, size=5)

        # Заполняем мелкие отверстия в зонах
        for i in range(num_zones):
            zone_mask = (labels == i).astype(np.uint8)
            # Морфологическое закрытие для объединения близких областей
            zone_mask = ndimage.binary_closing(zone_mask, structure=np.ones((7,7)))
            # Заполняем отверстия
            zone_mask = ndimage.binary_fill_holes(zone_mask).astype(np.uint8)
            labels[zone_mask == 1] = i

        # 5. Векторизация с агрегацией
        results = []
        colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]
        names = ["Низкая", "Средняя", "Высокая"]

        # Увеличенное упрощение для более гладких геометрий
        simplify_tolerance = 0.0001  # Было 0.00002

        for i in range(num_zones):
            mask = (labels == i).astype(np.uint8)

            # Находим связные компоненты
            labeled_array, num_features = ndimage.label(mask)

            if num_features == 0:
                continue

            # Собираем все полигоны
            all_polygons = []
            for j in range(1, num_features + 1):
                component_mask = (labeled_array == j).astype(np.uint8)
                shapes_gen = features.shapes(component_mask, mask=component_mask, transform=out_transform)
                for s, v in shapes_gen:
                    poly = shape(s)
                    # Фильтруем слишком мелкие полигоны
                    # После ресемплинга площадь в градусах очень мала, поэтому используем адаптивный порог
                    min_area = 0.00005 / (scale * scale)  # Адаптируем под scale
                    if poly.area > min_area:
                        all_polygons.append(poly)

            if not all_polygons:
                continue

            # Объединяем все полигоны зоны в один
            merged = unary_union(all_polygons)

            # Упрощаем геометрию для гладкости
            simplified = merged.simplify(simplify_tolerance, preserve_topology=True)

            results.append({
                "name": names[i] if i < len(names) else f"Зона {i+1}",
                "geometry_wkt": simplified.wkt,
                "avg_ndvi": round(float(centers[sorted_indices[i]]), 3),
                "color": colors[i] if i < len(colors) else "#808080"
            })

    return results
