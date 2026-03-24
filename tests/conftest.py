# tests/conftest.py

import pytest
import os
import sys
import socket
from tornado.httpclient import AsyncHTTPClient

# Добавляем путь к корню проекта, чтобы можно было импортировать модули приложения
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ПРИНУДИТЕЛЬНО УСТАНАВЛИВАЕМ ОКРУЖЕНИЕ ТЕСТОВ
os.environ['FIELD_MAPPER_ENV'] = 'test'

import db
from app import make_app
from db import initialize_db

# Указываем pytest-asyncio использовать режим "auto" для автоматического обнаружения асинхронных тестов
def pytest_configure(config):
    config.option.asyncio_mode = "auto"

def find_unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@pytest.fixture(scope='function')
def test_db():
    # Удаляем старый файл тестовой базы, если он остался
    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)
    
    # Инициализируем чистую базу
    initialize_db()
    db.database.connect(reuse_if_open=True)
    yield db.database
    db.database.close()
    
    # Удаляем после теста (по желанию)
    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)

@pytest.fixture
async def http_server_client(test_db):
    application = make_app()
    port = find_unused_port()
    server = application.listen(port)
    client = AsyncHTTPClient()
    yield client, f"http://localhost:{port}"
    client.close()
    server.stop()
