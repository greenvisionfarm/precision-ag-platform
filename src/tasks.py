"""
Фоновые задачи Huey для обработки данных.
"""
import logging
import os
from typing import Any

from huey import RedisHuey

from src.utils.db_utils import db_connection

# Настройка Huey
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
huey = RedisHuey('field-mapper', url=redis_url)


@huey.task()
def process_geotiff_task(file_path: str, field_id: int) -> bool:
    """Фоновая задача по обработке GeoTIFF и созданию зон.

    Args:
        file_path: Путь к файлу GeoTIFF.
        field_id: ID поля для обработки.

    Returns:
        True если обработка успешна, False иначе.
    """
    # Импортируем database внутри функции чтобы использовать правильный путь
    from db import Field, FieldZone, database
    from src.services.raster_service import process_ndvi_zones

    logging.info(f"Запуск обработки растра: {file_path} для поля ID {field_id}")

    try:
        with db_connection():
            field = Field.get_by_id(field_id)

            # Запускаем тяжелое зонирование
            zones_data = process_ndvi_zones(file_path, field.geometry_wkt)

            if not zones_data:
                logging.error("Не удалось выделить зоны")
                return False

            # Сохраняем зоны в БД в транзакции
            with database.atomic():
                # Удаляем старые зоны этого поля
                FieldZone.delete().where(FieldZone.field == field).execute()

                for z in zones_data:
                    FieldZone.create(
                        field=field,
                        name=z['name'],
                        geometry_wkt=z['geometry_wkt'],
                        avg_ndvi=z['avg_ndvi'],
                        color=z['color']
                    )

            logging.info(f"Обработка завершена. Зон создано: {len(zones_data)}")

            # Удаляем временный файл после успешной обработки
            if os.path.exists(file_path):
                os.remove(file_path)

            return True

    except Exception as e:
        logging.error(f"Ошибка в фоновой задаче: {str(e)}")
        return False
