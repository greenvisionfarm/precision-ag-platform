"""
Handlers для загрузки и обработки снимков с дрона.

Поддерживает:
- Загрузку ZIP архива со снимками (JPEG/TIFF)
- Быструю обработку NDVI на основе GPS-точек (grid-based)
- Автоматическое определение поля по координатам
"""
import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import tornado.web

from db import Field, FieldScan
from src.tasks import process_drone_fast_task
from src.utils.db_utils import db_connection
from src.handlers.upload_handlers import UPLOAD_DIR

import logging
logger = logging.getLogger(__name__)


class DroneUploadHandler(tornado.web.RequestHandler):
    """Handler для загрузки снимков с дрона (ZIP архив)."""

    def post(self) -> None:
        """
        Загружает ZIP архив со снимками для быстрой обработки.
        
        Body параметры (в JSON поле 'data'):
            - field_id: ID поля (опционально, если не указано — авто-определение по GPS)
            - crop_type: Тип культуры (опционально)
            - total_fertilizer_kg: Общая масса удобрений для расчета VRA
        """
        try:
            if 'drone_images' not in self.request.files:
                self.set_status(400)
                self.write({"error": "Нет файла. Используйте поле 'drone_images'"})
                return

            uploaded_file = self.request.files['drone_images'][0]
            
            # Парсим параметры из body
            field_id = None
            crop_type = 'auto'
            total_fertilizer_kg = None
            
            try:
                body = json.loads(self.get_argument('data', '{}'))
                field_id = body.get('field_id')
                crop_type = body.get('crop_type', 'auto')
                total_fertilizer_kg = body.get('total_fertilizer_kg')
            except Exception as e:
                logger.warning(f"Ошибка парсинга параметров: {e}")

            # Сохраняем ZIP файл
            file_ext = os.path.splitext(uploaded_file['filename'])[1] or '.zip'
            unique_filename = f"drone_{uuid.uuid4()}{file_ext}"
            zip_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(zip_path, 'wb') as f:
                f.write(uploaded_file['body'])

            logger.info(f"Загружен архив для быстрой обработки: {uploaded_file['filename']}, {len(uploaded_file['body'])} байт")
            
            # Если field_id не указан — пытаемся определить по GPS из первого снимка
            if not field_id:
                field_id = self._detect_field_from_gps(zip_path)
                if not field_id:
                    os.remove(zip_path)
                    self.set_status(400)
                    self.write({
                        "error": "Не удалось определить поле по GPS. Укажите field_id явно"
                    })
                    return
                logger.info(f"Поле определено по GPS: {field_id}")

            # Проверяем существование поля
            try:
                with db_connection():
                    field = Field.get_by_id(field_id)
            except Field.DoesNotExist:
                os.remove(zip_path)
                self.set_status(404)
                self.write({"error": f"Поле {field_id} не найдено"})
                return

            # 1. Создаём запись скана (status: pending)
            with db_connection():
                scan = FieldScan.create(
                    field=field,
                    file_path=zip_path,
                    filename=uploaded_file['filename'],
                    uploaded_at=datetime.now(),
                    processed='pending',
                    source='drone_fast',
                    crop_type=crop_type if crop_type != 'auto' else None
                )

            # 2. Запускаем фоновую задачу
            task = process_drone_fast_task.delay(
                zip_path=zip_path,
                field_id=field_id,
                total_fertilizer_kg=total_fertilizer_kg,
                scan_id=scan.id
            )

            # 3. Обновляем task_id у скана
            with db_connection():
                scan.task_id = str(task.id)
                scan.save()

            self.write({
                "message": "Запущена обработка снимков (fast mode).",
                "task_id": str(task.id),
                "field_id": field_id,
                "scan_id": scan.id
            })

        except Exception as e:
            logger.error(f"Ошибка в DroneUploadHandler: {e}")
            self.set_status(500)
            self.write({"error": str(e)})

    def _detect_field_from_gps(self, zip_path: str) -> Optional[int]:
        """
        Пытается определить поле по GPS координатам из мультиспектральных снимков.
        """
        import zipfile
        import tempfile
        from shapely.geometry import Point
        from shapely.wkt import loads as wkt_loads
        from src.services.provider_dji import DJIProvider
        
        provider = DJIProvider()
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Ищем любой JPG/TIF файл
                    files = [f for f in zip_ref.namelist() 
                            if f.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff'))]
                    
                    if not files:
                        return None
                    
                    # Извлекаем первый попавшийся файл для получения координат
                    first_file = files[0]
                    zip_ref.extract(first_file, tmpdir)
                    img_path = os.path.join(tmpdir, first_file)
                    
                    # Используем DJIProvider для извлечения метаданных (включая XMP)
                    meta = provider.extract_dji_meta(img_path)
                    
                    if meta["lat"] == 0.0 or meta["lon"] == 0.0:
                        return None
                    
                    # Ищем поле которое содержит эту точку
                    with db_connection():
                        point = Point(meta["lon"], meta["lat"])
                        for field in Field.select():
                            field_geom = wkt_loads(field.geometry_wkt)
                            if field_geom.contains(point) or field_geom.intersects(point):
                                return field.id
                        
        except Exception as e:
            logger.error(f"Ошибка определения поля по GPS: {e}")
        
        return None
