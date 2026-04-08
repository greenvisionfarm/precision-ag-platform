/**
 * Регрессионный тест для бага: после логина таблица полей не загружается.
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Таблица полей после авторизации', () => {
  test('должна показывать DataTables после перехода на #fields', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Логируем консоль браузера
    page.on('console', msg => {
      console.log(`[BROWSER ${msg.type()}] ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.log(`[BROWSER ERROR] ${err.message}`);
    });

    // Переходим на страницу полей
    await page.goto('/#fields');
    await page.waitForTimeout(3000);

    // Проверяем что handleRoute вызвался (data-route на body)
    const bodyRoute = await page.locator('body').getAttribute('data-route');
    console.log('body data-route:', bodyRoute);

    // Если #fields не виден — кликаем на навигацию
    const fieldsVisible = await page.locator('#view-fields').isVisible().catch(() => false);
    if (!fieldsVisible) {
      await page.locator('.nav-link[href="#fields"]').click();
      await page.waitForTimeout(1000);
    }

    // Проверяем что #view-fields видим
    await expect(page.locator('#view-fields')).toBeVisible({ timeout: 5000 });

    // Проверяем что таблица есть в DOM
    await expect(page.locator('#fields-table')).toBeAttached({ timeout: 5000 });

    // Ждём DataTables wrapper
    await expect(page.locator('div.dataTables_wrapper').first()).toBeVisible({ timeout: 10000 });
  });
});
