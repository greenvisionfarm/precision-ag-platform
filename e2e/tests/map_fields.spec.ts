/**
 * Тест: поля отображаются на карте после авторизации.
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Поля на карте', () => {
  test('должна показывать полигоны полей на карте после перехода на #map', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Переходим на карту
    await page.goto('/#map');
    await page.waitForTimeout(2000);

    // Проверяем что #view-map видим
    await expect(page.locator('#view-map')).toBeVisible({ timeout: 5000 });

    // Проверяем что карта Leaflet инициализирована
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 5000 });

    // Проверяем что данные полей загружены (editableLayers содержит слои)
    const layerCount = await page.evaluate(() =>
      window.MapManager?.editableLayers?.getLayers?.().length ?? -1
    );
    expect(layerCount).toBeGreaterThan(0);

    // Проверяем что полигоны отрисованы в DOM (SVG path внутри leaflet overlay pane)
    const polygons = page.locator('.leaflet-overlay-pane svg path');
    const count = await polygons.count();
    expect(count).toBeGreaterThan(0);
  });
});
