"""
Фоновые задачи Huey для обработки данных.
"""
import logging
import os
from datetime import datetime
from typing import Optional

from huey import RedisHuey

from src.utils.db_utils import db_connection

# Настройка Huey
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
huey = RedisHuey('field-mapper', url=redis_url)


def _process_geotiff_impl(file_path: str, field_id: int, scan_id: Optional[int] = None) -> bool:
    """Внутренняя реализация обработки GeoTIFF, вызываемая из задачи и тестов."""
    from db import Field, FieldScan, FieldZone, database
    from src.services.crop_classifier import classify_from_raster
    from src.services.raster_service import process_ndvi_zones

    logging.info(f"Запуск обработки растра: {file_path} для поля ID {field_id}")

    try:
        with db_connection():
            field = Field.get_by_id(field_id)

            # Запускаем тяжелое зонирование
            zones_data = process_ndvi_zones(file_path, field.geometry_wkt)

            if not zones_data:
                logging.error("Не удалось выделить зоны")
                if scan_id:
                    FieldScan.update(processed='false').where(FieldScan.id == scan_id).execute()
                return False

            # Классификация культуры
            crop_result = classify_from_raster(file_path)
            crop_type = crop_result.get("crop_type")
            crop_confidence = crop_result.get("confidence")

            # Сохраняем зоны в БД в транзакции
            with database.atomic():
                # Если есть scan_id, привязываем зоны к скану и удаляем старые зоны этого скана
                if scan_id:
                    FieldZone.delete().where(FieldZone.field == field, FieldZone.scan == scan_id).execute()
                else:
                    # Для обратной совместимости - удаляем все старые зоны поля
                    FieldZone.delete().where(FieldZone.field == field).execute()

                for z in zones_data:
                    FieldZone.create(
                        field=field,
                        scan=scan_id if scan_id else None,
                        name=z['name'],
                        geometry_wkt=z['geometry_wkt'],
                        avg_ndvi=z['avg_ndvi'],
                        color=z['color'],
                        rate_kg_ha=z.get('rate_kg_ha')
                    )

                # Обновляем статус скана с результатами классификации
                if scan_id:
                    update_fields = {'processed': 'true'}
                    if crop_type:
                        update_fields['crop_type'] = crop_type
                    if crop_confidence is not None:
                        update_fields['crop_confidence'] = crop_confidence
                    FieldScan.update(**update_fields).where(FieldScan.id == scan_id).execute()

            logging.info(f"Обработка завершена. Зон создано: {len(zones_data)}. Культура: {crop_type}")

            # Удаляем временный файл после успешной обработки
            if os.path.exists(file_path):
                os.remove(file_path)

            return True

    except Exception as e:
        logging.error(f"Ошибка в реализации обработки: {str(e)}")
        if scan_id:
            FieldScan.update(processed='false').where(FieldScan.id == scan_id).execute()
        return False


@huey.task()
def process_geotiff_task(file_path: str, field_id: int, scan_id: Optional[int] = None) -> bool:
    """Фоновая задача по обработке GeoTIFF и созданию зон."""
    return _process_geotiff_impl(file_path, field_id, scan_id)


@huey.task()
def process_drone_fast_task(
    zip_path: str,
    field_id: int,
    total_fertilizer_kg: Optional[float] = None,
    scan_id: Optional[int] = None,
) -> dict:
    """Быстрая обработка снимков с дрона без создания ортомозаики."""
    from src.services.fast_drone_pipeline import FastDronePipeline
    logging.info(f"Запуск БЫСТРОЙ обработки дрона: {zip_path} для поля ID {field_id}")
    return FastDronePipeline().run(zip_path, field_id, total_fertilizer_kg, scan_id)


def _process_orthomosaic_impl(
    zip_path: str,
    field_id: int,
    total_fertilizer_kg: Optional[float] = None,
    scan_id: Optional[int] = None,
) -> dict:
    """Внутренняя реализация обработки ортомозаики."""
    from src.services.orthomosaic_pipeline import OrthomosaicPipeline
    logging.info(f"Запуск ОРТОМОЗАИКИ: {zip_path} для поля ID {field_id}")
    return OrthomosaicPipeline().run(zip_path, field_id, total_fertilizer_kg, scan_id)


@huey.task()
def process_orthomosaic_task(
    zip_path: str,
    field_id: int,
    total_fertilizer_kg: Optional[float] = None,
    scan_id: Optional[int] = None,
) -> dict:
    """Фоновая задача по созданию ортомозаики из дрон-снимков."""
    return _process_orthomosaic_impl(zip_path, field_id, total_fertilizer_kg, scan_id)
