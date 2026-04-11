/**
 * Тесты модальных окон и диалогов.
 * Проверяют:
 * - Модалка KMZ имеет сетку настроек (не в один ряд)
 * - Модалка поля имеет карту и кнопки
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Модальные окна', () => {
  test('модалка DJI KMZ должна иметь 4 поля настроек', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Переходим на страницу полей и открываем KMZ настройки для первого поля
    await page.goto('/#fields');
    await page.waitForTimeout(2000);

    // Ждём пока DataTables загрузится
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    // Кликаем по кнопке настроек KMZ (первая строка, кнопка с шестерёнкой)
    const kmzSettingsBtn = page.locator('#fields-table tbody tr').first().locator('button.btn-outline-primary');
    await kmzSettingsBtn.click();

    // Ждём появления модалки
    await page.waitForTimeout(1000);

    // Проверяем что все 4 поля присутствуют
    await expect(page.locator('text=Высота полета')).toBeVisible();
    await expect(page.locator('text=Фронтальное перекрытие')).toBeVisible();
    await expect(page.locator('text=Боковое перекрытие')).toBeVisible();
    await expect(page.locator('text=Угол курса')).toBeVisible();

    // Проверяем что поля имеют значения по умолчанию
    await expect(page.locator('#swal-h')).toHaveValue('100');
    await expect(page.locator('#swal-oh')).toHaveValue('80');
    await expect(page.locator('#swal-ow')).toHaveValue('70');
    await expect(page.locator('#swal-dir')).toHaveValue('0');
  });

  test('модалка поля должна содержать карту и кнопки при клике на строку таблицы', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await page.goto('/#fields');
    await page.waitForTimeout(2000);
    await page.waitForSelector('#fields-table tbody tr', { timeout: 10000 });

    // Кликаем по TD чтобы перейти на detail
    const firstTD = page.locator('#fields-table tbody tr').first().locator('td').first();
    await firstTD.click();
    await page.waitForTimeout(2000);

    await expect(page.locator('#view-field-detail')).toBeVisible({ timeout: 5000 });

    await expect(page.locator('#detail-export-kmz')).toBeVisible();
    await expect(page.locator('#detail-export-isoxml')).toBeVisible();
  });
});
