"""
Handlers для загрузки файлов (Shapefile, GeoTIFF).
"""
import json
import math
import os
import tempfile
import uuid
import zipfile
from typing import Any, Dict, Optional

import geopandas as gpd
import rasterio
import tornado.web

from db import Field, database
from src.tasks import huey, process_geotiff_task
from src.utils.db_utils import db_connection

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


class UploadHandler(tornado.web.RequestHandler):
    """Handler для загрузки файлов."""
    
    def post(self) -> None:
        # 1. Обработка Shapefile
        if 'shapefile_zip' in self.request.files:
            return self.handle_shapefile()

        # 2. Обработка GeoTIFF (новая асинхронная логика)
        elif 'raster_file' in self.request.files:
            return self.handle_geotiff()

        else:
            self.set_status(400)
            self.write({"error": "No file provided"})

    def handle_shapefile(self) -> None:
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
                            properties_json=json.dumps(cleaned)
                        )
            self.write({"message": "Shapefile uploaded and processed"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

    def handle_geotiff(self) -> None:
        try:
            from shapely import wkt
            from shapely.geometry import box

            uploaded_file = self.request.files['raster_file'][0]

            # Сохраняем файл в папку uploads с уникальным именем
            file_ext = os.path.splitext(uploaded_file['filename'])[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(file_path, 'wb') as f:
                f.write(uploaded_file['body'])

            try:
                with rasterio.open(file_path) as src:
                    # Определяем границы растра
                    bounds = src.bounds
                    raster_box = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

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

                    # Запускаем фоновую задачу
                    task = process_geotiff_task(file_path, target_field.id)

                self.write({
                    "message": f"Файл принят. Обработка NDVI для поля '{target_field.name}' запущена в фоне.",
                    "task_id": task.id,
                    "field_id": target_field.id
                })

            except Exception as e:
                if os.path.exists(file_path): 
                    os.remove(file_path)
                raise

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
