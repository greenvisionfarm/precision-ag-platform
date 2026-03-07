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
from peewee import JOIN

from db import initialize_db, database, Field, Owner

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

class OwnersPageHandler(tornado.web.RequestHandler):
    def get(self):
        logging.info("Запрос страницы владельцев.")
        self.render("owners_list.html")

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
            
            # Предварительно загружаем владельцев, чтобы избежать N+1 проблемы
            fields_from_db = Field.select(Field, Owner).join(Owner, JOIN.LEFT_OUTER)

            data = []
            for field in fields_from_db:
                properties = json.loads(field.properties_json) if field.properties_json else {}
                
                row_data = {
                    "id": field.id,
                    "name": field.name if field.name else "N/A",
                    "area": f"{properties.get('area_sq_m', 0) / 10000:.2f} га" if isinstance(properties.get('area_sq_m'), (int, float)) else "N/A",
                    "owner": field.owner.name if field.owner else "N/A",
                    "owner_id": field.owner.id if field.owner else None,
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

class FieldRenameHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        logging.info(f"Получен запрос на переименование поля с ID: {field_id}")
        try:
            if database.is_closed():
                database.connect()
            
            field_to_rename = Field.get_or_none(Field.id == field_id)
            if not field_to_rename:
                logging.warning(f"Поле с ID {field_id} не найдено для переименования.")
                self.set_status(404)
                self.write({"error": f"Поле с ID {field_id} не найдено."})
                return

            try:
                request_data = json.loads(self.request.body)
                new_name = request_data.get('new_name')
            except json.JSONDecodeError:
                logging.error("Неверный формат JSON в запросе на переименование.")
                self.set_status(400)
                self.write({"error": "Неверный формат JSON."})
                return
            
            if not new_name:
                logging.warning("Новое имя поля не предоставлено.")
                self.set_status(400)
                self.write({"error": "Новое имя поля не может быть пустым."})
                return

            field_to_rename.name = new_name
            field_to_rename.save()
            logging.info(f"Поле с ID {field_id} успешно переименовано в '{new_name}'.")
            self.set_status(200)
            self.write({"message": f"Поле с ID {field_id} успешно переименовано."})

        except Exception as e:
            logging.error(f"Ошибка при переименовании поля с ID {field_id}:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class FieldAssignOwnerHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        logging.info(f"Получен запрос на назначение владельца для поля с ID: {field_id}")
        try:
            if database.is_closed():
                database.connect()
            
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено."})
                return

            request_data = json.loads(self.request.body)
            owner_id = request_data.get('owner_id')
            
            if owner_id == "" or owner_id is None:
                field.owner = None
            else:
                owner = Owner.get_or_none(Owner.id == owner_id)
                if not owner:
                    self.set_status(400)
                    self.write({"error": "Владелец не найден."})
                    return
                field.owner = owner
            
            field.save()
            logging.info(f"Владелец для поля {field_id} обновлен (owner_id: {owner_id}).")
            self.write({"message": "Владелец успешно обновлен."})
                
        except Exception as e:
            logging.error(f"Ошибка при назначении владельца:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class FieldAddHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info("Получен запрос на добавление нового поля вручную.")
        try:
            request_data = json.loads(self.request.body)
            geometry = request_data.get('geometry')
            name = request_data.get('name', 'Новое поле')

            if not geometry:
                self.set_status(400)
                self.write({"error": "Геометрия обязательна."})
                return

            # Превращаем GeoJSON в объект Shapely
            poly = shape(geometry)
            geom_wkt = poly.wkt

            # Расчет площади (переводим в EPSG:3857 для метров)
            # Для простоты создаем временный GeoDataFrame
            temp_gdf = gpd.GeoDataFrame([{'geometry': poly}], crs="EPSG:4326")
            temp_gdf_projected = temp_gdf.to_crs(epsg=3857)
            area_sq_m = temp_gdf_projected.geometry.area.iloc[0]

            properties = {
                "area_sq_m": area_sq_m,
                "source": "manual_draw"
            }

            if database.is_closed():
                database.connect()
            
            new_field = Field.create(
                name=name,
                geometry_wkt=geom_wkt,
                properties_json=json.dumps(properties)
            )

            logging.info(f"Создано новое поле ID {new_field.id} вручную.")
            self.write({
                "message": "Поле успешно добавлено.",
                "id": new_field.id
            })

        except Exception as e:
            logging.error("Ошибка при ручном добавлении поля:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class FieldUpdateGeometryHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        logging.info(f"Получен запрос на обновление геометрии поля с ID: {field_id}")
        try:
            if database.is_closed():
                database.connect()
            
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                self.write({"error": "Поле не найдено."})
                return

            request_data = json.loads(self.request.body)
            geometry = request_data.get('geometry')

            if not geometry:
                self.set_status(400)
                self.write({"error": "Геометрия обязательна."})
                return

            # Превращаем GeoJSON в объект Shapely и WKT
            poly = shape(geometry)
            geom_wkt = poly.wkt

            # Пересчет площади
            temp_gdf = gpd.GeoDataFrame([{'geometry': poly}], crs="EPSG:4326")
            temp_gdf_projected = temp_gdf.to_crs(epsg=3857)
            area_sq_m = temp_gdf_projected.geometry.area.iloc[0]

            # Обновляем свойства в JSON
            properties = json.loads(field.properties_json) if field.properties_json else {}
            properties['area_sq_m'] = area_sq_m
            
            field.geometry_wkt = geom_wkt
            field.properties_json = json.dumps(properties)
            field.save()

            logging.info(f"Геометрия поля ID {field_id} успешно обновлена. Новая площадь: {area_sq_m:.2f} кв.м.")
            self.write({"message": "Геометрия поля успешно обновлена."})

        except Exception as e:
            logging.error(f"Ошибка при обновлении геометрии поля {field_id}:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class OwnersDataApiHandler(tornado.web.RequestHandler):
    def get(self):
        logging.info("Запрос данных владельцев через API.")
        self.set_header("Content-Type", "application/json")
        try:
            if database.is_closed():
                database.connect()
            
            owners = Owner.select()
            data = [{"id": o.id, "name": o.name} for o in owners]
            
            self.write(json.dumps({"data": data}))
        except Exception as e:
            logging.error("Ошибка при получении владельцев:", exc_info=True)
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed():
                database.close()

class AddOwnerApiHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info("Запрос на добавление нового владельца.")
        try:
            if database.is_closed():
                database.connect()
            
            request_data = json.loads(self.request.body)
            owner_name = request_data.get('name')
            
            if not owner_name:
                self.set_status(400)
                self.write({"error": "Имя владельца обязательно."})
                return
            
            owner, created = Owner.get_or_create(name=owner_name)
            if created:
                logging.info(f"Создан новый владелец: {owner_name}")
                self.write({"message": f"Владелец '{owner_name}' успешно добавлен."})
            else:
                self.set_status(400)
                self.write({"error": f"Владелец '{owner_name}' уже существует."})
                
        except Exception as e:
            logging.error("Ошибка при добавлении владельца:", exc_info=True)
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

                    field_name = properties.get('Field_Name') or \
                                 properties.get('name') or \
                                 properties.get('NAME') or \
                                 properties.get('ID')
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
        (r"/owners", OwnersPageHandler),
        (r"/api/fields", FieldsApiHandler),
        (r"/api/fields_data", FieldsDataApiHandler),
        (r"/api/owners", OwnersDataApiHandler),
        (r"/api/owner/add", AddOwnerApiHandler),
        (r"/api/field/delete/([0-9]+)", FieldDeleteHandler),
        (r"/api/field/rename/([0-9]+)", FieldRenameHandler),
        (r"/api/field/assign_owner/([0-9]+)", FieldAssignOwnerHandler),
        (r"/api/field/add", FieldAddHandler),
        (r"/api/field/update_geometry/([0-9]+)", FieldUpdateGeometryHandler),
        (r"/upload", UploadHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
    ], **settings)

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    logging.info("Сервер запущен. Откройте http://localhost:8888 в вашем браузере.")
    tornado.ioloop.IOLoop.current().start()
