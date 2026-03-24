import tornado.ioloop
import tornado.web
import os
import logging
from db import initialize_db

from src.handlers.field_handlers import (
    FieldsApiHandler, FieldsDataApiHandler, FieldGetHandler, 
    FieldActionHandler, FieldUpdateHandler, FieldExportKmzHandler,
    BulkKMZExportHandler
)
from src.handlers.owner_handlers import OwnersDataApiHandler, OwnerActionHandler
from src.handlers.upload_handlers import UploadHandler, TaskStatusHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/index.html")

def make_app():
    settings = {
        "template_path": os.path.dirname(__file__),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "debug": True,
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        
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
        
        # Static & PWA
        (r"/(sw\.js)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/(manifest\.json)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/(favicon\.ico)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings['static_path']}),
    ], **settings)

if __name__ == "__main__":
    try:
        initialize_db()
        app = make_app()
        app.listen(8888, max_body_size=1024 * 1024 * 1024) # 1GB limit here
        logging.info("Сервер запущен: http://localhost:8888")
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info("Остановка сервера...")
        tornado.ioloop.IOLoop.current().stop()
