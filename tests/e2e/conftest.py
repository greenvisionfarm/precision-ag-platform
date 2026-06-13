"""
E2E тесты с Playwright — запускаются против реального Tornado сервера.
Скриншоты сохраняются в tests/e2e/screenshots/.
"""
import os
import sys
import socket
import threading
import time

import pytest
from playwright.sync_api import sync_playwright

# Добавляем корень проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ["FIELD_MAPPER_ENV"] = "test"
os.environ["SESSION_SECRET"] = "e2e_test_secret_key"

import db
from app import make_app
from db import initialize_db


def _find_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server():
    """Запускает Tornado сервер на случайном порту на время сессии."""
    if not db.database.is_closed():
        db.database.close()

    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)

    initialize_db()
    db.database.connect(reuse_if_open=True)

    # Создаём тестового пользователя и поле
    from src.models.auth import Company, User, UserRole
    from src.utils.auth import session_manager
    session_manager.secret_key = os.environ["SESSION_SECRET"]

    company = Company.create(name="E2E Company", slug="e2e-company")
    user = User.create_user(
        email="e2e@test.com",
        password="test1234",
        company=company,
        role=UserRole.OWNER,
    )

    from db import Field
    field = Field.create(
        name="Тестовое поле E2E",
        geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
        properties_json='{"area": 42}',
        company_id=company.id,
    )

    app = make_app()
    port = _find_port()
    server_instance = app.listen(port, address="127.0.0.1")

    base_url = f"http://127.0.0.1:{port}"

    yield {"url": base_url, "user": user, "field": field, "company": company}

    server_instance.stop()
    db.database.close()
    if os.path.exists(db.TEST_DB_FILE):
        os.remove(db.TEST_DB_FILE)


@pytest.fixture(scope="session")
def browser():
    """Запускает headless Chromium на время сессии."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser, server):
    """Создаёт новую страницу для каждого теста."""
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 800},
        base_url=server["url"],
    )
    page = ctx.new_page()
    yield page, server
    ctx.close()


@pytest.fixture
def screenshot_dir():
    """Директория для скриншотов."""
    d = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(d, exist_ok=True)
    return d


def take_screenshot(page, name, screenshot_dir):
    """Делает скриншот и сохраняет с именем."""
    path = os.path.join(screenshot_dir, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path
