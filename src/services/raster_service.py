
import numpy as np
import rasterio
import rasterio.mask
from rasterio import features
from shapely.geometry import shape
from shapely.ops import unary_union
from sklearn.cluster import KMeans


def process_ndvi_zones(tif_path, field_geometry_wkt, num_zones=3):
    """
    Анализирует NDVI растр и разбивает его на зоны с использованием ресемплинга для скорости.
    """
    from shapely import wkt
    field_geom = wkt.loads(field_geometry_wkt)
    
    with rasterio.open(tif_path) as src:
        # ОПТИМИЗАЦИЯ: читаем с ресемплингом (уменьшаем в 10 раз)
        # Если файл огромный, уменьшаем до разумного размера (напр. макс 2000 пикселей по стороне)
        scale = max(1, max(src.width, src.height) // 1000)
        
        # Обрезаем растр по контуру поля (с маской и ресемплингом)
        out_image, out_transform = rasterio.mask.mask(
            src, [field_geom], crop=True, 
            # Ресемплинг на этапе чтения
            # Мы не можем просто передать Resampling в mask, поэтому сделаем это чуть иначе
        )
        
        # Если после обрезки он все еще слишком большой, уменьшаем его
        if scale > 1:
            int(out_image.shape[1] / scale)
            int(out_image.shape[2] / scale)
            
            # Читаем данные заново с ресемплингом
            data = out_image[0]
            # Упрощенный ресемплинг через numpy (берем каждый N-й пиксель)
            data = data[::scale, ::scale]
            
            # Обновляем трансформ для векторизации
            from rasterio.transform import Affine
            out_transform = out_transform * Affine.scale(scale, scale)
        else:
            data = out_image[0]

        # 2. Фильтруем данные (убираем NoData и значения вне диапазона NDVI)
        # Обычно NoData в таких файлах это 0 или -9999
        valid_mask = (data > -1.0) & (data <= 1.0) & (data != 0)
        valid_data = data[valid_mask].reshape(-1, 1)
        
        if len(valid_data) < 10:
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

        # 4. Векторизация
        results = []
        colors = ["#ff4d4d", "#ffcc00", "#2eb82e"]
        names = ["Низкая", "Средняя", "Высокая"]
        
        for i in range(num_zones):
            mask = (labels == i).astype(np.uint8)
            shapes = features.shapes(mask, mask=mask, transform=out_transform)
            
            polygons = []
            for s, v in shapes:
                polygons.append(shape(s))
            
            if not polygons: continue
            
            merged = unary_union(polygons)
            # Упрощаем геометрию
            simplified = merged.simplify(0.00002, preserve_topology=True)
            
            results.append({
                "name": names[i] if i < len(names) else f"Зона {i+1}",
                "geometry_wkt": simplified.wkt,
                "avg_ndvi": round(float(centers[sorted_indices[i]]), 3),
                "color": colors[i] if i < len(colors) else "#808080"
            })
            
    return results
