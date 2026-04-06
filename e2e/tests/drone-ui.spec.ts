/**
 * Тесты UI для загрузки снимков с дрона.
 * Делают скриншоты для проверки визуального вида.
 */
import { test, expect } from '../fixtures/fixtures';

test.describe('UI загрузки дронов', () => {
  
  test('должна отображать форму загрузки дронов', async ({ page }) => {
    // Переходим на страницу загрузок
    await page.goto('/#uploads');
    await page.waitForTimeout(1000); // Ждём рендеринга

    // Проверяем наличие карточки загрузки дронов
    const droneCard = page.locator('.upload-card').filter({ hasText: /Обработка снимков с дрона/ });
    await expect(droneCard).toBeVisible();

    // Скриншот всей карточки
    await droneCard.screenshot({ path: 'e2e/results/drone_upload_card.png' });
  });

  test('должна показывать dropdown с культурами', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    // Проверяем dropdown культур
    const cropSelect = page.locator('#drone-crop-type');
    await expect(cropSelect).toBeVisible();

    // Проверяем опции
    const options = await cropSelect.locator('option').all();
    expect(options.length).toBeGreaterThan(5);

    // Скриншот dropdown
    await cropSelect.screenshot({ path: 'e2e/results/drone_crop_select.png' });
  });

  test('должна показывать dropdown с полями', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    const fieldSelect = page.locator('#drone-field-select');
    await expect(fieldSelect).toBeVisible();

    // Проверяем что есть опция "Авто"
    const autoOption = fieldSelect.locator('option').first();
    const text = await autoOption.textContent();
    expect(text).toContain('Авто');

    await fieldSelect.screenshot({ path: 'e2e/results/drone_field_select.png' });
  });

  test('должна отображать кнопку загрузки', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    const uploadButton = page.locator('#drone-upload-button');
    
    // Кнопка скрыта пока не выбран файл
    await expect(uploadButton).toBeHidden();

    // Выбираем файл
    const fileInput = page.locator('#drone-input');
    await fileInput.setInputFiles('e2e/fixtures/test_field.geojson');
    
    // Кнопка должна появиться
    await expect(uploadButton).toBeVisible();
    
    await page.waitForTimeout(500);
    await uploadButton.screenshot({ path: 'e2e/results/drone_upload_button.png' });
  });

  test('должна показывать прогресс бар', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    // Проверяем что прогресс бар есть в DOM (но скрыт)
    const progressDiv = page.locator('#drone-progress');
    await expect(progressDiv).toBeVisible({ visible: false });

    const progressBar = page.locator('.progress-bar');
    await expect(progressBar).toBeInViewport({ ratio: 0 }); // Скрыт

    console.log('Прогресс бар найден');
  });

  test('должна отображать иконку дрона', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    const droneCard = page.locator('.upload-card').filter({ hasText: /Обработка снимков с дрона/ });
    const icon = droneCard.locator('.upload-icon i');
    
    const iconClass = await icon.getAttribute('class');
    expect(iconClass).toContain('fa-plane');

    await droneCard.screenshot({ path: 'e2e/results/drone_card_full.png' });
  });

  test('должна корректно отображаться в тёмной теме', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    // Включаем тёмную тему
    const themeToggle = page.locator('#theme-toggle-btn');
    await themeToggle.click();
    await page.waitForTimeout(500);

    // Проверяем что тема переключилась
    const html = page.locator('html');
    const theme = await html.getAttribute('data-theme');
    expect(theme).toBe('dark');

    // Скриншот в тёмной теме
    await page.screenshot({ path: 'e2e/results/drone_upload_dark_theme.png' });
  });

  test('должна быть адаптивной на мобильных', async ({ page }) => {
    // Устанавливаем мобильный viewport
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE

    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    const droneCard = page.locator('.upload-card').filter({ hasText: /Обработка снимков с дрона/ });
    await expect(droneCard).toBeVisible();

    await page.screenshot({ path: 'e2e/results/drone_upload_mobile.png' });
  });

  test('должна показывать все карточки загрузок', async ({ page }) => {
    await page.goto('/#uploads');
    await page.waitForTimeout(1000);

    // Скриншот всей страницы загрузок
    const uploadsContainer = page.locator('.uploads-container');
    await uploadsContainer.screenshot({ path: 'e2e/results/all_upload_cards.png' });

    // Проверяем что есть 3 карточки
    const cards = page.locator('.upload-card');
    const count = await cards.count();
    expect(count).toBe(3);

    const cardTitles = await cards.allTextContents();
    expect(cardTitles.join(' ')).toContain('Shapefile');
    expect(cardTitles.join(' ')).toContain('дрона');
    expect(cardTitles.join(' ')).toContain('NDVI');
  });
});
