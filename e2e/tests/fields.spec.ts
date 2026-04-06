/**
 * E2E тесты для управления полями (обновлённая версия)
 * Проверяет создание, редактирование, удаление и экспорт полей
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Управление полями', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000); // Ждём загрузки карты
  });

  test('должна отображать карту полей', async ({ page, takeScreenshot }) => {
    // Проверяем наличие карты
    const mapContainer = page.locator('#map');
    await expect(mapContainer).toBeVisible();
    
    // Проверяем, что карта загрузилась (есть элементы Leaflet)
    const mapTiles = page.locator('.leaflet-tile-container');
    await expect(mapTiles.first()).toBeVisible({ timeout: 10000 });
    
    // Скриншот карты
    await takeScreenshot('fields_map');
  });

  test('должна показывать список полей', async ({ page, takeScreenshot }) => {
    // Ищем навигацию и кликаем на "Список полей"
    const navLinks = page.locator('.nav-link');
    const fieldsLink = navLinks.filter({ hasText: /Поля|Список|Fields/i }).first();
    
    if (await fieldsLink.isVisible()) {
      await fieldsLink.click();
      await page.waitForTimeout(1000);
    }
    
    // Проверяем наличие таблицы или списка
    const table = page.locator('table, .data-table, [data-testid="fields-table"], #fields-list').first();
    await expect(table).toBeVisible({ timeout: 5000 });
    
    // Скриншот списка полей
    await takeScreenshot('fields_list');
  });

  test('должна создавать новое поле через API и отображать в списке', async ({ page, takeScreenshot, createTestField }) => {
    // Создаём поле через API
    const fieldId = await createTestField({
      name: `Тестовое Поле ${Date.now()}`
    });
    
    expect(fieldId).toBeTruthy();
    
    // Обновляем страницу
    await page.reload();
    await page.waitForTimeout(1000);
    
    // Скриншот с новым полем
    await takeScreenshot('field_created_api');
    
    // Проверяем, что поле появилось (хотя бы в DOM)
    const pageContent = await page.content();
    expect(pageContent).toContain('Тестовое Поле');
  });

  test('должна позволять редактировать поле через API', async ({ page, createTestField }) => {
    // Создаём поле через API
    const fieldId = await createTestField({
      name: `Поле для редактирования ${Date.now()}`
    });
    
    // Редактируем через API
    const editResponse = await page.request.put(`/api/field/rename/${fieldId}`, {
      json: { new_name: 'Обновлённое название' }
    });
    
    expect(editResponse.ok()).toBeTruthy();
    
    // Обновляем страницу и проверяем
    await page.reload();
    await page.waitForTimeout(1000);
    
    const pageContent = await page.content();
    expect(pageContent).toContain('Обновлённое название');
  });

  test('должна позволять удалять поле через API', async ({ page, createTestField }) => {
    // Создаём поле через API
    const fieldId = await createTestField({
      name: `Поле для удаления ${Date.now()}`
    });
    
    // Удаляем через API
    const deleteResponse = await page.request.delete(`/api/field/delete/${fieldId}`);
    
    expect(deleteResponse.ok()).toBeTruthy();
    
    // Проверяем, что поле удалено
    const getResponse = await page.request.get(`/api/field/${fieldId}`);
    expect(getResponse.status()).toBe(404);
  });

  test('должна позволять экспортировать поле в KMZ', async ({ page, createTestField }) => {
    // Создаём поле через API
    const fieldId = await createTestField();
    
    // Делаем запрос на экспорт
    const exportResponse = await page.request.get(`/api/field/export/kmz/${fieldId}`);
    
    // Проверяем, что это KMZ файл
    expect(exportResponse.headers()['content-type']).toContain('application/vnd.google-earth.kmz');
    expect(exportResponse.ok()).toBeTruthy();
    
    // Проверяем, что это ZIP файл (KMZ это ZIP)
    const body = await exportResponse.body();
    expect(body.slice(0, 2)).toEqual(Buffer.from('PK'));
  });

  test('должна получать детали поля через API', async ({ page, createTestField }) => {
    // Создаём поле через API
    const fieldId = await createTestField();
    
    // Получаем детали
    const response = await page.request.get(`/api/field/${fieldId}`);
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.id).toBe(fieldId);
    expect(data.name).toBeTruthy();
    expect(data.geometry).toBeTruthy();
    expect(data.area).toBeTruthy();
  });

  test('должна назначать владельца полю через API', async ({ page, createTestField, createTestOwner }) => {
    // Создаём владельца и поле
    const ownerId = await createTestOwner();
    const fieldId = await createTestField();
    
    // Назначаем владельца
    const assignResponse = await page.request.put(`/api/field/assign_owner/${fieldId}`, {
      json: { owner_id: ownerId }
    });
    
    expect(assignResponse.ok()).toBeTruthy();
    
    // Проверяем, что владелец назначен
    const fieldResponse = await page.request.get(`/api/field/${fieldId}`);
    const data = await fieldResponse.json();
    
    expect(data.owner_id).toBe(ownerId);
  });
});
