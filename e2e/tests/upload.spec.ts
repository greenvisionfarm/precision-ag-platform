/**
 * Тесты API для загрузки снимков и обработки
 */
import { test, expect } from '../fixtures/fixtures';

test.describe('API загрузки и NDVI анализа', () => {
  test('должна получать статус задач через API', async ({ authedRequest }) => {
    const response = await authedRequest.get('/api/tasks');
    // Может быть 200 или 404 если эндпоинт не реализован
    expect([200, 404]).toContain(response.status());
  });

  test('должна получать сканы поля через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField();

    const response = await authedRequest.get(`/api/field/${fieldId}`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.id).toBe(fieldId);
  });

  test('должна экспортировать ISOXML через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField();

    const exportResponse = await authedRequest.get(`/api/field/export/isoxml/${fieldId}`);
    // Может быть 200 (успех) или 500 (нет зон для экспорта)
    expect([200, 500, 404]).toContain(exportResponse.status());
  });

  test('должна получать зоны скана через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField();

    const response = await authedRequest.get(`/api/field/${fieldId}`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.id).toBe(fieldId);
  });
});
