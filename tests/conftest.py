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

import pytest
from tornado.httpclient import AsyncHTTPClient

import db
from app import make_app
from db import initialize_db


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

    # Синхронизируем session_manager secret_key с приложением
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


# Известные проблемы (xfail) — все исправлены!
KNOWN_FAILURES = [
    # "test_owner_assignment",  # ИСПРАВЛЕНО: AssignOwnerCommand теперь использует owner_id
    # "test_invalidate_token",  # ИСПРАВЛЕНО: тест обновлён для stateless режима
    # "test_field_get_handler_excludes_unprocessed_scans",  # ИСПРАВЛЕНО: добавлен source поле
]


def pytest_runtest_setup(item):
    """Автоматически помечает известные failing тесты как xfail."""
    for failure_name in KNOWN_FAILURES:
        if item.name == failure_name:
            item.add_marker(pytest.mark.xfail(reason=f"Known issue: {failure_name}"))
            break


@pytest.fixture
def auth_token(test_db):
    """Создаёт тестового пользователя и возвращает auth токен."""
    from src.utils.auth import session_manager
    session_manager.secret_key = os.environ["SESSION_SECRET"]

    from src.models.auth import Company, User, UserRole

    company = Company.create(name='Test Company', slug='test-company')
    user = User.create_user(
        email='test@test.com',
        password='testpassword123',
        company=company,
        role=UserRole.OWNER
    )

    return session_manager.create_token(user)


@pytest.fixture
def auth_headers(auth_token):
    """Заголовки с авторизацией для HTTP запросов."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def auth_cookies(auth_token):
    """Cookie заголовки с авторизацией (для Tornado secure cookie)."""
    from app import make_app
    app = make_app()
    secret = app.settings.get('cookie_secret', os.environ["SESSION_SECRET"])
    
    import tornado.web
    signed = tornado.web.create_signed_value(secret, 'session_token', auth_token.encode())
    return {"Cookie": f"session_token={signed.decode()}"}
