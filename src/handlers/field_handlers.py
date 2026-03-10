import tornado.web
import json
import logging
import math
from shapely.geometry import mapping, shape
from shapely.wkt import loads as wkt_loads
from peewee import JOIN

from db import database, Field, Owner
from src.services.gis_service import calculate_accurate_area
from src.services.kmz_service import create_kmz

class FieldApiBaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

class FieldsApiHandler(FieldApiBaseHandler):
    def get(self):
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

class FieldsDataApiHandler(FieldApiBaseHandler):
    def get(self):
        try:
            if database.is_closed(): database.connect()
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

class FieldGetHandler(FieldApiBaseHandler):
    def get(self, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.select(Field, Owner).join(Owner, JOIN.LEFT_OUTER).where(Field.id == field_id).objects().first()
            if not field:
                self.set_status(404)
                self.write({"error": "Field not found"})
                return
            
            geom = wkt_loads(field.geometry_wkt)
            properties = json.loads(field.properties_json) if field.properties_json else {}
            area_ha = properties.get('area_sq_m', 0) / 10000
            
            data = {
                "id": field.id,
                "name": field.name or "N/A",
                "area": f"{area_ha:.2f} га",
                "owner": field.owner.name if field.owner_id else "N/A",
                "owner_id": field.owner_id,
                "land_status": field.land_status or "Не указан",
                "parcel_number": field.parcel_number or "N/A",
                "geometry": mapping(geom),
                "properties": properties
            }
            self.write(json.dumps(data))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()

class FieldActionHandler(FieldApiBaseHandler):
    """Объединенный обработчик для действий с полем (PUT/DELETE/POST)"""
    
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

    def post(self):
        """Добавление поля"""
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
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()

class FieldUpdateHandler(FieldApiBaseHandler):
    """Обработчик обновлений (PUT)"""
    
    def put(self, action, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                return
            
            data = json.loads(self.request.body)
            
            if action == 'rename':
                field.name = data.get('new_name')
            elif action == 'assign_owner':
                owner_id = data.get('owner_id')
                field.owner = Owner.get_or_none(Owner.id == owner_id) if owner_id else None
            elif action == 'update_details':
                field.land_status = data.get('land_status', field.land_status)
                field.parcel_number = data.get('parcel_number', field.parcel_number)
            elif action == 'update_geometry':
                if 'geometry' in data:
                    poly = shape(data['geometry'])
                    area = calculate_accurate_area(poly)
                    field.geometry_wkt = poly.wkt
                    props = json.loads(field.properties_json or '{}')
                    props['area_sq_m'] = area
                    field.properties_json = json.dumps(props)
            
            field.save()
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

class FieldExportKmzHandler(FieldApiBaseHandler):
    def get(self, field_id):
        try:
            if database.is_closed(): database.connect()
            field = Field.get_or_none(Field.id == field_id)
            if not field:
                self.set_status(404)
                return
            
            height = int(self.get_argument("height", 100))
            overlap_h = int(self.get_argument("overlap_h", 80))
            overlap_w = int(self.get_argument("overlap_w", 70))
            if height > 120: height = 120
            
            kmz_data = create_kmz(field.id, field.name or "Field", field.geometry_wkt, 
                                 height=height, overlap_h=overlap_h, overlap_w=overlap_w)
            
            filename = f"Field_{field.id}_{height}m.kmz"
            self.set_header('Content-Type', 'application/vnd.google-earth.kmz')
            self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.write(kmz_data)
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()
