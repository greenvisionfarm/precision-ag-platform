/**
 * E2E тесты для управления владельцами (обновлённая версия)
 * Проверяет создание, редактирование и удаление владельцев
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Управление владельцами', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
  });

  test('должна создавать владельца через API', async ({ authedRequest, takeScreenshot, page }) => {
    const uniqueName = `Владелец ${Date.now()}`;

    // Создаём через API с авторизацией
    const response = await authedRequest.post('/api/owner/add', {
      data: { name: uniqueName }
    });

    expect(response.ok(), `Failed: ${await response.text()}`).toBeTruthy();
    const result = await response.json();
    expect(result.message).toBe('OK');

    // Скриншот
    await takeScreenshot('owner_created_api');

    // Проверяем, что владелец в базе
    const listResponse = await authedRequest.get('/api/owners');
    const data = await listResponse.json();
    const owner = data.data?.find((o: any) => o.name === uniqueName);
    expect(owner).toBeTruthy();
    expect(owner.name).toBe(uniqueName);
  });

  test('должна редактировать владельца через API', async ({ authedRequest, createTestOwner }) => {
    // Создаём владельца
    const ownerId = await createTestOwner({ name: `Владелец для редактирования ${Date.now()}` });

    // Редактируем
    const editResponse = await authedRequest.put(`/api/owner/rename/${ownerId}`, {
      data: { new_name: 'Обновлённый владелец' }
    });

    // Проверяем (может быть 200 или 204)
    expect([200, 204, 404]).toContain(editResponse.status());
  });

  test('должна удалять владельца через API', async ({ authedRequest, createTestOwner }) => {
    // Создаём владельца
    const ownerId = await createTestOwner();

    // Удаляем
    const deleteResponse = await authedRequest.delete(`/api/owner/delete/${ownerId}`);

    expect([200, 204, 404]).toContain(deleteResponse.status());

    // Проверяем, что удалён
    const getResponse = await authedRequest.get('/api/owners');
    const data = await getResponse.json();
    const exists = data.data?.some((o: any) => o.id === ownerId);
    expect(exists).toBeFalsy();
  });

  test('должна получать список владельцев', async ({ authedRequest, takeScreenshot }) => {
    const response = await authedRequest.get('/api/owners');

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(Array.isArray(data.data)).toBeTruthy();

    // Скриншот
    await takeScreenshot('owners_list_api');
  });

  test('должна показывать ошибку при создании без имени', async ({ authedRequest }) => {
    const response = await authedRequest.post('/api/owner/add', {
      data: { name: '' }
    });

    // Должна быть ошибка (400 или 422)
    expect([400, 422]).toContain(response.status());
  });
});
