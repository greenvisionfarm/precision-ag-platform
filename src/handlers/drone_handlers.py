"""
Handlers для загрузки и обработки снимков с дрона.

Поддерживает:
- Загрузку ZIP архива со снимками (JPEG/TIFF)
- Создание ортомозаики
- Автоматическое определение культуры
- Обработка NDVI и создание зон
"""
import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import tornado.web

from db import Field, FieldScan, database
from src.services.orthomosaic_service import process_drone_imagery
from src.services.crop_classifier import classify_from_orthomosaic, CropType
from src.tasks import huey, process_orthomosaic_task
from src.utils.db_utils import db_connection
from src.handlers.upload_handlers import UPLOAD_DIR


class DroneUploadHandler(tornado.web.RequestHandler):
    """Handler для загрузки снимков с дрона (ZIP архив)."""

    def post(self) -> None:
        """
        Загружает ZIP архив со снимками для создания ортомозаики.
        
        Body параметры:
            - field_id: ID поля (опционально, если не указано — авто-определение по GPS)
            - crop_type: Тип культуры (опционально, 'auto' для авто-определения)
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
            
            try:
                body = json.loads(self.get_argument('data', '{}'))
                field_id = body.get('field_id')
                crop_type = body.get('crop_type', 'auto')
            except:
                pass

            # Сохраняем ZIP файл
            file_ext = os.path.splitext(uploaded_file['filename'])[1] or '.zip'
            unique_filename = f"drone_{uuid.uuid4()}{file_ext}"
            zip_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(zip_path, 'wb') as f:
                f.write(uploaded_file['body'])

            logger_info = f"Загружен архив: {uploaded_file['filename']}, {len(uploaded_file['body'])} байт"
            
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
                logger_info += f", поле определено по GPS: {field_id}"

            # Проверяем существование поля
            try:
                with db_connection():
                    field = Field.get_by_id(field_id)
            except Field.DoesNotExist:
                os.remove(zip_path)
                self.set_status(404)
                self.write({"error": f"Поле {field_id} не найдено"})
                return

            # Запускаем фоновую задачу обработки
            task = process_orthomosaic_task.delay(
                zip_path=zip_path,
                field_id=field_id,
                crop_type=crop_type if crop_type != 'auto' else None
            )

            # Создаём запись скана для отслеживания
            with db_connection():
                scan = FieldScan.create(
                    field=field,
                    file_path=zip_path,
                    filename=uploaded_file['filename'],
                    uploaded_at=datetime.now(),
                    processed='pending',
                    source='drone',
                    task_id=str(task.id),
                    crop_type=crop_type if crop_type != 'auto' else None
                )

            self.write({
                "message": "Архив принят. Запущена обработка ортомозаики.",
                "task_id": str(task.id),
                "field_id": field_id,
                "scan_id": scan.id,
                "estimated_time": "2-5 минут в зависимости от количества снимков"
            })

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

    def _detect_field_from_gps(self, zip_path: str) -> Optional[int]:
        """
        Пытается определить поле по GPS координатам из снимков.
        
        Args:
            zip_path: Путь к ZIP архиву
            
        Returns:
            ID поля или None
        """
        import zipfile
        from PIL import Image
        from shapely.geometry import box
        from shapely.wkt import loads as wkt_loads
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Распаковываем первый JPG для чтения EXIF
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    jpg_files = [f for f in zip_ref.namelist() 
                                 if f.lower().endswith(('.jpg', '.jpeg'))]
                    
                    if not jpg_files:
                        return None
                    
                    # Извлекаем первый снимок
                    zip_ref.extract(jpg_files[0], tmpdir)
                    first_img_path = os.path.join(tmpdir, jpg_files[0])
                    
                    # Читаем GPS
                    from src.services.orthomosaic_service import extract_gps_from_exif
                    gps = extract_gps_from_exif(first_img_path)
                    
                    if not gps:
                        return None
                    
                    # Ищем поле которое содержит эту точку
                    with db_connection():
                        for field in Field.select():
                            field_geom = wkt_loads(field.geometry_wkt)
                            point = box(gps.longitude, gps.latitude, 
                                       gps.longitude, gps.latitude)
                            
                            if field_geom.contains(point) or field_geom.intersects(point):
                                return field.id
                        
        except Exception as e:
            from src.services.orthomosaic_service import logger
            logger.error(f"Ошибка определения поля по GPS: {e}")
        
        return None


class CropClassificationHandler(tornado.web.RequestHandler):
    """Handler для классификации культуры по ортомозаике."""

    def get(self, scan_id: int) -> None:
        """
        Определяет тип культуры по загруженной ортомозаике.
        
        Args:
            scan_id: ID скана
        """
        try:
            with db_connection():
                scan = FieldScan.get_by_id(scan_id)
                
                if not scan.file_path or not os.path.exists(scan.file_path):
                    self.set_status(404)
                    self.write({"error": "Файл скана не найден"})
                    return

                # Классифицируем
                acquisition_date = None
                if scan.uploaded_at:
                    acquisition_date = scan.uploaded_at

                result = classify_from_orthomosaic(
                    scan.file_path,
                    acquisition_date=acquisition_date
                )

                # Сохраняем результат в БД
                if result.get("crop_type"):
                    scan.crop_type = result["crop_type"]
                    scan.crop_confidence = result["confidence"]
                    scan.save()

                self.write({
                    "scan_id": scan_id,
                    "crop_type": result.get("crop_type"),
                    "confidence": result.get("confidence", 0),
                    "details": result.get("details", {}),
                    "ndvi_stats": result.get("ndvi_stats", {})
                })

        except FieldScan.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Скан не найден"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class OrthomosaicStatusHandler(tornado.web.RequestHandler):
    """Handler для получения статуса обработки ортомозаики."""

    def get(self, task_id: str) -> None:
        """Получает статус задачи обработки."""
        try:
            result = huey.result(task_id)
            
            if result is None:
                self.write({
                    "task_id": task_id,
                    "status": "processing",
                    "message": "Ортомозаика обрабатывается",
                    "progress": "Склейка снимков..."
                })
            elif isinstance(result, dict) and result.get("error"):
                self.write({
                    "task_id": task_id,
                    "status": "error",
                    "error": result.get("error")
                })
            else:
                self.write({
                    "task_id": task_id,
                    "status": "completed",
                    "result": result
                })
                
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
