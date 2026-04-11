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

    // Переходим на страницу полей — handleRoute по хешу должен показать view
    await page.goto('/#fields');
    await page.waitForTimeout(3000);

    // Проверяем что handleRoute вызвался (data-route на body)
    const bodyRoute = await page.locator('body').getAttribute('data-route');
    console.log('body data-route:', bodyRoute);

    // Проверяем что #view-fields видим (роутер должен показать его по хешу)
    await expect(page.locator('#view-fields')).toBeVisible({ timeout: 5000 });

    // Проверяем что таблица есть в DOM
    await expect(page.locator('#fields-table')).toBeAttached({ timeout: 5000 });

    // Ждём DataTables wrapper
    await expect(page.locator('div.dataTables_wrapper').first()).toBeVisible({ timeout: 10000 });
  });
});
