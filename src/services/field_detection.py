"""
Определение поля по GPS-координатам из ZIP-архива дрон-снимков.
Приоритет: PPK (.MRK) > EXIF/XMP из TIF.
"""
import logging
import os
import tempfile
import zipfile
from typing import List, Optional, Tuple

from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

logger = logging.getLogger(__name__)


def detect_field_from_gps(
    zip_path: str,
    company_id: int,
) -> Tuple[Optional[int], Optional[dict], List[dict]]:
    """
    Пытается определить поле по GPS координатам из ZIP-архива.

    Args:
        zip_path: Путь к ZIP-архиву со снимками
        company_id: ID компании для фильтрации полей

    Returns:
        (field_id, gps_info, nearby_fields) — field_id может быть None
    """
    from db import Field
    from src.services.provider_dji import DJIProvider
    from src.utils.db_utils import db_connection

    provider = DJIProvider()
    gps_info = None
    detected_point = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

                # Приоритет 1: PPK GPS из .MRK файла (точность ±2см)
                mrk_path = provider.find_mrk_file(tmpdir)
                if mrk_path:
                    ppk_data = provider.parse_ppk_timestamps(mrk_path)
                    if ppk_data:
                        first = ppk_data[0]
                        lat, lon = first['lat'], first['lon']
                        if lat != 0.0 and lon != 0.0:
                            gps_info = {
                                "source": "PPK",
                                "lat": lat,
                                "lon": lon,
                                "quality": first.get('quality', ''),
                                "sigma": f"{first['sigma_n']:.2f}/{first['sigma_e']:.2f}/{first['sigma_u']:.2f}cm",
                            }
                            logger.info(
                                f"PPK GPS: lat={lat}, lon={lon}, "
                                f"quality={first['quality']}, "
                                f"sigma={first['sigma_n']:.2f}/{first['sigma_e']:.2f}/{first['sigma_u']:.2f}cm"
                            )
                            detected_point = Point(lon, lat)

                # Приоритет 2: EXIF/XMP из первого TIF файла
                if not detected_point:
                    files = [f for f in zip_ref.namelist()
                             if f.lower().endswith(('.tif', '.tiff'))]

                    if not files:
                        return None, gps_info, []

                    first_file = files[0]
                    img_path = os.path.join(tmpdir, first_file)

                    meta = provider.extract_dji_meta(img_path)

                    if meta["lat"] == 0.0 or meta["lon"] == 0.0:
                        return None, gps_info, []

                    gps_info = {"source": "EXIF", "lat": meta["lat"], "lon": meta["lon"]}
                    detected_point = Point(meta["lon"], meta["lat"])

                # Ищем поле, содержащее точку, или ближайшие поля
                if detected_point:
                    with db_connection():
                        fields = list(Field.select().where(Field.company_id == company_id))

                        # Проверяем containment
                        for field in fields:
                            field_geom = wkt_loads(field.geometry_wkt)
                            if field_geom.contains(detected_point):
                                return field.id, gps_info, []

                        # Точка не попала ни в одно поле — собираем список с расстояниями
                        fields_list = []
                        for field in fields:
                            field_geom = wkt_loads(field.geometry_wkt)
                            dist_m = field_geom.distance(detected_point) * 111000
                            fields_list.append({"id": field.id, "name": field.name, "distance_m": round(dist_m)})
                        fields_list.sort(key=lambda f: f["distance_m"])
                        return None, gps_info, fields_list[:5]

    except Exception as e:
        logger.error(f"Ошибка определения поля по GPS: {e}")

    return None, gps_info, []
