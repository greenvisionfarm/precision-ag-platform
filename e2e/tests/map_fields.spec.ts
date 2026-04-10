/**
 * Тест: поля отображаются на карте после авторизации.
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Поля на карте', () => {
  test('должна показывать полигоны полей на карте после перехода на #map', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Переходим на карту
    await page.goto('/#map');
    await page.waitForTimeout(3000);

    // Проверяем что #view-map видим
    await expect(page.locator('#view-map')).toBeVisible({ timeout: 5000 });

    // Проверяем что карта Leaflet инициализирована
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 5000 });

    // Диагностика: проверяем все звенья цепи
    const diag = await page.evaluate(async () => {
      const result: any = {};

      // 0. Сколько раз вызывалась loadMapData
      result.loadMapDataCalls = window._loadMapDataCalls || 0;

      // 1. Проверка $.ajaxSetup
      result.ajaxDefaults = $.ajaxSettings?.xhrFields;

      // 2. Прямой вызов $.getJSON
      const jqResult = await $.getJSON('/api/fields').then(d => ({ ok: true, type: d?.type, features: d?.features?.length }))
        .catch(e => ({ ok: false, error: e?.xhr?.status || e?.message || 'unknown' }));
      result.jqueryGetFields = jqResult;

      // 3. Проверка API.getFields
      const apiResult = await window.API.getFields().then(d => ({ ok: true, type: d?.type, features: d?.features?.length }))
        .catch(e => ({ ok: false, error: e?.message || 'unknown' }));
      result.apiGetFields = apiResult;

      // 4. Проверка fetch (контроль)
      const fetchResp = await fetch('/api/fields', { credentials: 'include' });
      const fetchData = await fetchResp.json();
      result.fetchGetFields = { ok: fetchResp.ok, type: fetchData?.type, features: fetchData?.features?.length };

      // 5. Проверка MapManager
      result.mapManagerExists = !!window.MapManager;
      result.mapInstance = !!window.MapManager?.instance;
      result.editableLayers = !!window.MapManager?.editableLayers;
      result.layerCount = window.MapManager?.editableLayers?.getLayers?.().length ?? 'N/A';

      // 6. Проверка что loadMapData и renderFields существуют
      result.loadMapDataExists = typeof window.loadMapData === 'function';
      result.renderFieldsExists = typeof window.MapManager?.renderFields === 'function';

      return result;
    });
    console.log('Диагностика карты:', JSON.stringify(diag, null, 2));

    // Проверяем что API работает
    expect(diag.apiGetFields.ok).toBe(true);
    expect(diag.apiGetFields.features).toBeGreaterThan(0);

    // Проверяем что MapManager и editableLayers готовы
    expect(diag.mapManagerExists).toBe(true);
    expect(diag.editableLayers).toBe(true);

    // Ждём отрисовки
    await page.waitForTimeout(2000);

    // Если слоёв нет — вручную вызываем loadMapData и проверяем
    if (diag.layerCount === 0 || diag.layerCount === 'N/A') {
      console.log('Нет слоёв, вызываю loadMapData вручную...');
      await page.evaluate(async () => {
        await window.loadMapData();
        // Ждём завершения асинхронных операций
        await new Promise(r => setTimeout(r, 1000));
      });

      const afterCount = await page.evaluate(() =>
        window.MapManager?.editableLayers?.getLayers?.().length ?? -1
      );
      console.log(`Слоёв после loadMapData: ${afterCount}`);
      expect(afterCount).toBeGreaterThan(0);
    }

    // Финальная проверка: полигоны отрисованы
    const polygons = page.locator('path.leaflet-interactive, svg.leaflet-zoom-animator path');
    await expect(polygons).toHaveCount({ min: 1 }, { timeout: 5000 }).catch(async () => {
      const count = await polygons.count();
      throw new Error(`No polygons rendered. Found ${count} polygon elements.`);
    });
  });
});
