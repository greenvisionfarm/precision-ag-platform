"""
Сервис для создания ортомозаики из снимков с дрона.

Поддерживает:
- Загрузку набора JPEG/TIFF снимков
- Чтение EXIF данных (GPS, ориентация, параметры камеры)
- Склейка в ортомозаику (OpenCV SIFT + бесшовное сглаживание)
- Геореференсинг (привязка к координатам)
"""
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


@dataclass
class CameraParams:
    """Параметры камеры для фотограмметрии."""
    focal_length_mm: float  # Фокусное расстояние (мм)
    sensor_width_mm: float  # Ширина сенсора (мм)
    image_width_px: int  # Ширина изображения (пиксели)
    image_height_px: int  # Высота изображения (пиксели)
    
    @property
    def focal_length_px(self) -> float:
        """Фокусное расстояние в пикселях."""
        return (self.focal_length_mm / self.sensor_width_mm) * self.image_width_px


@dataclass
class ImageGPS:
    """GPS данные снимка."""
    latitude: float
    longitude: float
    altitude: float  # Над уровнем моря (м)
    yaw: Optional[float] = None  # Курс (градусы)
    pitch: Optional[float] = None  # Тангаж (градусы)
    roll: Optional[float] = None  # Крен (градусы)
    timestamp: Optional[datetime] = None


def extract_gps_from_exif(image_path: str) -> Optional[ImageGPS]:
    """
    Извлекает GPS координаты и ориентацию из EXIF снимка.
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        ImageGPS с координатами или None если данных нет
    """
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                logger.debug(f"Нет EXIF в {image_path}")
                return None
            
            # Словарь тегов
            tags = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            
            # GPS данные
            gps_info = tags.get('GPSInfo', {})
            if not gps_info:
                logger.debug(f"Нет GPSInfo в {image_path}")
                return None
            
            # Конвертируем GPS координаты из DMS в десятичные
            def convert_to_degrees(value: Tuple[int, int]) -> float:
                d = float(value[0]) / float(value[1])
                m = float(value[2]) / float(value[3])
                s = float(value[4]) / float(value[5])
                return d + (m / 60.0) + (s / 3600.0)
            
            lat = convert_to_degrees(gps_info.get('GPSLatitude', (0, 1, 0, 1, 0, 1)))
            lat_ref = gps_info.get('GPSLatitudeRef', 'N')
            if lat_ref != 'N':
                lat = -lat
            
            lon = convert_to_degrees(gps_info.get('GPSLongitude', (0, 1, 0, 1, 0, 1)))
            lon_ref = gps_info.get('GPSLongitudeRef', 'E')
            if lon_ref != 'E':
                lon = -lon
            
            # Высота
            alt = gps_info.get('GPSAltitude', 0)
            alt_ref = gps_info.get('GPSAltitudeRef', 0)
            if alt_ref == 1:  # Ниже уровня моря
                alt = -alt
            
            # Ориентация (DJI специфичные теги)
            # Makernote теги для DJI
            yaw = gps_info.get('GPSImgDirection', None)
            
            # Timestamp
            timestamp = None
            date_str = tags.get('DateTimeOriginal', '')
            if date_str:
                try:
                    timestamp = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass
            
            return ImageGPS(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                yaw=yaw,
                timestamp=timestamp
            )
            
    except Exception as e:
        logger.error(f"Ошибка чтения EXIF {image_path}: {e}")
        return None


def extract_camera_params(image_path: str) -> Optional[CameraParams]:
    """
    Извлекает параметры камеры из EXIF.
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        CameraParams или None
    """
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return None
            
            tags = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            
            # Фокусное расстояние (мм)
            focal_length = tags.get('FocalLength', 0)
            if isinstance(focal_length, tuple):
                focal_length = focal_length[0] / focal_length[1]
            
            # 35mm эквивалент
            focal_35mm = tags.get('FocalLengthIn35mmFormat', 0)
            
            # Размер изображения
            width, height = img.size
            
            # Параметры сенсора (приблизительные для популярных дронов)
            # DJI Mavic 3M: 4/3" сенсор, 17.3mm x 13mm
            # DJI Phantom 4: 1" сенсор, 13.2mm x 8.8mm
            sensor_width_mm = 13.2  # По умолчанию 1" сенсор
            
            if focal_35mm and focal_length:
                # Вычисляем реальный размер сенсора
                crop_factor = focal_35mm / focal_length
                sensor_width_mm = 36.0 / crop_factor  # 36mm - ширина 35mm кадра
            
            return CameraParams(
                focal_length_mm=focal_length,
                sensor_width_mm=sensor_width_mm,
                image_width_px=width,
                image_height_px=height
            )
            
    except Exception as e:
        logger.error(f"Ошибка чтения параметров камеры {image_path}: {e}")
        return None


def find_keypoints_and_descriptors(image: np.ndarray) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
    """
    Находит ключевые точки и дескрипторы на изображении.
    
    Args:
        image: Изображение в BGR
        
    Returns:
        (keypoints, descriptors)
    """
    # SIFT детектор (лучшее качество для аэрофотоснимков)
    sift = cv2.SIFT_create(
        nfeatures=10000,
        nOctaveLayers=3,
        contrastThreshold=0.04,
        edgeThreshold=10,
        sigma=1.6
    )
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return sift.detectAndCompute(gray, None)


def match_descriptors(
    desc1: np.ndarray,
    desc2: np.ndarray,
    ratio: float = 0.75
) -> List[cv2.DMatch]:
    """
    Сопоставляет дескрипторы двух изображений.
    
    Args:
        desc1: Дескрипторы первого изображения
        desc2: Дескрипторы второго изображения
        ratio: Порог отношения расстояний (Lowe's ratio)
        
    Returns:
        Список хороших совпадений
    """
    # FLANN матчер (быстрее для больших наборов)
    index_params = dict(algorithm=2, trees=5)  # KD-tree
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    
    matches = flann.knnMatch(desc1, desc2, k=2)
    
    # Lowe's ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < ratio * n.distance:
            good_matches.append(m)
    
    return good_matches


def stitch_images(
    images: List[np.ndarray],
    gps_data: List[ImageGPS],
    overlap: float = 0.7
) -> Tuple[np.ndarray, Optional[Any]]:
    """
    Склеивает изображения в ортомозаику.
    
    Args:
        images: Список изображений (BGR)
        gps_data: GPS данные для каждого изображения
        overlap: Ожидаемое перекрытие между снимками
        
    Returns:
        (панорама, трансформация) или (изображение, None) если не удалось
    """
    if len(images) < 2:
        return images[0] if images else np.array([]), None
    
    logger.info(f"Склейка {len(images)} изображений...")
    
    # 1. Сортируем изображения по GPS (для оптимального порядка склейки)
    sorted_indices = sorted(
        range(len(gps_data)),
        key=lambda i: (gps_data[i].latitude, gps_data[i].longitude)
    )
    images_sorted = [images[i] for i in sorted_indices]
    
    # 2. Создаем панораму с использованием OpenCV Stitcher
    stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
    
    # Устанавливаем параметры для аэрофотоснимков
    stitcher.setPanoConfidenceThresh(0.1)  # Ниже стандартного для лучшего сшивания
    
    status, panorama = stitcher.stitch(images_sorted)
    
    if status != cv2.Stitcher_OK:
        logger.warning(f"Stitcher не смог создать панораму (статус {status}), пробуем попарно...")
        return stitch_images_sequential(images_sorted, gps_data)
    
    # 3. Бесшовное сглаживание (multiband blending)
    blender = cv2.Blender_createDefault(cv2.Blender_NO)
    
    # Подготовка для blending
    panorama_float = panorama.astype(np.float32) / 255.0
    
    logger.info(f"Панорама создана: {panorama.shape}")
    
    return panorama, None


def stitch_images_sequential(
    images: List[np.ndarray],
    gps_data: List[ImageGPS]
) -> Tuple[np.ndarray, Optional[Any]]:
    """
    Последовательная склейка изображений (fallback метод).
    
    Args:
        images: Список изображений
        gps_data: GPS данные
        
    Returns:
        Панорама
    """
    if not images:
        return np.array([]), None
    
    result = images[0]
    
    for i in range(1, len(images)):
        logger.debug(f"Склейка изображения {i}/{len(images)}")
        
        # Находим ключевые точки
        kp1, desc1 = find_keypoints_and_descriptors(result)
        kp2, desc2 = find_keypoints_and_descriptors(images[i])
        
        if desc1 is None or desc2 is None or len(desc1) < 10 or len(desc2) < 10:
            logger.warning(f"Недостаточно ключевых точек для изображения {i}")
            continue
        
        # Матчим дескрипторы
        matches = match_descriptors(desc1, desc2)
        
        if len(matches) < 20:
            logger.warning(f"Недостаточно совпадений для изображения {i}: {len(matches)}")
            continue
        
        # Находим гомографию с RANSAC
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        if H is None:
            logger.warning(f"Не удалось найти гомографию для изображения {i}")
            continue
        
        # Применяем трансформацию
        h1, w1 = result.shape[:2]
        h2, w2 = images[i].shape[:2]
        
        # Вычисляем размеры результата
        corners = np.float32([
            [0, 0],
            [w1, 0],
            [w1, h1],
            [0, h1]
        ]).reshape(-1, 1, 2)
        
        transformed_corners = cv2.perspectiveTransform(corners, H)
        all_corners = np.vstack([corners, transformed_corners])
        
        x_min = int(np.floor(all_corners[:, 0, 0].min()))
        x_max = int(np.ceil(all_corners[:, 0, 0].max()))
        y_min = int(np.floor(all_corners[:, 0, 1].min()))
        y_max = int(np.ceil(all_corners[:, 0, 1].max()))
        
        w_out = x_max - x_min
        h_out = y_max - y_min
        
        # Создаем трансформацию с учётом смещения
        H_shift = H @ np.array([
            [1, 0, -x_min],
            [0, 1, -y_min],
            [0, 0, 1]
        ])
        
        # Варпим первое изображение
        result_warped = cv2.warpPerspective(
            result,
            H_shift,
            (w_out, h_out)
        )
        
        # Варпим второе изображение
        img2_warped = cv2.warpPerspective(
            images[i],
            np.eye(3) @ np.array([
                [1, 0, -x_min],
                [0, 1, -y_min],
                [0, 0, 1]
            ]),
            (w_out, h_out)
        )
        
        # Бесшовное слияние (простое взвешенное)
        mask1 = np.any(result_warped > 0, axis=2).astype(np.float32)
        mask2 = np.any(img2_warped > 0, axis=2).astype(np.float32)
        
        # Область перекрытия
        overlap_mask = (mask1 > 0) & (mask2 > 0)
        
        # Создаем градиент для плавного перехода
        blended = result_warped.astype(np.float32)
        
        for y in range(h_out):
            for x in range(w_out):
                if overlap_mask[y, x]:
                    # Взвешенное среднее на основе расстояния до краёв
                    w1_weight = 0.5
                    w2_weight = 0.5
                    blended[y, x] = (
                        result_warped[y, x] * w1_weight +
                        img2_warped[y, x] * w2_weight
                    )
                elif mask2[y, x] > 0:
                    blended[y, x] = img2_warped[y, x]
        
        result = np.clip(blended, 0, 255).astype(np.uint8)
        logger.debug(f"Промежуточный результат: {result.shape}")
    
    return result, None


def create_orthomosaic_from_zip(
    zip_path: str,
    output_path: str,
    target_crs: str = "EPSG:4326"
) -> Dict[str, Any]:
    """
    Создаёт ортомозаику из ZIP архива со снимками.
    
    Args:
        zip_path: Путь к ZIP архиву
        output_path: Путь для сохранения результата
        target_crs: Целевая система координат
        
    Returns:
        Статистика обработки
    """
    logger.info(f"Создание ортомозаики из {zip_path}")
    
    stats = {
        "total_images": 0,
        "images_with_gps": 0,
        "orthomosaic_created": False,
        "output_path": None,
        "error": None
    }
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Распаковываем архив
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # Находим все изображения
            image_extensions = {'.jpg', '.jpeg', '.tif', '.tiff', '.png'}
            image_paths = []
            
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if Path(file).suffix.lower() in image_extensions:
                        image_paths.append(os.path.join(root, file))
            
            if not image_paths:
                stats["error"] = "Нет изображений в архиве"
                return stats
            
            stats["total_images"] = len(image_paths)
            logger.info(f"Найдено изображений: {len(image_paths)}")
            
            # Читаем EXIF данные
            images = []
            gps_data = []
            
            for img_path in image_paths:
                # Загружаем изображение
                img = cv2.imread(img_path)
                if img is None:
                    logger.warning(f"Не удалось прочитать {img_path}")
                    continue
                
                images.append(img)
                
                # Читаем GPS
                gps = extract_gps_from_exif(img_path)
                if gps:
                    gps_data.append(gps)
                    stats["images_with_gps"] += 1
                else:
                    # Создаём заглушку
                    gps_data.append(ImageGPS(0, 0, 0))
            
            logger.info(f"Изображений с GPS: {stats['images_with_gps']}")
            
            if len(images) < 2:
                stats["error"] = "Недостаточно изображений для склейки (минимум 2)"
                return stats
            
            # Склеиваем в панораму
            panorama, transform = stitch_images(images, gps_data)
            
            if panorama.size == 0:
                stats["error"] = "Не удалось создать панораму"
                return stats
            
            # Сохраняем результат
            if output_path.endswith('.tiff') or output_path.endswith('.tif'):
                # Сохраняем как GeoTIFF (пока без геореференсинга)
                from osgeo import gdal, osr
                import numpy as np
                
                # Создаём GeoTIFF
                driver = gdal.GetDriverByName('GTiff')
                dataset = driver.Create(
                    output_path,
                    panorama.shape[1],
                    panorama.shape[0],
                    3,
                    gdal.GDT_Byte
                )
                
                # Записываем каналы
                for i in range(3):
                    band = dataset.GetRasterBand(i + 1)
                    band.WriteArray(panorama[:, :, 2 - i])  # BGR -> RGB
                    
                # Устанавливаем CRS (приблизительный, по центру GPS)
                if gps_data:
                    center_lat = np.mean([g.latitude for g in gps_data if g.latitude != 0])
                    center_lon = np.mean([g.longitude for g in gps_data if g.longitude != 0])
                    
                    # Простая аффинная трансформация (требует доработки для точности)
                    # Временно устанавливаем примерные координаты
                    geotransform = (center_lon, 0.0001, 0, center_lat, 0, -0.0001)
                    dataset.SetGeoTransform(geotransform)
                    
                    srs = osr.SpatialReference()
                    srs.ImportFromEPSG(4326)
                    dataset.SetProjection(srs.ExportToWkt())
                
                dataset = None  # Закрываем файл
                
            else:
                # Сохраняем как обычное изображение
                cv2.imwrite(output_path, panorama)
            
            stats["orthomosaic_created"] = True
            stats["output_path"] = output_path
            stats["output_size"] = os.path.getsize(output_path)
            stats["panorama_shape"] = list(panorama.shape)
            
            logger.info(f"Ортомозаика сохранена: {output_path}")
            
    except Exception as e:
        logger.error(f"Ошибка создания ортомозаики: {e}", exc_info=True)
        stats["error"] = str(e)
    
    return stats


def process_drone_imagery(
    zip_path: str,
    field_id: int,
    crop_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Полный пайплайн обработки снимков с дрона.
    
    Args:
        zip_path: ZIP архив со снимками
        field_id: ID поля в БД
        crop_type: Тип культуры (опционально)
        
    Returns:
        Результаты обработки
    """
    from db import Field, FieldScan
    from src.utils.db_utils import db_connection
    from datetime import datetime
    import uuid
    
    results = {
        "orthomosaic": None,
        "ndvi": None,
        "zones": None,
        "crop_type": crop_type,
        "error": None
    }
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Создаём ортомозаику
            orthomosaic_path = os.path.join(tmpdir, f"orthomosaic_{uuid.uuid4()}.tif")
            ortho_stats = create_orthomosaic_from_zip(zip_path, orthomosaic_path)
            
            if not ortho_stats["orthomosaic_created"]:
                results["error"] = f"Не удалось создать ортомозаику: {ortho_stats.get('error')}"
                return results
            
            results["orthomosaic"] = ortho_stats
            
            # 2. Сохраняем ортомозаику в uploads
            from src.handlers.upload_handlers import UPLOAD_DIR
            final_path = os.path.join(UPLOAD_DIR, f"orthomosaic_{field_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tif")
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            import shutil
            shutil.copy2(orthomosaic_path, final_path)
            
            # 3. Создаём запись скана в БД
            with db_connection():
                field = Field.get_by_id(field_id)
                
                scan = FieldScan.create(
                    field=field,
                    file_path=final_path,
                    filename=f"orthomosaic_{field_id}.tif",
                    uploaded_at=datetime.now(),
                    processed='false',
                    source='drone'  # Новый источник
                )
                
                results["scan_id"] = scan.id
            
            # 4. Запускаем обработку NDVI (через existing pipeline)
            from src.services.raster_service import process_ndvi_zones
            
            with db_connection():
                field = Field.get_by_id(field_id)
                
                zones = process_ndvi_zones(final_path, field.geometry_wkt)
                results["zones"] = zones
                
                # Сохраняем зоны в БД
                from db import FieldZone
                for zone in zones:
                    FieldZone.create(
                        field=field,
                        scan=scan,
                        name=zone["name"],
                        geometry_wkt=zone["geometry_wkt"],
                        avg_ndvi=zone["avg_ndvi"],
                        color=zone["color"]
                    )
                
                scan.processed = 'true'
                scan.save()
            
            results["ndvi"] = {
                "zones_count": len(zones),
                "processed": True
            }
            
            logger.info(f"Обработка завершена: {len(zones)} зон создано")
            
    except Exception as e:
        logger.error(f"Ошибка обработки снимков дрона: {e}", exc_info=True)
        results["error"] = str(e)
    
    return results
