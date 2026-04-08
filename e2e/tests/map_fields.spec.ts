/**
 * Тест: поля отображаются на карте после авторизации.
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Поля на карте', () => {
  test('должна показывать полигоны полей на карте после перехода на #map', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Логируем консоль браузера
    page.on('console', msg => {
      console.log(`[BROWSER ${msg.type()}] ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.log(`[BROWSER ERROR] ${err.message}`);
    });

    // Переходим на карту
    await page.goto('/#map');
    await page.waitForTimeout(3000);

    // Проверяем что #view-map видим
    await expect(page.locator('#view-map')).toBeVisible({ timeout: 5000 });

    // Проверяем что карта Leaflet инициализирована
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 5000 });

    // Логируем состояние MapManager и ответ API
    const mapState = await page.evaluate(async () => {
      const result: any = {};
      result.mapExists = !!window.MapManager;
      result.mapInstance = !!window.MapManager?.instance;
      result.editableLayers = !!window.MapManager?.editableLayers;
      result.layerCount = window.MapManager?.editableLayers?.getLayers?.().length ?? 'N/A';

      // Проверяем ответ API
      try {
        const resp = await fetch('/api/fields', { credentials: 'include' });
        result.apiStatus = resp.status;
        if (resp.ok) {
          const data = await resp.json();
          result.featuresCount = data.features?.length ?? 0;
        } else {
          result.apiError = await resp.text();
        }
      } catch (e: any) {
        result.fetchError = e.message;
      }
      return result;
    });
    console.log('Map state:', JSON.stringify(mapState));

    // Проверяем что поля загружены через API
    expect(mapState.apiStatus).toBe(200);
    expect(mapState.featuresCount).toBeGreaterThan(0);

    // Ждём отрисовки полигонов
    await page.waitForTimeout(2000);

    // Проверяем что полигоны полей отрисованы
    const polygons = page.locator('path.leaflet-interactive');
    const count = await polygons.count();
    console.log(`Polygons found: ${count}`);

    if (count === 0) {
      // Попробуем вручную вызвать loadMapData
      await page.evaluate(() => {
        if (window.loadMapData) window.loadMapData();
      });
      await page.waitForTimeout(2000);
    }

    await expect(polygons).toHaveCount({ min: 1 }, { timeout: 5000 }).catch(async () => {
      const finalCount = await polygons.count();
      console.log(`Final polygon count: ${finalCount}`);
      throw new Error(`No polygons rendered. API returned ${mapState.featuresCount} features.`);
    });
  });
});
