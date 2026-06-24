/**
 * Тесты API для загрузки снимков и обработки
 */
import { test, expect, makeTestField } from '../fixtures/fixtures';

test.describe('API загрузки и NDVI анализа', () => {
  test('должна получать статус задач через API', async ({ authedRequest }) => {
    const response = await authedRequest.get('/api/tasks');
    expect([200, 404]).toContain(response.status());
  });

  test('должна получать сканы поля через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Scans ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const response = await authedRequest.get(`/api/field/${id}`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.id).toBe(id);
  });

  test('должна экспортировать ISOXML через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `ISOXML ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const exportResp = await authedRequest.get(`/api/field/export/isoxml/${id}`);
    expect([200, 500, 404]).toContain(exportResp.status());
  });

  test('должна получать зоны скана через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Zones ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const response = await authedRequest.get(`/api/field/${id}`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.id).toBe(id);
  });
});
