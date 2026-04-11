/**
 * Тесты страницы детали поля.
 * Проверяют:
 * - Header: кнопка "Назад" НЕ в одном ряду с названием
 * - NDVI сканы отображаются
 * - Кнопки экспорта не в одном ряду
 * - Зоны внесения видны
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Страница детали поля', () => {
  test('должна открывать страницу детали поля через хеш', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    // Кликаем по TD (обработчик на td, не на tr)
    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();

    await page.waitForTimeout(2000);

    await expect(page.locator('#view-field-detail')).toBeVisible({ timeout: 5000 });
  });

  test('header детали не должен быть в одном ряду с back-link', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(2000);

    await expect(page.locator('.back-link')).toBeVisible();

    const headerContainer = page.locator('.detail-header');
    await expect(headerContainer).toBeVisible();

    const headerStyle = await headerContainer.evaluate(el => {
      const style = window.getComputedStyle(el);
      return {
        flexDirection: style.flexDirection,
        display: style.display
      };
    });

    expect(headerStyle.display).toBe('flex');
    expect(headerStyle.flexDirection).toBe('column');
  });

  test('NDVI сканы должны отображаться на странице детали', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(3000);

    const scansSelector = page.locator('#scans-selector');
    const exists = await scansSelector.count();
    expect(exists).toBeGreaterThan(0);
  });

  test('кнопки экспорта должны быть расположены горизонтально', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(2000);

    const fieldActions = page.locator('.field-actions');
    await expect(fieldActions).toBeVisible();

    const actionsStyle = await fieldActions.evaluate(el => window.getComputedStyle(el).display);
    expect(actionsStyle).toBe('flex');

    const buttons = fieldActions.locator('.btn');
    await expect(buttons).toHaveCount(2);
  });

  test('зоны внесения должны отображаться если есть данные', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(3000);

    const zonesStats = page.locator('#zones-stats');
    const visible = await zonesStats.isVisible().catch(() => false);

    if (visible) {
      await expect(page.locator('.zones-table')).toBeVisible();
    }
  });
});
