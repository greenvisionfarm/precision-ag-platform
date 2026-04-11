/**
 * Тесты страницы загрузок.
 * Проверяют что все формы загрузки видны и кнопки работают.
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Страница загрузок', () => {
  test('должна показывать страницу загрузок', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#uploads');
    await page.waitForTimeout(2000);

    // Проверяем что view-uploads видим
    await expect(page.locator('#view-uploads')).toBeVisible({ timeout: 5000 });
  });

  test('должна показывать все 3 карточки загрузок', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#uploads');
    await page.waitForTimeout(2000);

    // Проверяем что есть 3 карточки
    const uploadCards = page.locator('.upload-card');
    await expect(uploadCards).toHaveCount(3);

    // Shapefile карточка
    await expect(page.locator('text=Загрузка Границ Полей')).toBeVisible();
    // Drone карточка
    await expect(page.locator('text=Обработка снимков с дрона')).toBeVisible();
    // NDVI карточка
    await expect(page.locator('text=Загрузка NDVI')).toBeVisible();
  });

  test('кнопка загрузки shapefile должна появляться при выборе файла', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    // Кнопка изначально скрыта
    const uploadButton = page.locator('#upload-button');
    await expect(uploadButton).toBeHidden();

    // Выбираем файл и триггерим change event
    const fileInput = page.locator('#shapefile-input');
    await fileInput.setInputFiles({
      name: 'test.zip',
      mimeType: 'application/zip',
      buffer: Buffer.from('PK test')
    });

    // Ждём что кнопка появится
    await page.waitForTimeout(500);
    // Кнопка должна появиться (force т.к. может быть hidden через class а не style)
    await expect(uploadButton).not.toHaveClass(/hidden/);
  });

  test('кнопка загрузки NDVI должна появляться при выборе файла', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    const uploadButton = page.locator('#raster-upload-button');
    await expect(uploadButton).toBeHidden();

    // Выбираем файл
    const fileInput = page.locator('#raster-input');
    await fileInput.setInputFiles({
      name: 'test.tif',
      mimeType: 'image/tiff',
      buffer: Buffer.from('II\\x2a\\x00 test')
    });

    await page.waitForTimeout(500);
    await expect(uploadButton).not.toHaveClass(/hidden/);
  });

  test('кнопка загрузки дрона должна появляться при выборе файла', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    const uploadButton = page.locator('#drone-upload-button');
    await expect(uploadButton).toBeHidden();

    // Выбираем файл
    const fileInput = page.locator('#drone-input');
    await fileInput.setInputFiles({
      name: 'drone_photos.zip',
      mimeType: 'application/zip',
      buffer: Buffer.from('PK drone')
    });

    await page.waitForTimeout(500);
    await expect(uploadButton).not.toHaveClass(/hidden/);
  });

  test('drone upload должен иметь dropdown поля', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    // Проверяем что dropdown поля существует
    await expect(page.locator('#drone-field-select')).toBeVisible();
    // Проверяем что выбор культуры существует
    await expect(page.locator('#drone-crop-type')).toBeVisible();
  });
});
