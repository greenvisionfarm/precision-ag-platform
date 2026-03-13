import tornado.web
import json
import tempfile
import zipfile
import os
import math
import geopandas as gpd
import rasterio
from db import database, Field

class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        # 1. Обработка Shapefile (старая логика)
        if 'shapefile_zip' in self.request.files:
            return self.handle_shapefile()
        
        # 2. Обработка GeoTIFF (новая логика)
        elif 'raster_file' in self.request.files:
            return self.handle_geotiff()
        
        else:
            self.set_status(400)
            self.write({"error": "No file provided"})

    def handle_shapefile(self):
        try:
            uploaded_file = self.request.files['shapefile_zip'][0]
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "up.zip")
                with open(zip_path, 'wb') as f: f.write(uploaded_file['body'])
                with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(tmpdir)
                shp_file = next((os.path.join(r, f) for r, _, fs in os.walk(tmpdir) for f in fs if f.endswith('.shp')), None)
                if not shp_file: raise ValueError("No SHP")
                gdf = gpd.read_file(shp_file).to_crs(epsg=4326)
                gdf_proj = gdf.to_crs(epsg=3035)
                gdf['area_sq_m'] = gdf_proj.geometry.area
            
            if database.is_closed(): database.connect()
            with database.atomic():
                for _, row in gdf.iterrows():
                    props = row.drop('geometry').to_dict()
                    cleaned = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in props.items()}
                    field_name = cleaned.get('Field_Name') or cleaned.get('name') or \
                                 cleaned.get('NAME') or cleaned.get('Name') or \
                                 cleaned.get('id') or cleaned.get('ID') or "Поле"
                    Field.create(name=str(field_name), geometry_wkt=row.geometry.wkt, properties_json=json.dumps(cleaned))
            self.write({"message": "Shapefile uploaded and processed"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()

    def handle_geotiff(self):
        try:
            from src.services.raster_service import process_ndvi_zones
            from shapely import wkt
            from shapely.geometry import box
            
            uploaded_file = self.request.files['raster_file'][0]
            filename = uploaded_file['filename']
            
            # Сохраняем во временный файл для обработки
            with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
                tmp.write(uploaded_file['body'])
                tmp_path = tmp.name

            try:
                with rasterio.open(tmp_path) as src:
                    # Определяем границы растра
                    bounds = src.bounds
                    raster_box = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
                
                # Ищем поле, которое пересекается с этим растром
                if database.is_closed(): database.connect()
                
                target_field = None
                for field in Field.select():
                    field_geom = wkt.loads(field.geometry_wkt)
                    if field_geom.intersects(raster_box):
                        target_field = field
                        break
                
                if not target_field:
                    raise ValueError("Не найдено поле, соответствующее координатам этого растра")

                # Запускаем зонирование
                zones_data = process_ndvi_zones(tmp_path, target_field.geometry_wkt)
                
                if not zones_data:
                    raise ValueError("Не удалось выделить зоны (возможно, растр не пересекается с контуром поля)")

                # Сохраняем зоны в БД
                from db import FieldZone
                with database.atomic():
                    # Удаляем старые зоны этого поля перед обновлением
                    FieldZone.delete().where(FieldZone.field == target_field).execute()
                    
                    for z in zones_data:
                        FieldZone.create(
                            field=target_field,
                            name=z['name'],
                            geometry_wkt=z['geometry_wkt'],
                            avg_ndvi=z['avg_ndvi'],
                            color=z['color']
                        )

                self.write({
                    "message": f"Растр привязан к полю '{target_field.name}'. Выделено зон: {len(zones_data)}",
                    "field_id": target_field.id,
                    "zones_count": len(zones_data)
                })

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path) # Удаляем тяжелый оригинал после обработки
                    
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()
