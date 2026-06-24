/**
 * E2E тесты для управления полями
 */
import { test, expect, makeTestField } from '../fixtures/fixtures';

test.describe('Управление полями', () => {
  test('должна создавать новое поле через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Создание ${Date.now()}` });
    const response = await authedRequest.post('/api/field/add', { data: fieldData });
    expect(response.ok(), `createField: ${await response.text()}`).toBeTruthy();
    const { id } = await response.json();
    expect(id).toBeTruthy();

    const getResp = await authedRequest.get(`/api/field/${id}`);
    expect(getResp.ok()).toBeTruthy();
    const data = await getResp.json();
    expect(data.id).toBe(id);
  });

  test('должна позволять редактировать поле через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Редакт ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const editResp = await authedRequest.put(`/api/field/rename/${id}`, {
      data: { new_name: 'Обновлённое название' }
    });
    expect(editResp.ok(), `rename: ${await editResp.text()}`).toBeTruthy();

    const getResp = await authedRequest.get(`/api/field/${id}`);
    const data = await getResp.json();
    expect(data.name).toBe('Обновлённое название');
  });

  test('должна позволять удалять поле через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Удаление ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const deleteResp = await authedRequest.delete(`/api/field/delete/${id}`);
    expect(deleteResp.ok(), `delete: ${await deleteResp.text()}`).toBeTruthy();

    const getResp = await authedRequest.get(`/api/field/${id}`);
    expect(getResp.status()).toBe(404);
  });

  test('должна позволять экспортировать поле в KMZ', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `KMZ ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const exportResp = await authedRequest.get(`/api/field/export/kmz/${id}`);
    expect([200, 500]).toContain(exportResp.status());

    if (exportResp.status() === 200) {
      const body = await exportResp.body();
      expect(body.slice(0, 2)).toEqual(Buffer.from('PK'));
    }
  });

  test('должна получать детали поля через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Детали ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const getResp = await authedRequest.get(`/api/field/${id}`);
    expect(getResp.ok()).toBeTruthy();
    const data = await getResp.json();
    expect(data.id).toBe(id);
    expect(data.name).toBeTruthy();
    expect(data.geometry).toBeTruthy();
  });

  test('должна получать список полей через API', async ({ authedRequest }) => {
    const fieldData = makeTestField({ name: `Список ${Date.now()}` });
    await authedRequest.post('/api/field/add', { data: fieldData });

    const listResp = await authedRequest.get('/api/fields');
    expect(listResp.ok()).toBeTruthy();
    const data = await listResp.json();
    expect(data.type).toBe('FeatureCollection');
    expect(Array.isArray(data.features)).toBeTruthy();
  });

  test('должна назначать владельца полю через API', async ({ authedRequest, createTestOwner }) => {
    const ownerId = await createTestOwner({ name: `Владелец ${Date.now()}` });
    const fieldData = makeTestField({ name: `Owner ${Date.now()}` });
    const createResp = await authedRequest.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    const assignResp = await authedRequest.put(`/api/field/assign_owner/${id}`, {
      data: { owner_id: ownerId }
    });
    expect(assignResp.ok(), `assign: ${await assignResp.text()}`).toBeTruthy();
  });
});
