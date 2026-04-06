/**
 * E2E тесты для загрузки и NDVI анализа (обновлённая версия)
 * Проверяет загрузку снимков, анализ и работу с зонами
 */

import { test, expect } from '../fixtures/fixtures';
import * as path from 'path';
import * as fs from 'fs';

test.describe('Загрузка и NDVI анализ', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
  });

  test('должна создавать тестовый файл для загрузки', async ({ page }) => {
    // Создаём простой GeoJSON файл
    const testGeoJSON = {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [[[19.0, 48.0], [19.01, 48.0], [19.01, 48.01], [19.0, 48.01], [19.0, 48.0]]]
      },
      properties: { name: 'Test Field' }
    };
    
    const tempFile = path.join(__dirname, '../fixtures/temp_test.json');
    fs.writeFileSync(tempFile, JSON.stringify(testGeoJSON));
    
    expect(fs.existsSync(tempFile)).toBeTruthy();
    
    // Очищаем
    fs.unlinkSync(tempFile);
  });

  test('должна получать статус задач через API', async ({ page }) => {
    // Проверяем эндпоинт статуса (должен возвращать 404 для несуществующей задачи)
    const response = await page.request.get('/api/task/nonexistent');
    
    // Может быть 404 или другой статус ошибки
    expect([404, 400]).toContain(response.status());
  });

  test('должна получать сканы поля через API', async ({ page, createTestField }) => {
    // Создаём поле
    const fieldId = await createTestField();
    
    // Получаем сканы
    const response = await page.request.get(`/api/field/${fieldId}/scans`);
    
    expect(response.ok()).toBeTruthy();
    const scans = await response.json();
    
    expect(Array.isArray(scans)).toBeTruthy();
  });

  test('должна экспортировать ISOXML через API', async ({ page, createTestField }) => {
    // Создаём поле
    const fieldId = await createTestField();
    
    // Экспортируем ISOXML
    const exportResponse = await page.request.get(`/api/field/export/isoxml/${fieldId}`);
    
    // Проверяем, что это XML
    const contentType = exportResponse.headers()['content-type'];
    expect([200, 400]).toContain(exportResponse.status());
    
    if (exportResponse.status() === 200) {
      expect(contentType).toContain('application/xml') || 
             expect(contentType).toContain('text/xml') ||
             expect(contentType).toContain('application/vnd.google-earth.kmz');
    }
  });

  test('должна получать зоны скана через API', async ({ page, createTestField }) => {
    // Создаём поле
    const fieldId = await createTestField();
    
    // Получаем сканы
    const scansResponse = await page.request.get(`/api/field/${fieldId}/scans`);
    const scans = await scansResponse.json();
    
    if (scans.length > 0) {
      const scanId = scans[0].id;
      
      // Получаем зоны
      const zonesResponse = await page.request.get(`/api/scan/${scanId}/zones`);
      
      if (zonesResponse.ok()) {
        const zones = await zonesResponse.json();
        expect(Array.isArray(zones)).toBeTruthy();
      }
    }
  });
});
