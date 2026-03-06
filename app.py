import tornado.ioloop
import tornado.web
import geopandas as gpd
import os
import zipfile
import tempfile
import shutil
import json
import logging
import math
from shapely.geometry import mapping, shape
from shapely.wkt import loads as wkt_loads

from db import initialize_db, database, Field

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация базы данных при старте приложения
initialize_db()
logging.info("База данных инициализирована.")

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        logging.info("Запрос главной страницы.")
        self.render("index.html")

class FieldsListPageHandler(tornado.web.RequestHandler):
    def get(self):
        logging.info("Запрос страницы со списком полей.")
        self.render("fields_list.html")

class FieldsApiHandler(tornado.web.RequestHandler):
    def get(self):
        logging.info("Запрос данных полей через API (GeoJSON).")
        self.set_header("Content-Type", "application/json")
        try:
            if database.is_closed():
                database.connect()
            
            fields_from_db = Field.select()

            features = []
            for field in fields_from_db:
                geom = wkt_loads(field.geometry_wkt)
                properties = json.loads(field.properties_json) if field.properties_json else {}
                properties['db_id'] = field.id # Добавляем ID из БД в свойства для фронтенда
                if field.name:
                    properties['name'] = field.name

                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": properties
                })

            geojson_data = {
                "type": "FeatureCollection",
                "features": features
            }
            logging.info(f"Отправлено {len(features)} полей в формате GeoJSON.")
            self.write(json.dumps(geojson_data))

        except Exception as e:
            logging.error("Ошибка при получении данных полей из БД (GeoJSON):", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class FieldsDataApiHandler(tornado.web.RequestHandler):
    def get(self):
        logging.info("Запрос данных полей через API (для таблицы).")
        self.set_header("Content-Type", "application/json")
        try:
            if database.is_closed():
                database.connect()
            
            fields_from_db = Field.select()

            data = []
            for field in fields_from_db:
                properties = json.loads(field.properties_json) if field.properties_json else {}
                
                row_data = {
                    "id": field.id,
                    "name": field.name if field.name else "N/A",
                    "area": f"{properties.get('area_sq_m', 0) / 10000:.2f} га" if isinstance(properties.get('area_sq_m'), (int, float)) else "N/A",
                    "owner": properties.get('owner', 'N/A'),
                    "properties": json.dumps(properties)
                }
                data.append(row_data)

            logging.info(f"Отправлено {len(data)} полей для таблицы.")
            self.write(json.dumps({"data": data}))

        except Exception as e:
            logging.error("Ошибка при получении данных полей из БД (для таблицы):", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class FieldDeleteHandler(tornado.web.RequestHandler):
    def delete(self, field_id):
        logging.info(f"Получен запрос на удаление поля с ID: {field_id}")
        try:
            if database.is_closed():
                database.connect()
            
            field_to_delete = Field.get_or_none(Field.id == field_id)
            if field_to_delete:
                field_to_delete.delete_instance()
                logging.info(f"Поле с ID {field_id} успешно удалено.")
                self.set_status(200)
                self.write({"message": f"Поле с ID {field_id} успешно удалено."})
            else:
                logging.warning(f"Поле с ID {field_id} не найдено для удаления.")
                self.set_status(404)
                self.write({"error": f"Поле с ID {field_id} не найдено."})

        except Exception as e:
            logging.error(f"Ошибка при удалении поля с ID {field_id}:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info("Получен запрос на загрузку файла.")
        try:
            uploaded_file = self.request.files['shapefile_zip'][0]
            original_filename = uploaded_file['filename']
            file_body = uploaded_file['body']
            logging.info(f"Получен файл: {original_filename}")

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, original_filename)
                with open(zip_path, 'wb') as f:
                    f.write(file_body)
                logging.info(f"ZIP-файл сохранен во временную директорию: {zip_path}")

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                logging.info(f"ZIP-файл '{original_filename}' успешно распакован в '{tmpdir}'.")

                shp_file = None
                for root, _, files in os.walk(tmpdir):
                    for f in files:
                        if f.endswith('.shp'):
                            shp_file = os.path.join(root, f)
                            break
                    if shp_file:
                        break

                if not shp_file:
                    raise ValueError("В ZIP-архиве не найден .shp файл.")
                logging.info(f"Найден .shp файл: {shp_file}")

                gdf = gpd.read_file(shp_file)
                gdf_wgs84 = gdf.to_crs(epsg=4326)
                logging.info(f"Shapefile прочитан и перепроецирован в WGS84. Найдено {len(gdf_wgs84)} объектов.")

                gdf_projected_for_area = gdf_wgs84.to_crs(epsg=3857)
                gdf_wgs84['area_sq_m'] = gdf_projected_for_area.geometry.area
                logging.info(f"Площади полей рассчитаны в EPSG:3857.")

            if database.is_closed():
                database.connect()
            
            with database.atomic():
                # Field.delete().execute() # Раскомментировать, если нужно очищать БД при каждой загрузке

                for _, row in gdf_wgs84.iterrows():
                    geom_wkt = row.geometry.wkt
                    
                    properties = row.drop('geometry').to_dict()
                    cleaned_properties = {}
                    for key, value in properties.items():
                        if isinstance(value, float) and math.isnan(value):
                            cleaned_properties[key] = None
                        else:
                            cleaned_properties[key] = value
                    properties_json = json.dumps(cleaned_properties)

                    field_name = properties.get('name') or properties.get('NAME') or properties.get('ID')
                    if isinstance(field_name, (int, float)):
                        field_name = str(field_name)
                    
                    Field.create(
                        name=field_name,
                        geometry_wkt=geom_wkt,
                        properties_json=properties_json
                    )
            logging.info(f"Все {len(gdf_wgs84)} полей успешно сохранены в БД.")
            
            self.set_status(200)
            self.write({"message": "Файлы успешно загружены и данные сохранены в БД."})

        except Exception as e:
            logging.error("Ошибка при обработке загрузки файла:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()


def make_app():
    settings = {
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "debug": True,
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/fields_list", FieldsListPageHandler),
        (r"/api/fields", FieldsApiHandler),
        (r"/api/fields_data", FieldsDataApiHandler),
        (r"/api/field/delete/([0-9]+)", FieldDeleteHandler), # Новый маршрут для удаления
        (r"/upload", UploadHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
    ], **settings)

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    logging.info("Сервер запущен. Откройте http://localhost:8888 в вашем браузере.")
    tornado.ioloop.IOLoop.current().start()
