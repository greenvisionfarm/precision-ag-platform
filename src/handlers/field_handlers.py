"""
Handlers для работы с полями (CRUD, экспорт KMZ).
"""
import io
import json
import logging
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import tornado.web
from peewee import JOIN
from shapely.geometry import mapping, shape
from shapely.wkt import loads as wkt_loads

from db import Field, Owner, database
from src.services.gis_service import calculate_accurate_area
from src.services.kmz_service import create_kmz
from src.utils.db_utils import db_connection
from src.utils.validators import validate_field_data


def slugify(text: Optional[str]) -> str:
    """Очистка строки для использования в имени файла.
    
    Args:
        text: Исходная строка.
        
    Returns:
        Очищенная строка для имени файла.
    """
    if not text: 
        return "Field"
    return "".join([c if c.isalnum() or c in (' ', '_', '-') else '' for c in text]).strip().replace(' ', '_')


class FieldApiBaseHandler(tornado.web.RequestHandler):
    """Базовый класс для API handlers полей."""
    
    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")


class FieldsApiHandler(FieldApiBaseHandler):
    """Handler для получения всех полей в формате GeoJSON."""
    
    def get(self) -> None:
        try:
            with db_connection():
                fields_from_db = Field.select()
                features: List[Dict[str, Any]] = []
                for field in fields_from_db:
                    geom = wkt_loads(field.geometry_wkt)
                    properties = json.loads(field.properties_json) if field.properties_json else {}
                    properties['db_id'] = field.id
                    if field.name: 
                        properties['name'] = field.name
                    features.append({
                        "type": "Feature", 
                        "geometry": mapping(geom), 
                        "properties": properties
                    })
            self.write(json.dumps({"type": "FeatureCollection", "features": features}))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldsDataApiHandler(FieldApiBaseHandler):
    """Handler для получения данных полей для таблицы."""
    
    def get(self) -> None:
        try:
            with db_connection():
                query = Field.select(Field, Owner).join(Owner, JOIN.LEFT_OUTER).objects()
                data: List[Dict[str, Any]] = []
                for field in query:
                    properties = json.loads(field.properties_json) if field.properties_json else {}
                    area_ha = properties.get('area_sq_m', 0) / 10000
                    data.append({
                        "id": field.id,
                        "name": field.name or "N/A",
                        "area": f"{area_ha:.2f} га",
                        "owner": field.owner.name if field.owner_id else "N/A",
                        "owner_id": field.owner_id,
                        "land_status": properties.get('land_status', "Не указан"),
                        "parcel_number": properties.get('parcel_number', "N/A"),
                        "properties": json.dumps(properties)
                    })
            self.write(json.dumps({"data": data}))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldGetHandler(FieldApiBaseHandler):
    """Handler для получения деталей конкретного поля."""
    
    def get(self, field_id: int) -> None:
        try:
            from db import FieldZone
            with db_connection():
                field = Field.select(Field, Owner).join(Owner, JOIN.LEFT_OUTER).where(Field.id == field_id).objects().first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Field not found"})
                    return

                # Собираем зоны
                zones: List[Dict[str, Any]] = []
                for z in FieldZone.select().where(FieldZone.field == field):
                    zones.append({
                        "name": z.name,
                        "geometry": mapping(wkt_loads(z.geometry_wkt)),
                        "avg_ndvi": z.avg_ndvi,
                        "color": z.color
                    })

                geom = wkt_loads(field.geometry_wkt)
                properties = json.loads(field.properties_json) if field.properties_json else {}
                area_ha = properties.get('area_sq_m', 0) / 10000

                data: Dict[str, Any] = {
                    "id": field.id,
                    "name": field.name or "N/A",
                    "area": f"{area_ha:.2f} га",
                    "owner": field.owner.name if field.owner_id else "N/A",
                    "owner_id": field.owner_id,
                    "land_status": properties.get('land_status', "Не указан"),
                    "parcel_number": properties.get('parcel_number', "N/A"),
                    "geometry": mapping(geom),
                    "properties": properties,
                    "zones": zones
                }
            self.write(json.dumps(data))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldActionHandler(FieldApiBaseHandler):
    """Объединенный обработчик для действий с полем (PUT/DELETE/POST)"""
    
    def delete(self, field_id: int) -> None:
        try:
            from db import FieldZone
            with db_connection():
                field = Field.get_or_none(Field.id == field_id)
                if not field:
                    self.set_status(404)
                    return

                # Проверяем наличие связанных зон
                zones_count = FieldZone.select().where(FieldZone.field == field).count()
                if zones_count > 0:
                    self.set_status(400)
                    self.write({
                        "error": f"Нельзя удалить поле: есть {zones_count} связанных зон. "
                                 "Удалите зоны перед удалением поля."
                    })
                    return

                field.delete_instance()
            self.write({"message": "Удалено."})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

    def post(self) -> None:
        """Добавление поля"""
        try:
            data = json.loads(self.request.body)

            # Валидация входных данных
            errors = validate_field_data(data)
            if errors:
                self.set_status(400)
                self.write({"error": "; ".join(errors)})
                return

            poly = shape(data['geometry'])
            area = calculate_accurate_area(poly)
            with db_connection():
                new_f = Field.create(
                    name=data.get('name', 'Поле'), 
                    geometry_wkt=poly.wkt, 
                    properties_json=json.dumps({"area_sq_m": area})
                )
            self.write({"id": new_f.id})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldUpdateHandler(FieldApiBaseHandler):
    """Обработчик обновлений (PUT) с использованием паттерна Command."""
    
    def put(self, action: str, field_id: int) -> None:
        try:
            # Получаем команду из реестра
            from src.handlers.field_commands import get_command, get_available_actions
            
            command = get_command(action)
            if not command:
                self.set_status(400)
                self.write({
                    "error": f"Неизвестное действие: {action}. "
                             f"Доступные действия: {', '.join(get_available_actions())}"
                })
                return
            
            with db_connection():
                field = Field.get_or_none(Field.id == field_id)
                if not field:
                    self.set_status(404)
                    self.write({"error": "Field not found"})
                    return
                
                data = json.loads(self.request.body)
                command.execute(field, data)
                field.save()
            
            self.write({"message": "OK"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldExportKmzHandler(FieldApiBaseHandler):
    """Handler для экспорта поля в KMZ."""
    
    def get(self, field_id: int) -> None:
        try:
            with db_connection():
                field = Field.get_or_none(Field.id == field_id)
                if not field:
                    self.set_status(404)
                    return
                height = int(self.get_argument("height", 100))
                overlap_h = int(self.get_argument("overlap_h", 80))
                overlap_w = int(self.get_argument("overlap_w", 70))
                direction = int(self.get_argument("direction", 0))
                kmz_data = create_kmz(
                    field.id, field.name or "Field", field.geometry_wkt,
                    height=height, overlap_h=overlap_h, overlap_w=overlap_w,
                    direction=direction
                )
                filename = f"{slugify(field.name)}_{height}m.kmz"
                self.set_header('Content-Type', 'application/vnd.google-earth.kmz')
                self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.write(kmz_data)
        except Exception as e:
            logging.error(f"KMZ Export error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class BulkKMZExportHandler(FieldApiBaseHandler):
    """Handler для массового экспорта всех полей в KMZ (ZIP)."""
    
    def get(self) -> None:
        try:
            with db_connection():
                fields = Field.select()
                if not fields.exists():
                    self.set_status(404)
                    self.write(json.dumps({"error": "Нет полей для экспорта"}))
                    return
                height = int(self.get_argument("height", 100))
                overlap_h = int(self.get_argument("overlap_h", 80))
                overlap_w = int(self.get_argument("overlap_w", 70))
                direction = int(self.get_argument("direction", 0))
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for field in fields:
                        kmz_data = create_kmz(
                            field.id, field.name or "Field", field.geometry_wkt,
                            height=height, overlap_h=overlap_h, overlap_w=overlap_w,
                            direction=direction
                        )
                        filename = f"{slugify(field.name)}_{height}m.kmz"
                        zf.writestr(filename, kmz_data)
                zip_buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                self.set_header('Content-Type', 'application/zip')
                self.set_header('Content-Disposition', f'attachment; filename=all_fields_kmz_{timestamp}.zip')
            self.write(zip_buffer.read())
        except Exception as e:
            logging.error(f"Bulk KMZ Export error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})
