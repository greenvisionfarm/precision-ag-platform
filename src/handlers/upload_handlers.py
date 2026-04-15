"""
Handlers для загрузки файлов (Shapefile, GeoTIFF).
"""
import json
import logging
import math
import os
import tempfile
import uuid
import zipfile
from typing import Any, Dict, Optional

import geopandas as gpd
import numpy as np
import rasterio
import tornado.web

from db import Field, FieldScan, database
from src.tasks import huey, process_geotiff_task
from src.utils.db_utils import db_connection
from src.services.isoxml_service import export_isoxml
from src.utils.auth import get_current_user_from_token

logger = logging.getLogger(__name__)

# Используем абсолютный путь для загрузок
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


class TaskStatusHandler(tornado.web.RequestHandler):
    """Handler для получения статуса фоновой задачи."""
    
    def get(self, task_id: str) -> None:
        try:
            result = huey.result(task_id)
            if result is None:
                self.write({
                    "task_id": task_id,
                    "status": "pending",
                    "message": "Задача обрабатывается"
                })
            elif result is False:
                self.write({
                    "task_id": task_id,
                    "status": "error",
                    "message": "Ошибка при обработке"
                })
            else:
                self.write({
                    "task_id": task_id,
                    "status": "completed",
                    "message": "Обработка завершена успешно"
                })
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


def process_geotiff_file(request_files, upload_dir: str) -> dict:
    """
    Общая логика обработки GeoTIFF файла.
    Используется обоими handlers.
    """
    from datetime import datetime
    from shapely import wkt
    from shapely.geometry import box

    uploaded_file = request_files['raster_file'][0]

    # Сохраняем файл в папку uploads с уникальным именем
    file_ext = os.path.splitext(uploaded_file['filename'])[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, 'wb') as f:
        f.write(uploaded_file['body'])

    try:
        with rasterio.open(file_path) as src:
            # Определяем границы растра
            bounds = src.bounds
            raster_box = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

            # Статистика NDVI
            data = src.read(1)
            valid_data = data[(data > -1.0) & (data <= 1.0) & (data != 0)]
            ndvi_min = float(np.min(valid_data)) if len(valid_data) > 0 else None
            ndvi_max = float(np.max(valid_data)) if len(valid_data) > 0 else None
            ndvi_avg = float(np.mean(valid_data)) if len(valid_data) > 0 else None

        # Ищем поле, которое пересекается с этим растром
        with db_connection():
            target_field: Optional[Field] = None
            for field in Field.select():
                field_geom = wkt.loads(field.geometry_wkt)
                if field_geom.intersects(raster_box):
                    target_field = field
                    break

            if not target_field:
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise ValueError("Не найдено поле, соответствующее координатам этого растра")

            # Создаём запись скана
            scan = FieldScan.create(
                field=target_field,
                file_path=file_path,
                filename=uploaded_file['filename'],
                uploaded_at=datetime.now(),
                ndvi_min=ndvi_min,
                ndvi_max=ndvi_max,
                ndvi_avg=ndvi_avg,
                processed='false',
                task_id=None
            )

            # Запускаем фоновую задачу
            task = process_geotiff_task(file_path, target_field.id, scan.id)

            # Обновляем task_id
            scan.task_id = task.id
            scan.save()

        return {
            "message": f"Файл принят. Обработка NDVI для поля '{target_field.name}' запущена в фоне.",
            "task_id": task.id,
            "field_id": target_field.id,
            "scan_id": scan.id
        }

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


class RasterUploadHandler(tornado.web.RequestHandler):
    """Handler для загрузки растровых файлов (GeoTIFF/NDVI) через API."""

    def get_current_user(self):
        """Получает текущий пользователь из cookie."""
        token = self.get_secure_cookie('session_token')
        if not token:
            return None
        try:
            return get_current_user_from_token(token.decode('utf-8'))
        except Exception:
            return None

    def post(self) -> None:
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({"error": "Требуется авторизация"})
            return

        if 'raster_file' not in self.request.files:
            self.set_status(400)
            self.write({"error": "Отсутствует файл"})
            return

        try:
            result = process_geotiff_file(self.request.files, UPLOAD_DIR)
            self.write(result)
        except Exception as e:
            logger.error(f"Error processing raster upload: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class UploadHandler(tornado.web.RequestHandler):
    """Handler для загрузки файлов."""

    def get_current_user(self):
        """Получает текущего пользователя из cookie."""
        token = self.get_secure_cookie('session_token')
        if not token:
            return None
        try:
            return get_current_user_from_token(token.decode('utf-8'))
        except Exception:
            return None

    def post(self) -> None:
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({"error": "Требуется авторизация"})
            return

        # 1. Обработка Shapefile
        if 'shapefile_zip' in self.request.files:
            return self.handle_shapefile(user.company_id)

        # 2. Обработка GeoTIFF (новая асинхронная логика)
        elif 'raster_file' in self.request.files:
            return self.handle_geotiff()

        else:
            self.set_status(400)
            self.write({"error": "No file provided"})

    def handle_shapefile(self, company_id: int) -> None:
        try:
            uploaded_file = self.request.files['shapefile_zip'][0]
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "up.zip")
                with open(zip_path, 'wb') as f:
                    f.write(uploaded_file['body'])
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                shp_file = next(
                    (os.path.join(r, f) for r, _, fs in os.walk(tmpdir) for f in fs if f.endswith('.shp')),
                    None
                )
                if not shp_file:
                    raise ValueError("No SHP")
                gdf = gpd.read_file(shp_file).to_crs(epsg=4326)
                gdf_proj = gdf.to_crs(epsg=3035)
                gdf['area_sq_m'] = gdf_proj.geometry.area

            with db_connection():
                with database.atomic():
                    for _, row in gdf.iterrows():
                        props = row.drop('geometry').to_dict()
                        cleaned: Dict[str, Any] = {
                            k: (None if isinstance(v, float) and math.isnan(v) else v)
                            for k, v in props.items()
                        }
                        field_name = (
                            cleaned.get('Field_Name') or cleaned.get('name') or
                            cleaned.get('NAME') or cleaned.get('Name') or
                            cleaned.get('id') or cleaned.get('ID') or "Поле"
                        )
                        Field.create(
                            name=str(field_name),
                            geometry_wkt=row.geometry.wkt,
                            properties_json=json.dumps(cleaned),
                            company_id=company_id
                        )
            self.write({"message": "Shapefile uploaded and processed"})
        except Exception as e:
            logger.error(f"Error processing shapefile: {e}")
            self.set_status(500)
            self.write({"error": str(e)})

    def handle_geotiff(self) -> None:
        try:
            result = process_geotiff_file(self.request.files, UPLOAD_DIR)
            self.write(result)
        except Exception as e:
            logger.error(f"Error processing geotiff: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class ISOXMLExportHandler(tornado.web.RequestHandler):
    """Handler для экспорта поля в формате ISOXML."""

    def get(self, field_id: int) -> None:
        try:
            # Проверяем что поле существует
            field = Field.get_by_id(field_id)
            
            # Проверяем что есть зоны
            from db import FieldZone
            zones_count = FieldZone.select().where(FieldZone.field == field).count()
            if zones_count == 0:
                self.set_status(404)
                self.write({"error": "Нет зон для экспорта"})
                return
            
            # Генерируем имя файла
            filename = f"field_{field_id}_isoxml.xml"
            output_path = os.path.join(UPLOAD_DIR, filename)
            
            # Экспортируем
            export_isoxml(field_id, output_path)
            
            # Отправляем файл
            self.set_header('Content-Type', 'application/xml')
            self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
            
            with open(output_path, 'rb') as f:
                self.write(f.read())
            
            # Удаляем временный файл
            os.remove(output_path)
            
        except Field.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Поле не найдено"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldScansHandler(tornado.web.RequestHandler):
    """Handler для получения списка сканов поля."""

    def get(self, field_id: int) -> None:
        try:
            from db import FieldScan

            # Проверяем что поле существует
            Field.get_by_id(field_id)

            # Получаем все сканы поля
            scans = FieldScan.select().where(
                FieldScan.field == field_id
            ).order_by(FieldScan.uploaded_at.desc())

            result = []
            from src.services.crop_classifier import CROP_PROFILES, CropType

            for scan in scans:
                # Получаем дефолтные нормы для культуры, если она определена
                default_rates = []
                if scan.crop_type:
                    try:
                        crop_enum = CropType(scan.crop_type)
                        if crop_enum in CROP_PROFILES:
                            default_rates = CROP_PROFILES[crop_enum].default_rates
                    except (ValueError, KeyError):
                        pass

                result.append({
                    "id": scan.id,
                    "filename": scan.filename,
                    "uploaded_at": scan.uploaded_at.isoformat(),
                    "ndvi_min": scan.ndvi_min,
                    "ndvi_max": scan.ndvi_max,
                    "ndvi_avg": scan.ndvi_avg,
                    "processed": scan.processed == 'true',
                    "has_zones": scan.zones.count() > 0,
                    "zones_count": scan.zones.count(),
                    "crop_type": scan.crop_type,
                    "crop_confidence": getattr(scan, 'crop_confidence', 0),
                    "default_rates": default_rates
                })

            self.write({"scans": result})

        except Field.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Поле не найдено"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

    def delete(self, field_id: int, scan_id: int) -> None:
        """Удаление скана и всех его зон."""
        try:
            import os
            from db import FieldScan, FieldZone

            # Проверяем что поле существует
            Field.get_by_id(field_id)

            # Находим скан
            scan = FieldScan.get_or_none(FieldScan.id == scan_id)
            if not scan:
                self.set_status(404)
                self.write({"error": "Скан не найден"})
                return

            # Удаляем зоны скана
            zones_count = FieldZone.delete().where(FieldZone.scan == scan).execute()

            # Удаляем файл TIFF если существует
            if scan.file_path and os.path.exists(scan.file_path):
                os.remove(scan.file_path)

            # Удаляем скан
            scan_id_deleted = scan.id
            scan.delete_instance()

            self.write({
                "success": True,
                "message": f"Скан {scan_id_deleted} удалён",
                "deleted_zones": zones_count
            })

        except Field.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Поле не найдено"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldScanZonesHandler(tornado.web.RequestHandler):
    """Handler для получения зон конкретного скана."""

    def get(self, scan_id: int) -> None:
        try:
            from db import FieldScan, FieldZone
            from shapely.wkt import loads as wkt_loads
            from shapely.geometry import mapping

            scan = FieldScan.get_by_id(scan_id)

            # Получаем зоны этого скана
            zones = FieldZone.select().where(FieldZone.scan == scan)

            result = []
            for zone in zones:
                # Конвертируем WKT в GeoJSON
                geometry = mapping(wkt_loads(zone.geometry_wkt)) if zone.geometry_wkt else None
                
                result.append({
                    "id": zone.id,
                    "name": zone.name,
                    "avg_ndvi": zone.avg_ndvi,
                    "color": zone.color,
                    "geometry": geometry
                })

            self.write({"zones": result})

        except FieldScan.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Скан не найден"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class ScanCropUpdateHandler(tornado.web.RequestHandler):
    """Handler для обновления типа культуры скана вручную."""

    def post(self, scan_id: int) -> None:
        try:
            from db import FieldScan
            import json

            data = json.loads(self.request.body)
            crop_type = data.get("crop_type")

            if not crop_type:
                self.set_status(400)
                self.write({"error": "Тип культуры не указан"})
                return

            from src.utils.db_utils import db_connection
            with db_connection():
                scan = FieldScan.get_by_id(scan_id)
                scan.crop_type = crop_type
                scan.crop_confidence = 1.0  # Устанавливаем 100% уверенность при ручном вводе
                scan.save()

            # Получаем новые дефолтные нормы
            from src.services.crop_classifier import CROP_PROFILES, CropType
            default_rates = []
            try:
                crop_enum = CropType(crop_type)
                if crop_enum in CROP_PROFILES:
                    default_rates = CROP_PROFILES[crop_enum].default_rates
            except:
                pass

            self.write({
                "success": True,
                "message": f"Культура обновлена на {crop_type}",
                "default_rates": default_rates
            })

        except FieldScan.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Скан не найден"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
