"""
E2E тесты: авторизация и навигация.
"""
import os
import pytest

from tests.e2e.conftest import take_screenshot


def _login(p, server):
    """Логин через auth-gate форму."""
    p.goto(server["url"])
    p.wait_for_load_state("networkidle")

    if p.locator("#auth-gate").is_visible():
        p.locator("#auth-gate-email").fill("e2e@test.com")
        p.locator("#auth-gate-password").fill("test1234")
        p.locator("#auth-gate-form button[type='submit']").click()
        p.wait_for_timeout(2000)


class TestAuth:
    """Тесты авторизации."""

    def test_login_page_loads(self, page, screenshot_dir):
        """Тест: страница логина загружается."""
        p, server = page
        p.goto(server["url"])
        p.wait_for_load_state("networkidle")

        assert p.locator("#auth-gate").is_visible(), "Auth gate не отображается"
        take_screenshot(p, "01_login_page", screenshot_dir)

    def test_login_success(self, page, screenshot_dir):
        """Тест: успешный логин."""
        p, server = page
        _login(p, server)
        take_screenshot(p, "03_after_login", screenshot_dir)

        assert not p.locator("#auth-gate").is_visible(), "Auth gate всё ещё виден после логина"

    def test_login_failure(self, page, screenshot_dir):
        """Тест: ошибка при неверном пароле."""
        p, server = page
        p.goto(server["url"])
        p.wait_for_load_state("networkidle")

        p.locator("#auth-gate-email").fill("e2e@test.com")
        p.locator("#auth-gate-password").fill("wrongpassword")
        p.locator("#auth-gate-form button[type='submit']").click()
        p.wait_for_timeout(1500)

        take_screenshot(p, "04_login_failure", screenshot_dir)

        alert = p.locator("#auth-gate-alert")
        assert alert.is_visible(), "Сообщение об ошибке не появилось"


class TestNavigation:
    """Тесты навигации по приложению."""

    def test_main_page_shows_fields(self, page, screenshot_dir):
        """Тест: главная страница показывает карту с полем."""
        p, server = page
        _login(p, server)
        take_screenshot(p, "05_main_page", screenshot_dir)

        assert p.locator("#map").count() > 0, "Карта не найдена"

    def test_field_detail_page(self, page, screenshot_dir):
        """Тест: страница деталей поля."""
        p, server = page
        _login(p, server)

        p.goto(f"{server['url']}/#/field/1")
        p.wait_for_timeout(3000)
        take_screenshot(p, "06_field_detail", screenshot_dir)

        detail = p.locator("#field-detail-name, .field-detail")
        assert detail.count() > 0, "Детали поля не отображаются"

    def test_upload_page(self, page, screenshot_dir):
        """Тест: страница загрузки."""
        p, server = page
        _login(p, server)

        p.goto(f"{server['url']}/#/uploads")
        p.wait_for_timeout(2000)
        take_screenshot(p, "07_upload_page", screenshot_dir)

        forms = p.locator(".upload-card, form[id*='upload']")
        assert forms.count() > 0, "Формы загрузки не найдены"
