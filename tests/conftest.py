# tests/conftest.py

import os
import socket
import sys

# ПРИНУДИТЕЛЬНО УСТАНАВЛИВАЕМ ОКРУЖЕНИЕ ТЕСТОВ **ДО** импорта модулей
os.environ["FIELD_MAPPER_ENV"] = "test"
# Фиксируем SESSION_SECRET чтобы токены создавались и проверялись одним ключом
os.environ["SESSION_SECRET"] = "test_session_secret_key_for_pytest_only"

# Добавляем путь к корню проекта, чтобы можно было импортировать модули приложения
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from tornado.httpclient import AsyncHTTPClient

import db
from app import make_app
from db import initialize_db

# Shared test constants
TEST_WKT_POLYGON = "POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))"
TEST_BOUNDS = (18.7, 48.1, 18.8, 48.2)


def pytest_configure(config):
    config.option.asyncio_mode = "auto"


def find_unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="function")
def test_db():
    """Создаёт чистую тестовую БД со всеми таблицами (включая auth)."""
    if not db.database.is_closed():
        db.database.close()

    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)

    initialize_db()
    db.database.connect(reuse_if_open=True)

    yield db.database

    db.database.close()
    if os.path.exists(db.TEST_DB_FILE):
        try:
            os.remove(db.TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture
async def http_server_client(test_db):
    application = make_app()
    port = find_unused_port()
    server = application.listen(port)
    client = AsyncHTTPClient()

    from src.utils.auth import session_manager
    session_manager.secret_key = os.environ["SESSION_SECRET"]

    yield client, f"http://localhost:{port}"
    client.close()
    server.stop()


@pytest.fixture
def http_client(http_server_client):
    return http_server_client[0]


@pytest.fixture
def base_url(http_server_client):
    return http_server_client[1]


def create_auth_token(user):
    """Создаёт auth токен для пользователя."""
    from src.utils.auth import session_manager
    return session_manager.create_token(user)


def _setup_session_secret():
    from src.utils.auth import session_manager
    session_manager.secret_key = os.environ["SESSION_SECRET"]

_setup_session_secret()


KNOWN_FAILURES = []


def pytest_runtest_setup(item):
    for failure_name in KNOWN_FAILURES:
        if item.name == failure_name:
            item.add_marker(pytest.mark.xfail(reason=f"Known issue: {failure_name}"))
            break


# ─── Shared fixtures ──────────────────────────────────────────────


@pytest.fixture
def test_company(test_db):
    """Создаёт тестовую компанию."""
    from src.models.auth import Company
    company = Company.create(name='Test Company', slug='test-company')
    return company


@pytest.fixture
def test_user(test_db, test_company):
    """Создаёт тестового пользователяOWNER в test_company."""
    from src.models.auth import User, UserRole
    user = User.create_user(
        email='test@test.com',
        password='testpassword123',
        company=test_company,
        role=UserRole.OWNER
    )
    return user


@pytest.fixture
def auth_token(test_db, test_user):
    """Возвращает auth токен для test_user."""
    from src.utils.auth import session_manager
    session_manager.secret_key = os.environ["SESSION_SECRET"]
    return session_manager.create_token(test_user)


@pytest.fixture
def auth_headers(auth_token):
    """Заголовки с авторизацией для HTTP запросов."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def auth_cookies(auth_token):
    """Cookie заголовки с авторизацией (для Tornado secure cookie)."""
    app = make_app()
    secret = app.settings.get('cookie_secret', os.environ["SESSION_SECRET"])

    import tornado.web
    signed = tornado.web.create_signed_value(secret, 'session_token', auth_token.encode())
    return {"Cookie": f"session_token={signed.decode()}"}


@pytest.fixture
def make_geotiff(tmp_path):
    """
    Фабрика для создания тестовых GeoTIFF файлов.
    Возвращает функцию с параметрами: rows, cols, zones, bounds, noise_std, nodata.
    """
    def _make(rows=100, cols=100, zones=None, bounds=TEST_BOUNDS, noise_std=0.05, nodata=None):
        if zones is None:
            zones = [0.2, 0.5, 0.8]

        data = np.zeros((rows, cols), dtype=np.float32)
        zone_height = rows // len(zones)
        for i, val in enumerate(zones):
            start = i * zone_height
            end = start + zone_height if i < len(zones) - 1 else rows
            data[start:end, :] = val

        data += np.random.normal(0, noise_std, (rows, cols))
        data = np.clip(data, -1, 1).astype(np.float32)

        path = tmp_path / "test.tif"
        transform = from_origin(bounds[0], bounds[3],
                                (bounds[2] - bounds[0]) / cols,
                                (bounds[3] - bounds[1]) / rows)

        write_kwargs = dict(
            driver='GTiff', height=rows, width=cols, count=1,
            dtype='float32', crs='EPSG:4326', transform=transform,
        )
        if nodata is not None:
            write_kwargs['nodata'] = nodata

        with rasterio.open(path, 'w', **write_kwargs) as dst:
            dst.write(data, 1)

        return str(path)

    return _make
