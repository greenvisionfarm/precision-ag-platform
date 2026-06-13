"""
E2E тесты: загрузка файлов и NDVI.
"""
import os
import tempfile
import numpy as np
import rasterio
from rasterio.transform import from_bounds

import pytest

from tests.e2e.conftest import take_screenshot


def _create_test_tiff(path, width=200, height=200):
    """Создаёт тестовый GeoTIFF с NDVI данными."""
    bounds = (18.72, 48.12, 18.78, 48.18)
    data = np.random.uniform(0.2, 0.9, (height, width)).astype(np.float32)
    data[0:10, :] = 0.0
    data[-10:, :] = 0.0

    transform = from_bounds(*bounds, width, height)
    with rasterio.open(path, 'w', driver='GTiff',
                       height=height, width=width, count=1,
                       dtype='float32', crs='EPSG:4326',
                       transform=transform, nodata=0.0) as dst:
        dst.write(data, 1)


def _login(p, server):
    """Логин через auth-gate."""
    p.goto(server["url"])
    p.wait_for_load_state("networkidle")
    if p.locator("#auth-gate").is_visible():
        p.locator("#auth-gate-email").fill("e2e@test.com")
        p.locator("#auth-gate-password").fill("test1234")
        p.locator("#auth-gate-form button[type='submit']").click()
        p.wait_for_timeout(2000)


def _open_upload_page(p, server):
    """Открывает страницу загрузки через sidebar."""
    _login(p, server)
    # Открываем sidebar
    p.locator("#sidebar-toggle").click()
    p.wait_for_timeout(500)
    # Кликаем "Загрузки"
    p.locator('.nav-link[href="#uploads"]').click()
    p.wait_for_timeout(1000)


class TestUploadFlow:
    """Тесты загрузки файлов."""

    def test_upload_page_loads(self, page, screenshot_dir):
        """Тест: страница загрузки загружается."""
        p, server = page
        _open_upload_page(p, server)
        take_screenshot(p, "10_upload_page", screenshot_dir)

        assert p.locator("#view-uploads").is_visible(), "Секция загрузок не видна"
        assert p.locator(".upload-card").count() >= 2, "Не все карточки загрузки найдены"

    def test_raster_upload_file_selection(self, page, screenshot_dir):
        """Тест: выбор файла в форме NDVI."""
        p, server = page
        _open_upload_page(p, server)

        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            tiff_path = tmp.name
        _create_test_tiff(tiff_path)

        try:
            p.locator("#raster-input").set_input_files(tiff_path)
            p.evaluate("document.getElementById('raster-input').dispatchEvent(new Event('change', {bubbles: true}))")
            p.wait_for_timeout(1000)
            take_screenshot(p, "11_file_selected", screenshot_dir)

            btn = p.locator("#raster-upload-button")
            assert btn.is_visible(), "Кнопка загрузки не появилась"
        finally:
            os.unlink(tiff_path)

    def test_raster_upload_submit(self, page, screenshot_dir):
        """Тест: отправка формы NDVI загрузки."""
        p, server = page
        _open_upload_page(p, server)

        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            tiff_path = tmp.name
        _create_test_tiff(tiff_path)

        try:
            p.locator("#raster-input").set_input_files(tiff_path)
            p.evaluate("document.getElementById('raster-input').dispatchEvent(new Event('change', {bubbles: true}))")
            p.wait_for_timeout(1000)

            p.locator("#raster-upload-button").click()
            take_screenshot(p, "12_upload_submitted", screenshot_dir)

            p.wait_for_timeout(5000)
            take_screenshot(p, "13_upload_result", screenshot_dir)

            status = p.locator("#raster-upload-status")
            assert status.count() > 0, "Статус загрузки не отображается"
        finally:
            os.unlink(tiff_path)

    def test_drone_upload_form_visible(self, page, screenshot_dir):
        """Тест: форма загрузки дрона видна."""
        p, server = page
        _open_upload_page(p, server)
        take_screenshot(p, "14_drone_form", screenshot_dir)

        drone_form = p.locator("#drone-upload-form")
        assert drone_form.count() > 0, "Форма загрузки дрона не найдена"

    def test_drone_field_dropdown_populated(self, page, screenshot_dir):
        """Тест: dropdown полей загружается."""
        p, server = page
        _open_upload_page(p, server)
        p.wait_for_timeout(2000)

        select = p.locator("#drone-field-select")
        options = select.locator("option")
        count = options.count()
        take_screenshot(p, "15_drone_dropdown", screenshot_dir)

        assert count >= 2, f"Dropdown полей пуст: {count} опций (ожидалось >= 2)"
