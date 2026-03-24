import json

import tornado.web

from db import Owner, database


class OwnerApiBaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

class OwnersDataApiHandler(OwnerApiBaseHandler):
    def get(self):
        try:
            if database.is_closed(): database.connect()
            owners = Owner.select()
            self.write(json.dumps({"data": [{"id": o.id, "name": o.name} for o in owners]}))
        finally:
            if not database.is_closed(): database.close()

class OwnerActionHandler(OwnerApiBaseHandler):
    def post(self):
        try:
            if database.is_closed(): database.connect()
            name = json.loads(self.request.body).get('name')
            Owner.get_or_create(name=name)
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()

    def delete(self, owner_id):
        try:
            if database.is_closed(): database.connect()
            owner = Owner.get_or_none(Owner.id == owner_id)
            if owner:
                owner.delete_instance()
                self.write({"message": "Удалено."})
            else:
                self.set_status(404)
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if not database.is_closed(): database.close()
