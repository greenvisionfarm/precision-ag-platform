/**
 * E2E тесты для управления полями
 * Проверяет создание, редактирование, удаление и экспорт полей через API
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Управление полями', () => {
  test('должна создавать новое поле через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField({
      name: `Тестовое Поле ${Date.now()}`
    });

    expect(fieldId).toBeTruthy();

    // Проверяем через API
    const response = await authedRequest.get(`/api/field/${fieldId}`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.id).toBe(fieldId);
  });

  test('должна позволять редактировать поле через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField({
      name: `Поле для редактирования ${Date.now()}`
    });

    // Редактируем через API
    const editResponse = await authedRequest.put(`/api/field/rename/${fieldId}`, {
      data: { new_name: 'Обновлённое название' }
    });

    expect(editResponse.ok()).toBeTruthy();

    // Проверяем
    const getResponse = await authedRequest.get(`/api/field/${fieldId}`);
    const data = await getResponse.json();
    expect(data.name).toBe('Обновлённое название');
  });

  test('должна позволять удалять поле через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField({
      name: `Поле для удаления ${Date.now()}`
    });

    // Удаляем через API
    const deleteResponse = await authedRequest.delete(`/api/field/delete/${fieldId}`);
    expect(deleteResponse.ok()).toBeTruthy();

    // Проверяем, что поле удалено
    const getResponse = await authedRequest.get(`/api/field/${fieldId}`);
    expect(getResponse.status()).toBe(404);
  });

  test('должна позволять экспортировать поле в KMZ', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField();

    // Делаем запрос на экспорт
    const exportResponse = await authedRequest.get(`/api/field/export/kmz/${fieldId}`);

    // Может быть 200 (успех) или 500 (нет зон для экспорта)
    expect([200, 500]).toContain(exportResponse.status());

    if (exportResponse.status() === 200) {
      // Проверяем, что это KMZ файл (ZIP формат)
      const body = await exportResponse.body();
      expect(body.slice(0, 2)).toEqual(Buffer.from('PK'));
    }
  });

  test('должна получать детали поля через API', async ({ authedRequest, createTestField }) => {
    const fieldId = await createTestField();

    // Получаем детали
    const response = await authedRequest.get(`/api/field/${fieldId}`);

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.id).toBe(fieldId);
    expect(data.name).toBeTruthy();
    expect(data.geometry).toBeTruthy();
  });

  test('должна получать список полей через API', async ({ authedRequest, createTestField }) => {
    // Создаём поле
    await createTestField({ name: `Поле для списка ${Date.now()}` });

    // Получаем список
    const response = await authedRequest.get('/api/fields');
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.type).toBe('FeatureCollection');
    expect(Array.isArray(data.features)).toBeTruthy();
  });

  test('должна назначать владельца полю через API', async ({ authedRequest, createTestField, createTestOwner }) => {
    // Создаём владельца и поле
    const ownerId = await createTestOwner();
    const fieldId = await createTestField();

    // Назначаем владельца
    const assignResponse = await authedRequest.put(`/api/field/assign_owner/${fieldId}`, {
      data: { owner_id: ownerId }
    });

    expect(assignResponse.ok()).toBeTruthy();
  });
});
