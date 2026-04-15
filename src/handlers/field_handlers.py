"""
Handlers для работы с полями (CRUD, экспорт KMZ).
С поддержкой мульти-тенантности и авторизации.
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

from db import database
from src.models.auth import User
from src.models.field import Field, FieldScan, FieldZone, Owner
from src.middleware.auth import AuthenticatedRequestHandler, require_auth
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


class FieldApiBaseHandler(AuthenticatedRequestHandler):
    """Базовый класс для API handlers полей с авторизацией."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")

    def get_company_fields_query(self):
        """Возвращает query для полей текущей компании."""
        user = self.get_current_user()
        if not user:
            return Field.select().where(Field.id == -1)
        return Field.select().where(Field.company == user.company)


class FieldsApiHandler(FieldApiBaseHandler):
    """Handler для получения всех полей в формате GeoJSON."""

    def get(self) -> None:
        """Получает все поля текущей компании."""
        try:
            with db_connection():
                fields_from_db = self.get_company_fields_query()
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
        """Получает данные полей для таблицы (с пагинацией и сортировкой)."""
        try:
            with db_connection():
                query = (
                    self.get_company_fields_query()
                    .select(Field, Owner)
                    .join(Owner, JOIN.LEFT_OUTER)
                    .objects()
                )
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
        """Получает детали поля с проверкой принадлежности компании."""
        try:
            with db_connection():
                # Получаем поле с проверкой принадлежности компании
                field = (
                    Field.select(Field, Owner)
                    .join(Owner, JOIN.LEFT_OUTER)
                    .where((Field.id == field_id) & (Field.company == self.current_user.company))
                    .objects()
                    .first()
                )
                if not field:
                    self.set_status(404)
                    self.write({"error": "Field not found"})
                    return

                # Находим последний обработанный скан
                last_scan = FieldScan.select().where(
                    FieldScan.field == field,
                    FieldScan.processed == 'true'
                ).order_by(FieldScan.uploaded_at.desc()).first()

                # Если нет обработанного скана, пробуем найти любой скан (даже необработанный)
                if not last_scan:
                    last_scan = FieldScan.select().where(
                        FieldScan.field == field
                    ).order_by(FieldScan.uploaded_at.desc()).first()

                # Собираем зоны из последнего скана (или все если сканов нет)
                zones: List[Dict[str, Any]] = []
                if last_scan:
                    # Зоны из последнего скана
                    for z in FieldZone.select().where(FieldZone.scan == last_scan):
                        zones.append({
                            "name": z.name,
                            "geometry": mapping(wkt_loads(z.geometry_wkt)),
                            "avg_ndvi": z.avg_ndvi,
                            "color": z.color,
                            "scan_id": last_scan.id
                        })
                else:
                    # Старые зоны без привязки к скану (для обратной совместимости)
                    for z in FieldZone.select().where(FieldZone.field == field, FieldZone.scan.is_null(True)):
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
                    "zones": zones,
                    "last_scan_id": last_scan.id if last_scan else None
                }
            self.write(json.dumps(data))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldActionHandler(FieldApiBaseHandler):
    """Объединенный обработчик для действий с полем (PUT/DELETE/POST)"""

    @require_auth
    def delete(self, field_id: int) -> None:
        """Удаляет поле с проверкой принадлежности компании."""
        try:
            with db_connection():
                # Проверяем принадлежность компании
                field = (
                    Field.select()
                    .where((Field.id == field_id) & (Field.company == self.current_user.company))
                    .first()
                )
                if not field:
                    self.set_status(404)
                    self.write({"error": "Field not found"})
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

    @require_auth
    def post(self) -> None:
        """Добавление поля в компанию текущего пользователя с проверкой на дубликаты."""
        try:
            data = json.loads(self.request.body)

            # Валидация входных данных
            errors = validate_field_data(data)
            if errors:
                self.set_status(400)
                self.write({"error": "; ".join(errors)})
                return

            poly = shape(data['geometry'])
            
            # ПРОВЕРКА НА ДУБЛИКАТЫ (наложение на существующие поля)
            # Если новое поле на 90% и более совпадает с существующим, не даем создать
            with db_connection():
                existing_fields = Field.select().where(Field.company == self.current_user.company)
                for field in existing_fields:
                    existing_poly = wkt_loads(field.geometry_wkt)
                    
                    # Быстрая проверка через bounding box
                    if not poly.bounds[0] > existing_poly.bounds[2] and \
                       not poly.bounds[2] < existing_poly.bounds[0] and \
                       not poly.bounds[1] > existing_poly.bounds[3] and \
                       not poly.bounds[3] < existing_poly.bounds[1]:
                        
                        # Точная проверка через пересечение
                        if poly.intersects(existing_poly):
                            intersection_area = poly.intersection(existing_poly).area
                            union_area = poly.union(existing_poly).area
                            iou = intersection_area / union_area if union_area > 0 else 0
                            
                            # Если IoU > 0.9 (90% совпадение), это дубликат
                            if iou > 0.9:
                                self.set_status(400)
                                self.write({
                                    "error": f"Поле с такими координатами уже существует (ID: {field.id}, '{field.name}')."
                                })
                                return

                area = calculate_accurate_area(poly)
                new_f = Field.create(
                    name=data.get('name', 'Поле'),
                    geometry_wkt=poly.wkt,
                    properties_json=json.dumps({"area_sq_m": area}),
                    company=self.current_user.company  # Привязываем к компании
                )
            self.write({"id": new_f.id})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class FieldUpdateHandler(FieldApiBaseHandler):
    """Обработчик обновлений (PUT) с использованием паттерна Command."""

    @require_auth
    def put(self, action: str, field_id: int) -> None:
        """Обновляет поле с проверкой принадлежности компании."""
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
                # Проверяем принадлежность компании
                field = (
                    Field.select()
                    .where((Field.id == field_id) & (Field.company == self.current_user.company))
                    .first()
                )
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

    @require_auth
    def get(self, field_id: int) -> None:
        """Экспортирует поле в KMZ с проверкой принадлежности компании."""
        try:
            with db_connection():
                # Проверяем принадлежность компании
                field = (
                    Field.select()
                    .where((Field.id == field_id) & (Field.company == self.current_user.company))
                    .first()
                )
                if not field:
                    self.set_status(404)
                    self.write({"error": "Field not found"})
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

    @require_auth
    def get(self) -> None:
        """Экспортирует все поля компании в ZIP архиве."""
        try:
            with db_connection():
                fields = self.get_company_fields_query()
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
