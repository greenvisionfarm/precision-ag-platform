"""
Фоновые задачи Huey для обработки данных.
"""
import logging
import os
from datetime import datetime
from typing import Any, Optional

from huey import RedisHuey

from src.utils.db_utils import db_connection

# Настройка Huey
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
huey = RedisHuey('field-mapper', url=redis_url)


def _process_geotiff_impl(file_path: str, field_id: int, scan_id: Optional[int] = None) -> bool:
    """Реализация обработки GeoTIFF (без декоратора huey).

    Args:
        file_path: Путь к файлу GeoTIFF.
        field_id: ID поля для обработки.
        scan_id: ID скана для обновления статуса (опционально).

    Returns:
        True если обработка успешна, False иначе.
    """
    # Импортируем database внутри функции чтобы использовать правильный путь
    from db import Field, FieldZone, FieldScan, database
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
                        color=z['color']
                    )

                # Обновляем статус скана
                if scan_id:
                    FieldScan.update(processed='true').where(FieldScan.id == scan_id).execute()

            logging.info(f"Обработка завершена. Зон создано: {len(zones_data)}")

            # Удаляем временный файл после успешной обработки
            if os.path.exists(file_path):
                os.remove(file_path)

            return True

    except Exception as e:
        logging.error(f"Ошибка в фоновой задаче: {str(e)}")
        if scan_id:
            FieldScan.update(processed='false').where(FieldScan.id == scan_id).execute()
        return False


@huey.task()
def process_geotiff_task(file_path: str, field_id: int, scan_id: Optional[int] = None) -> bool:
    """Фоновая задача по обработке GeoTIFF и созданию зон.

    Args:
        file_path: Путь к файлу GeoTIFF.
        field_id: ID поля для обработки.
        scan_id: ID скана для обновления статуса (опционально).

    Returns:
        True если обработка успешна, False иначе.
    """
    return _process_geotiff_impl(file_path, field_id, scan_id)


def _process_orthomosaic_impl(
    zip_path: str,
    field_id: int,
    crop_type: Optional[str] = None
) -> dict:
    """
    Реализация обработки снимков с дрона (ортомозаика).
    
    Args:
        zip_path: Путь к ZIP архиву со снимками
        field_id: ID поля
        crop_type: Тип культуры (опционально)
        
    Returns:
        Результаты обработки
    """
    from db import Field, FieldScan, database
    from src.services.orthomosaic_service import process_drone_imagery
    from src.services.crop_classifier import classify_from_orthomosaic
    
    logging.info(f"Запуск обработки ортомозаики: {zip_path} для поля ID {field_id}")
    
    try:
        # 1. Создаём ортомозаику и обрабатываем NDVI
        results = process_drone_imagery(zip_path, field_id, crop_type)
        
        if results.get("error"):
            logging.error(f"Ошибка обработки ортомозаики: {results['error']}")
            return {"error": results["error"]}
        
        # 2. Если crop_type='auto', классифицируем культуру
        if crop_type == 'auto' and results.get("orthomosaic", {}).get("output_path"):
            ortho_path = results["orthomosaic"]["output_path"]
            
            # Получаем дату съёмки из первого снимка
            acquisition_date = None
            with db_connection():
                scan = FieldScan.get_by_id(results.get("scan_id"))
                if scan and scan.uploaded_at:
                    acquisition_date = scan.uploaded_at
            
            # Классифицируем
            crop_result = classify_from_orthomosaic(
                ortho_path,
                acquisition_date=acquisition_date
            )
            
            results["crop_classification"] = crop_result
            
            # Сохраняем в БД
            with db_connection():
                if results.get("scan_id"):
                    scan = FieldScan.get_by_id(results["scan_id"])
                    scan.crop_type = crop_result.get("crop_type")
                    scan.crop_confidence = crop_result.get("confidence", 0)
                    scan.save()
        
        logging.info(f"Обработка ортомозаики завершена: {results}")
        
        # Удаляем временный ZIP
        if os.path.exists(zip_path):
            os.remove(zip_path)
        
        return results
        
    except Exception as e:
        logging.error(f"Ошибка в задаче ортомозаики: {str(e)}", exc_info=True)
        return {"error": str(e)}


@huey.task()
def process_orthomosaic_task(
    zip_path: str,
    field_id: int,
    crop_type: Optional[str] = None
) -> dict:
    """
    Фоновая задача по обработке снимков с дрона.
    
    Создаёт ортомозаику из ZIP архива со снимками,
    обрабатывает NDVI и классифицирует культуру.
    
    Args:
        zip_path: Путь к ZIP архиву со снимками
        field_id: ID поля
        crop_type: Тип культуры (опционально)
        
    Returns:
        Результаты обработки
    """
    return _process_orthomosaic_impl(zip_path, field_id, crop_type)
