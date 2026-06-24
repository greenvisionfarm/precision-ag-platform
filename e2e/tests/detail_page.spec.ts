/**
 * Тесты страницы детали поля.
 */
import { test, expect, makeTestField } from '../fixtures/fixtures';

test.describe('Страница детали поля', () => {
  test('должна открывать страницу детали поля через хеш', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Создаём поле через API
    const fieldData = makeTestField({ name: `Detail ${Date.now()}` });
    const createResp = await page.request.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(2000);

    await expect(page.locator('#view-field-detail')).toBeVisible({ timeout: 5000 });
  });

  test('NDVI сканы должны отображаться на странице детали', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    const fieldData = makeTestField({ name: `Scans ${Date.now()}` });
    const createResp = await page.request.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

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

  test('кнопки экспорта должны быть видимы', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    const fieldData = makeTestField({ name: `Export ${Date.now()}` });
    const createResp = await page.request.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(2000);

    await expect(page.locator('#view-field-detail')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#detail-export-kmz')).toBeVisible();
    await expect(page.locator('#detail-export-isoxml')).toBeVisible();
  });

  test('зоны внесения должны отображаться если есть данные', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    const fieldData = makeTestField({ name: `Zones ${Date.now()}` });
    const createResp = await page.request.post('/api/field/add', { data: fieldData });
    const { id } = await createResp.json();

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
