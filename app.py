"""
Главный модуль приложения Field Mapper.
Настраивает и запускает Tornado сервер.
"""
import logging
import os
import secrets
from typing import Any, Dict

import tornado.ioloop
import tornado.web

from db import ensure_db_exists
from src.handlers.auth_handlers import (
    CompanyHandler,
    LoginHandler,
    LogoutHandler,
    ProfileHandler,
    RegisterHandler,
)
from src.handlers.field_handlers import (
    BulkKMZExportHandler,
    FieldActionHandler,
    FieldExportKmzHandler,
    FieldGetHandler,
    FieldsApiHandler,
    FieldsDataApiHandler,
    FieldUpdateHandler,
)
from src.handlers.owner_handlers import OwnerActionHandler, OwnersDataApiHandler
from src.handlers.upload_handlers import TaskStatusHandler, UploadHandler, ISOXMLExportHandler, FieldScansHandler, FieldScanZonesHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class MainHandler(tornado.web.RequestHandler):
    """Обработчик главной страницы."""
    
    def get(self) -> None:
        self.render("static/index.html")


def make_app() -> tornado.web.Application:
    """Создаёт и настраивает Tornado приложение.

    Returns:
        Настроенное приложение Tornado.
    """
    # Генерируем secret_key из окружения или создаём новый
    secret_key = os.environ.get('SESSION_SECRET', secrets.token_hex(32))
    
    settings: Dict[str, Any] = {
        "template_path": os.path.dirname(__file__),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "debug": True,
        "cookie_secret": secret_key,
    }
    return tornado.web.Application([
        (r"/", MainHandler),

        # API: Authentication
        (r"/api/auth/login", LoginHandler),
        (r"/api/auth/register", RegisterHandler),
        (r"/api/auth/logout", LogoutHandler),
        (r"/api/auth/profile", ProfileHandler),
        (r"/api/auth/company", CompanyHandler),

        # API: Fields
        (r"/api/fields", FieldsApiHandler),
        (r"/api/fields_data", FieldsDataApiHandler),
        (r"/api/field/([0-9]+)", FieldGetHandler),
        (r"/api/field/add", FieldActionHandler),
        (r"/api/field/delete/([0-9]+)", FieldActionHandler),
        (r"/api/field/export/kmz/all", BulkKMZExportHandler),
        (r"/api/field/export/kmz/([0-9]+)", FieldExportKmzHandler),
        # Объединенный эндпоинт для апдейтов: rename, assign_owner, update_details, update_geometry
        (r"/api/field/(?P<action>rename|assign_owner|update_details|update_geometry)/(?P<field_id>[0-9]+)", FieldUpdateHandler),

        # API: Owners
        (r"/api/owners", OwnersDataApiHandler),
        (r"/api/owner/add", OwnerActionHandler),
        (r"/api/owner/delete/([0-9]+)", OwnerActionHandler),

        # Upload
        (r"/upload", UploadHandler),
        (r"/api/task/(.*)", TaskStatusHandler),
        (r"/api/field/export/isoxml/([0-9]+)", ISOXMLExportHandler),
        (r"/api/field/([0-9]+)/scans", FieldScansHandler),
        (r"/api/field/([0-9]+)/scans/([0-9]+)", FieldScansHandler),  # DELETE /api/field/{id}/scans/{scan_id}
        (r"/api/scan/([0-9]+)/zones", FieldScanZonesHandler),

        # Static & PWA
        (r"/(sw\.js)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/(manifest\.json)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/(favicon\.ico)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
    ], **settings)


if __name__ == "__main__":
    try:
        ensure_db_exists()
        app = make_app()
        app.listen(8888, address='0.0.0.0', max_body_size=1024 * 1024 * 1024)  # 1GB limit
        logging.info("Сервер запущен: http://0.0.0.0:8888")
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info("Остановка сервера...")
        tornado.ioloop.IOLoop.current().stop()
