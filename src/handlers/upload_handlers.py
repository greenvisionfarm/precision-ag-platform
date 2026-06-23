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
from shapely.validation import make_valid

from db import database
from src.models.field import Field, FieldScan
from src.tasks import huey, process_geotiff_task
from src.utils.db_utils import db_connection
from src.services.isoxml_service import export_isoxml
from src.middleware.auth import AuthenticatedRequestHandler
from src.constants import UPLOAD_DIR

logger = logging.getLogger(__name__)


class TaskStatusHandler(AuthenticatedRequestHandler):
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
            elif isinstance(result, dict):
                if result.get("success", True):
                    self.write({
                        "task_id": task_id,
                        "status": "completed",
                        "message": "Обработка завершена успешно",
                        "result": result
                    })
                else:
                    self.write({
                        "task_id": task_id,
                        "status": "error",
                        "message": result.get("error", "Ошибка при обработке"),
                        "result": result
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


def process_geotiff_file(request_files, upload_dir: str, company_id: Optional[int] = None) -> dict:
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

        # Ищем поле компании, которое пересекается с этим растром
        with db_connection():
            target_field: Optional[Field] = None
            query = Field.select()
            if company_id is not None:
                query = query.where(Field.company_id == company_id)
            for field in query:
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


class RasterUploadHandler(AuthenticatedRequestHandler):
    """Handler для загрузки растровых файлов (GeoTIFF/NDVI) через API."""

    def post(self) -> None:
        user = self.current_user
        if not user:
            self.set_status(401)
            self.write({"error": "Требуется авторизация"})
            return

        if 'raster_file' not in self.request.files:
            self.set_status(400)
            self.write({"error": "Отсутствует файл"})
            return

        try:
            result = process_geotiff_file(self.request.files, UPLOAD_DIR, self.current_user.company_id)
            self.write(result)
        except Exception as e:
            logger.error(f"Error processing raster upload: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class UploadHandler(AuthenticatedRequestHandler):
    """Handler для загрузки файлов."""

    def post(self) -> None:
        user = self.current_user
        if not user:
            self.set_status(401)
            self.write({"error": "Требуется авторизация"})
            return

        file_types = list(self.request.files.keys())
        logger.info(f"Upload from user={user.id}, company={user.company_id}, files={file_types}")

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
            logger.info(f"Shapefile upload: filename={uploaded_file['filename']}, size={len(uploaded_file['body'])} bytes, company={company_id}")
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
                    logger.error(f"No .shp found in archive. Files in zip: {os.listdir(tmpdir)}")
                    raise ValueError("No SHP")
                shp_dir = os.path.dirname(shp_file)
                shp_base = os.path.splitext(shp_file)[0]
                cpg_file = os.path.join(shp_dir, shp_base + '.cpg')
                encoding = 'utf-8'
                if os.path.exists(cpg_file):
                    with open(cpg_file, 'r') as cf:
                        encoding = cf.read().strip().lower()
                logger.info(f"Reading shapefile: {os.path.basename(shp_file)}, encoding={encoding}")
                gdf = gpd.read_file(shp_file, encoding=encoding).to_crs(epsg=4326)
                gdf_proj = gdf.to_crs(epsg=3035)
                gdf['area_sq_m'] = gdf_proj.geometry.area

            features = []
            for _, row in gdf.iterrows():
                props = row.drop('geometry').to_dict()
                cleaned: Dict[str, Any] = {
                    k: (None if isinstance(v, float) and math.isnan(v) else v)
                    for k, v in props.items()
                }
                field_name = (
                    cleaned.get('Field_Name') or cleaned.get('name') or
                    cleaned.get('NAME') or cleaned.get('Name') or
                    cleaned.get('Field_Name_') or cleaned.get('field_name') or
                    "Поле"
                )
                if field_name and str(field_name).isdigit():
                    field_name = f"Поле {field_name}"
                geom = row.geometry
                if not geom.is_valid:
                    geom = make_valid(geom)
                if geom.geom_type == 'MultiPolygon' and len(geom.geoms) == 1:
                    geom = geom.geoms[0]
                features.append({
                    "name": str(field_name),
                    "geometry_wkt": geom.wkt,
                    "properties": cleaned,
                    "area_ha": round(row['area_sq_m'] / 10000, 2) if 'area_sq_m' in row.index else 0
                })
            logger.info(f"Shapefile parsed: {len(features)} features, columns={list(gdf.columns)}, names={[f['name'] for f in features]}")
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({"features": features}))
        except Exception as e:
            logger.error(f"Error processing shapefile: {e}")
            self.set_status(500)
            self.write({"error": str(e)})

    def handle_geotiff(self) -> None:
        try:
            result = process_geotiff_file(self.request.files, UPLOAD_DIR, self.current_user.company_id)
            self.write(result)
        except Exception as e:
            logger.error(f"Error processing geotiff: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class ConfirmShapefileImportHandler(AuthenticatedRequestHandler):
    """Handler для подтверждения импорта Shapefile — сохранение отредактированных полей."""

    def post(self) -> None:
        user = self.current_user
        if not user:
            self.set_status(401)
            self.write({"error": "Требуется авторизация"})
            return

        try:
            from shapely.wkt import loads as wkt_loads
            data = json.loads(self.request.body)
            features = data.get("features", [])
            logger.info(f"Confirm import: user={user.id}, company={user.company_id}, features_count={len(features)}")
            if not features:
                self.set_status(400)
                self.write({"error": "Нет полей для сохранения"})
                return

            created = []
            skipped_names = []
            with db_connection():
                existing_geoms = [
                    wkt_loads(f.geometry_wkt)
                    for f in Field.select(Field.geometry_wkt).where(Field.company == user.company_id)
                ]
                logger.info(f"Existing fields with geometry: {len(existing_geoms)}")
                with database.atomic():
                    for feat in features:
                        geom_wkt = feat.get("geometry_wkt")
                        if not geom_wkt:
                            skipped_names.append(feat.get('name', '?') + ' (no geometry)')
                            continue
                        new_poly = wkt_loads(geom_wkt)
                        is_dupe = False
                        for existing_poly in existing_geoms:
                            if new_poly.intersects(existing_poly):
                                intersection_area = new_poly.intersection(existing_poly).area
                                union_area = new_poly.union(existing_poly).area
                                if union_area > 0 and intersection_area / union_area > 0.9:
                                    is_dupe = True
                                    break
                        if is_dupe:
                            skipped_names.append(feat.get('name', '?') + ' (geometry dupe)')
                            continue
                        name = feat.get("name", "Поле")
                        props = feat.get("properties", {})
                        area_ha = feat.get("area_ha", 0)
                        props["area_sq_m"] = area_ha * 10000
                        f = Field.create(
                            name=str(name),
                            geometry_wkt=geom_wkt,
                            properties_json=json.dumps(props),
                            company_id=user.company_id
                        )
                        created.append(f.id)
                        existing_geoms.append(new_poly)
                        logger.info(f"Created field: id={f.id}, name={name}")
            skipped = len(features) - len(created)
            msg = f"Создано полей: {len(created)}"
            if skipped:
                msg += f", пропущено (дубли геометрии): {skipped}"
            logger.info(f"Import result: created={len(created)}, skipped={skipped}, skipped_names={skipped_names}")
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({"message": msg, "ids": created, "skipped": skipped}))
        except Exception as e:
            logger.error(f"Error confirming shapefile import: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class ISOXMLExportHandler(AuthenticatedRequestHandler):
    """Handler для экспорта поля в формате ISOXML."""

    SUPPORTED_METHODS = ("GET", "POST")

    def get(self, field_id: int) -> None:
        self._export(field_id)

    def post(self, field_id: int) -> None:
        self._export(field_id)

    def _export(self, field_id: int) -> None:
        try:
            field = (
                Field.select()
                .where((Field.id == field_id) & (Field.company == self.current_user.company))
                .first()
            )
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено"})
                return

            from db import FieldZone
            zones_count = FieldZone.select().where(FieldZone.field == field).count()
            if zones_count == 0:
                self.set_status(404)
                self.write({"error": "Нет зон для экспорта"})
                return

            # Опциональные параметры продукта из POST body
            product_name = None
            product_type = None
            if self.request.method == 'POST':
                try:
                    import json
                    body = json.loads(self.request.body)
                    product_name = body.get('product_name')
                    product_type = body.get('product_type')
                except (json.JSONDecodeError, TypeError):
                    pass

            filename = f"field_{field_id}_isoxml.xml"
            output_path = os.path.join(UPLOAD_DIR, filename)

            export_isoxml(field_id, output_path, product_name=product_name, product_type=product_type)

            self.set_header('Content-Type', 'application/xml')
            self.set_header('Content-Disposition', f'attachment; filename="{filename}"')

            with open(output_path, 'rb') as f:
                self.write(f.read())

            os.remove(output_path)

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class TaskDataExportHandler(AuthenticatedRequestHandler):
    """Handler для экспорта поля в формате TaskData.zip (ISO 11783 v3.3)."""

    SUPPORTED_METHODS = ("GET", "POST")

    def get(self, field_id: int) -> None:
        self._export(field_id)

    def post(self, field_id: int) -> None:
        self._export(field_id)

    def _export(self, field_id: int) -> None:
        try:
            from src.services.taskdata_service import export_taskdata

            field = (
                Field.select()
                .where((Field.id == field_id) & (Field.company == self.current_user.company))
                .first()
            )
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено"})
                return

            from db import FieldZone
            zones_count = FieldZone.select().where(FieldZone.field == field).count()
            if zones_count == 0:
                self.set_status(404)
                self.write({"error": "Нет зон для экспорта"})
                return

            product_name = None
            farm_name = None
            resolution = 2.0
            rate_mode = "variable"
            constant_rate = None
            rate_min = None
            rate_max = None
            nutrient = "nitrogen"
            application_date = None
            residual_pct = 1.0
            product_group = "mineral"
            if self.request.method == 'POST':
                try:
                    import json
                    body = json.loads(self.request.body)
                    product_name = body.get('product_name')
                    farm_name = body.get('farm_name')
                    resolution = float(body.get('resolution', 2.0))
                    rate_mode = body.get('rate_mode', 'variable')
                    constant_rate = body.get('constant_rate')
                    rate_min = body.get('rate_min')
                    rate_max = body.get('rate_max')
                    nutrient = body.get('nutrient', 'nitrogen')
                    application_date = body.get('application_date')
                    residual_pct = float(body.get('residual_pct', 1.0))
                    product_group = body.get('product_group', 'mineral')
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            filename = f"field_{field_id}_taskdata.zip"
            output_path = os.path.join(UPLOAD_DIR, filename)

            export_taskdata(
                field_id, output_path,
                product_name=product_name,
                resolution_m=resolution,
                farm_name=farm_name,
                rate_mode=rate_mode,
                constant_rate=constant_rate,
                rate_min=rate_min,
                rate_max=rate_max,
                nutrient=nutrient,
                application_date=application_date,
                residual_pct=residual_pct,
                product_group=product_group,
            )

            self.set_header('Content-Type', 'application/zip')
            self.set_header('Content-Disposition', f'attachment; filename="{filename}"')

            with open(output_path, 'rb') as f:
                self.write(f.read())

            os.remove(output_path)

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldScansHandler(AuthenticatedRequestHandler):
    """Handler для получения списка сканов поля."""

    def get(self, field_id: int) -> None:
        try:
            from db import FieldScan

            field = (
                Field.select()
                .where((Field.id == field_id) & (Field.company == self.current_user.company))
                .first()
            )
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено"})
                return

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

            field = (
                Field.select()
                .where((Field.id == field_id) & (Field.company == self.current_user.company))
                .first()
            )
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено"})
                return

            scan = FieldScan.get_or_none(
                (FieldScan.id == scan_id) & (FieldScan.field == field)
            )
            if not scan:
                self.set_status(404)
                self.write({"error": "Скан не найден"})
                return

            zones_count = FieldZone.delete().where(FieldZone.scan == scan).execute()

            if scan.file_path and os.path.exists(scan.file_path):
                os.remove(scan.file_path)

            scan_id_deleted = scan.id
            scan.delete_instance()

            self.write({
                "success": True,
                "message": f"Скан {scan_id_deleted} удалён",
                "deleted_zones": zones_count
            })

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldScanZonesHandler(AuthenticatedRequestHandler):
    """Handler для получения зон конкретного скана."""

    def get(self, scan_id: int) -> None:
        try:
            from db import FieldScan, FieldZone
            from shapely.wkt import loads as wkt_loads
            from shapely.geometry import mapping

            scan = FieldScan.get_by_id(scan_id)

            # Проверяем что скан принадлежит компании пользователя
            field = Field.get_by_id(scan.field_id)
            if field.company_id != self.current_user.company_id:
                self.set_status(403)
                self.write({"error": "Доступ запрещён"})
                return

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


class ScanCropUpdateHandler(AuthenticatedRequestHandler):
    """Handler для ручного обновления типа культуры скана."""

    def post(self, scan_id: int) -> None:
        try:
            from db import FieldScan
            from src.services.crop_classifier import CROP_PROFILES, CropType

            body = json.loads(self.request.body)
            new_crop = body.get('crop_type')

            if not new_crop:
                self.set_status(400)
                self.write({"error": "crop_type is required"})
                return

            scan = FieldScan.get_by_id(scan_id)

            # Проверяем что скан принадлежит компании пользователя
            field = Field.get_by_id(scan.field_id)
            if field.company_id != self.current_user.company_id:
                self.set_status(403)
                self.write({"error": "Доступ запрещён"})
                return

            scan.crop_type = new_crop
            scan.crop_confidence = 1.0
            scan.save()

            # Получаем дефолтные нормы для этой культуры
            default_rates = [150, 250, 350]
            try:
                crop_enum = CropType(new_crop)
                if crop_enum in CROP_PROFILES:
                    default_rates = CROP_PROFILES[crop_enum].default_rates
            except Exception:
                pass

            self.write({
                "success": True,
                "crop_type": new_crop,
                "default_rates": default_rates
            })

        except FieldScan.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Скан не найден"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class ScanDateUpdateHandler(AuthenticatedRequestHandler):
    """Handler для обновления даты съёмки скана."""

    def post(self, scan_id: int) -> None:
        try:
            body = json.loads(self.request.body)
            flight_date_str = body.get("flight_date")

            if not flight_date_str:
                self.set_status(400)
                self.write({"error": "flight_date is required"})
                return

            from datetime import datetime as dt
            try:
                flight_date = dt.fromisoformat(flight_date_str)
            except ValueError:
                self.set_status(400)
                self.write({"error": "Неверный формат даты"})
                return

            scan = FieldScan.get_by_id(scan_id)
            field = Field.get_by_id(scan.field_id)
            if field.company_id != self.current_user.company_id:
                self.set_status(403)
                self.write({"error": "Доступ запрещён"})
                return

            scan.uploaded_at = flight_date
            scan.save()

            self.write({
                "success": True,
                "uploaded_at": scan.uploaded_at.isoformat()
            })

        except FieldScan.DoesNotExist:
            self.set_status(404)
            self.write({"error": "Скан не найден"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

class CropsMetadataHandler(AuthenticatedRequestHandler):
    """Handler для получения списка доступных культур и их названий."""

    def get(self) -> None:
        from src.services.crop_classifier import CROP_PROFILES
        
        names = {
            'wheat': 'Пшеница',
            'corn': 'Кукуруза',
            'sunflower': 'Подсолнечник',
            'soybean': 'Соя',
            'rapeseed': 'Рапс',
            'barley': 'Ячмень',
            'oats': 'Овес',
            'sugar_beet': 'Сахарная свекла',
            'potato': 'Картофель',
            'vegetables': 'Овощи',
            'grass': 'Трава/Сено',
            'unknown': 'Не определено'
        }
        
        result = [
            {"id": crop.value, "name": names.get(crop.value, crop.value)}
            for crop in CROP_PROFILES.keys()
        ]
        
        self.write({"crops": result})


class ScanMergeHandler(AuthenticatedRequestHandler):
    """Handler для объединения двух сканов в один (кейс: замена батареи дрона)."""

    def post(self, field_id: int) -> None:
        try:
            data = json.loads(self.request.body)
            scan_id_from = data.get("scan_id_from")
            scan_id_to = data.get("scan_id_to")

            if not scan_id_from or not scan_id_to:
                self.set_status(400)
                self.write({"error": "Требуются scan_id_from и scan_id_to"})
                return

            if scan_id_from == scan_id_to:
                self.set_status(400)
                self.write({"error": "Нельзя объединить скан с самим собой"})
                return

            field = (
                Field.select()
                .where((Field.id == field_id) & (Field.company == self.current_user.company))
                .first()
            )
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено"})
                return

            scan_from = FieldScan.get_or_none(
                (FieldScan.id == scan_id_from) & (FieldScan.field == field)
            )
            scan_to = FieldScan.get_or_none(
                (FieldScan.id == scan_id_to) & (FieldScan.field == field)
            )

            if not scan_from or not scan_to:
                self.set_status(404)
                self.write({"error": "Один из сканов не найден"})
                return

            from db import FieldZone

            zones_moved = FieldZone.update(scan=scan_to).where(FieldZone.scan == scan_from).execute()

            merged_zones_count = FieldZone.select().where(FieldZone.scan == scan_to).count()

            scan_from.delete_instance()

            self.write({
                "success": True,
                "message": f"Сканы объединены. Перенесено зон: {zones_moved}. Итого зон: {merged_zones_count}",
                "zones_moved": zones_moved,
                "merged_zones_count": merged_zones_count,
                "scan_id": scan_to.id,
            })

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
