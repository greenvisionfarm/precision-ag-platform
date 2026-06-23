"""
Handlers для работы с владельцами полей.
"""
import json
from typing import Any, Dict, List

import tornado.web

from src.middleware.auth import AuthenticatedRequestHandler, require_auth
from src.models.field import Owner
from src.utils.db_utils import db_connection
from src.utils.validators import validate_owner_data


class OwnerApiBaseHandler(AuthenticatedRequestHandler):
    """Базовый класс для API handlers владельцев с авторизацией."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")


class OwnersDataApiHandler(OwnerApiBaseHandler):
    """Handler для получения списка владельцев."""

    @require_auth
    def get(self) -> None:
        try:
            with db_connection():
                owners = Owner.select().where(Owner.company == self.current_user.company)
            data: List[Dict[str, Any]] = [
                {"id": o.id, "name": o.name, "color": o.color} for o in owners
            ]
            self.write(json.dumps({"data": data}))
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class OwnerActionHandler(OwnerApiBaseHandler):
    """Handler для действий с владельцем (создание/удаление)."""

    @require_auth
    def post(self) -> None:
        try:
            data = json.loads(self.request.body)

            errors = validate_owner_data(data)
            if errors:
                self.set_status(400)
                self.write({"error": "; ".join(errors)})
                return

            with db_connection():
                Owner.get_or_create(
                    name=data['name'],
                    defaults={'company': self.current_user.company, 'color': data.get('color')}
                )
            self.write({"message": "OK"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

    @require_auth
    def put(self, owner_id: int) -> None:
        try:
            data = json.loads(self.request.body)
            with db_connection():
                owner = Owner.get_or_none(
                    (Owner.id == owner_id) & (Owner.company == self.current_user.company)
                )
                if not owner:
                    self.set_status(404)
                    return
                if 'color' in data:
                    owner.color = data['color']
                    owner.save()
                if 'name' in data:
                    owner.name = data['name']
                    owner.save()
            self.write({"message": "OK"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})

    @require_auth
    def delete(self, owner_id: int) -> None:
        try:
            with db_connection():
                owner = Owner.get_or_none(
                    (Owner.id == owner_id) & (Owner.company == self.current_user.company)
                )
                if owner:
                    owner.delete_instance()
                    self.write({"message": "Удалено."})
                else:
                    self.set_status(404)
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
