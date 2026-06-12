"""
Handlers для журнала полевых работ (FieldJournal).
CRUD операции с привязкой к компании.
"""
import json
import logging
from datetime import datetime

from src.models.field import Field, FieldJournal, FieldScan
from src.middleware.auth import AuthenticatedRequestHandler, require_auth
from src.utils.db_utils import db_connection

logger = logging.getLogger(__name__)


class FieldJournalHandler(AuthenticatedRequestHandler):
    """GET /api/field/{id}/journal — список записей журнала поля."""

    @require_auth
    def get(self, field_id: int) -> None:
        try:
            with db_connection():
                field = Field.select().where(
                    (Field.id == field_id) & (Field.company == self.current_user.company)
                ).first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Поле не найдено"})
                    return

                entries = FieldJournal.select().where(
                    FieldJournal.field == field
                ).order_by(FieldJournal.created_at.desc())

                result = []
                for e in entries:
                    result.append({
                        "id": e.id,
                        "crop_type": e.crop_type,
                        "crop_variety": e.crop_variety,
                        "planting_date": e.planting_date.isoformat() if e.planting_date else None,
                        "harvest_date": e.harvest_date.isoformat() if e.harvest_date else None,
                        "product_name": e.product_name,
                        "product_type": e.product_type,
                        "application_rate": e.application_rate,
                        "application_date": e.application_date.isoformat() if e.application_date else None,
                        "application_method": e.application_method,
                        "scan_id": e.scan.id if e.scan else None,
                        "yield_amount": e.yield_amount,
                        "yield_date": e.yield_date.isoformat() if e.yield_date else None,
                        "notes": e.notes,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                    })

                self.write({"entries": result})
        except Exception as e:
            logger.error(f"Journal list error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class FieldJournalCreateHandler(AuthenticatedRequestHandler):
    """POST /api/field/{id}/journal — создать запись журнала."""

    @require_auth
    def post(self, field_id: int) -> None:
        try:
            with db_connection():
                field = Field.select().where(
                    (Field.id == field_id) & (Field.company == self.current_user.company)
                ).first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Поле не найдено"})
                    return

                body = json.loads(self.request.body)

                def parse_date(val):
                    if not val:
                        return None
                    try:
                        return datetime.fromisoformat(val.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        return None

                entry = FieldJournal.create(
                    field=field,
                    company=self.current_user.company,
                    crop_type=body.get('crop_type', ''),
                    crop_variety=body.get('crop_variety'),
                    planting_date=parse_date(body.get('planting_date')),
                    harvest_date=parse_date(body.get('harvest_date')),
                    product_name=body.get('product_name'),
                    product_type=body.get('product_type'),
                    application_rate=body.get('application_rate'),
                    application_date=parse_date(body.get('application_date')),
                    application_method=body.get('application_method'),
                    scan_id=body.get('scan_id'),
                    yield_amount=body.get('yield_amount'),
                    yield_date=parse_date(body.get('yield_date')),
                    notes=body.get('notes'),
                )

                self.write({"id": entry.id, "status": "created"})
        except Exception as e:
            logger.error(f"Journal create error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class FieldJournalDeleteHandler(AuthenticatedRequestHandler):
    """DELETE /api/field/{field_id}/journal/{entry_id} — удалить запись."""

    @require_auth
    def delete(self, field_id: int, entry_id: int) -> None:
        try:
            with db_connection():
                entry = FieldJournal.select().where(
                    (FieldJournal.id == entry_id) &
                    (FieldJournal.field == field_id) &
                    (FieldJournal.company == self.current_user.company)
                ).first()
                if not entry:
                    self.set_status(404)
                    self.write({"error": "Запись не найдена"})
                    return

                entry.delete_instance()
                self.write({"status": "deleted"})
        except Exception as e:
            logger.error(f"Journal delete error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})
