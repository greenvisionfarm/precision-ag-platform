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

def calculate_accurate_area(poly):
    """
    Расчет точной площади в квадратных метрах.
    Используется EPSG:3035 (ETRS89-extended / LAEA Europe).
    """
    temp_gdf = gpd.GeoDataFrame([{'geometry': poly}], crs="EPSG:4326")
    temp_gdf_projected = temp_gdf.to_crs(epsg=3035)
    return temp_gdf_projected.geometry.area.iloc[0]

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/index.html")

class FieldsApiHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        try:
            if database.is_closed(): database.connect()
            fields_from_db = Field.select()
            features = []
            for field in fields_from_db:
                geom = wkt_loads(field.geometry_wkt)
                properties = json.loads(field.properties_json) if field.properties_json else {}
                properties['db_id'] = field.id
                if field.name: properties['name'] = field.name
                features.append({"type": "Feature", "geometry": mapping(geom), "properties": properties})
            self.write(json.dumps({"type": "FeatureCollection", "features": features}))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()

class FieldsDataApiHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        try:
            if database.is_closed(): database.connect()
            # Используем .objects(), чтобы Peewee корректно собрал связанные модели
            query = Field.select(Field, Owner).join(Owner, JOIN.LEFT_OUTER).objects()
            data = []
            for field in query:
                properties = json.loads(field.properties_json) if field.properties_json else {}
                area_ha = properties.get('area_sq_m', 0) / 10000
                data.append({
                    "id": field.id,
                    "name": field.name or "N/A",
                    "area": f"{area_ha:.2f} га",
                    "owner": field.owner.name if field.owner_id else "N/A",
                    "owner_id": field.owner_id,
                    "land_status": field.land_status or "Не указан",
                    "parcel_number": field.parcel_number or "N/A",
                    "properties": json.dumps(properties)
                })
            self.write(json.dumps({"data": data}))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()

class FieldDeleteHandler(tornado.web.RequestHandler):
    def delete(self, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if field:
                field.delete_instance()
                self.write({"message": "Удалено."})
            else: self.set_status(404)
        finally:
            if not database.is_closed(): database.close()

class FieldRenameHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                return
            new_name = json.loads(self.request.body).get('new_name')
            field.name = new_name
            field.save()
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

class FieldAssignOwnerHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                return
            owner_id = json.loads(self.request.body).get('owner_id')
            if owner_id:
                field.owner = Owner.get_or_none(Owner.id == owner_id)
            else:
                field.owner = None
            field.save()
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

class FieldUpdateDetailsHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                return
            data = json.loads(self.request.body)
            field.land_status = data.get('land_status', field.land_status)
            field.parcel_number = data.get('parcel_number', field.parcel_number)
            field.save()
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

class FieldAddHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
            if 'geometry' not in data:
                self.set_status(400)
                self.write({"error": "Missing geometry"})
                return
            poly = shape(data['geometry'])
            area = calculate_accurate_area(poly)
            if database.is_closed(): database.connect()
            new_f = Field.create(name=data.get('name', 'Поле'), geometry_wkt=poly.wkt, properties_json=json.dumps({"area_sq_m": area}))
            self.write({"id": new_f.id})
        finally:
            if not database.is_closed(): database.close()

class FieldUpdateGeometryHandler(tornado.web.RequestHandler):
    def put(self, field_id):
        try:
            data = json.loads(self.request.body)
            if 'geometry' not in data:
                self.set_status(400)
                return
            poly = shape(data['geometry'])
            area = calculate_accurate_area(poly)
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                return
            field.geometry_wkt = poly.wkt
            props = json.loads(field.properties_json or '{}')
            props['area_sq_m'] = area
            field.properties_json = json.dumps(props)
            field.save()
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

class OwnersDataApiHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        try:
            if database.is_closed(): database.connect()
            owners = Owner.select()
            self.write(json.dumps({"data": [{"id": o.id, "name": o.name} for o in owners]}))
        finally:
            if not database.is_closed(): database.close()

class AddOwnerApiHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            if database.is_closed(): database.connect()
            name = json.loads(self.request.body).get('name')
            Owner.get_or_create(name=name)
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

class UploadHandler(tornado.web.RequestHandler):
    def post(self):
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
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

def make_app():
    settings = {
        "template_path": os.path.dirname(__file__),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "debug": True,
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/fields", FieldsApiHandler),
        (r"/api/fields_data", FieldsDataApiHandler),
        (r"/api/owners", OwnersDataApiHandler),
        (r"/api/owner/add", AddOwnerApiHandler),
        (r"/api/field/delete/([0-9]+)", FieldDeleteHandler),
        (r"/api/field/rename/([0-9]+)", FieldRenameHandler),
        (r"/api/field/assign_owner/([0-9]+)", FieldAssignOwnerHandler),
        (r"/api/field/update_details/([0-9]+)", FieldUpdateDetailsHandler),
        (r"/api/field/add", FieldAddHandler),
        (r"/api/field/update_geometry/([0-9]+)", FieldUpdateGeometryHandler),
        (r"/upload", UploadHandler),
        (r"/(sw\.js)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/(manifest\.json)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/(favicon\.ico)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
    ], **settings)

if __name__ == "__main__":
    try:
        initialize_db()
        app = make_app()
        app.listen(8888)
        logging.info("Сервер запущен: http://localhost:8888")
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info("Остановка сервера...")
        tornado.ioloop.IOLoop.current().stop()
