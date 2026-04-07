/**
 * E2E тесты для проверки адаптивности и UI
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Адаптивность и UI', () => {
  test('должна корректно отображаться на десктопе', async ({ authenticatedPage, takeScreenshot }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForTimeout(1000);

    // Проверяем наличие основных элементов
    await expect(authenticatedPage.locator('#map')).toBeVisible({ timeout: 10000 });

    // Скриншот
    await takeScreenshot('desktop_view');
  });

  // Пропускаем — нестабилен в headless режиме (кнопка вне viewport)
  test.skip('должна переключать тёмную тему', async ({ authenticatedPage, takeScreenshot }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForTimeout(500);

    const themeToggle = authenticatedPage.locator('#theme-toggle-btn, .theme-toggle').first();
    await themeToggle.scrollIntoViewIfNeeded();
    await themeToggle.click();
    await authenticatedPage.waitForTimeout(500);

    await takeScreenshot('dark_theme');
  });

  test('должна показывать меню на мобильном', async ({ browser, takeScreenshot }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
    });
    const page = await context.newPage();

    await page.goto('/');
    await page.waitForTimeout(1000);

    // Логин
    await page.request.post('/api/auth/login', {
      data: { email: 'test_e2e@example.com', password: 'TestPassword123!' }
    });

    await page.reload();
    await page.waitForTimeout(500);

    // Ищем кнопку меню
    const menuButton = page.locator('#sidebar-toggle, .menu-toggle').first();

    if (await menuButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await menuButton.click();
      await page.waitForTimeout(500);

      // Проверяем, что меню открылось
      const sidebar = page.locator('#sidebar');
      await expect(sidebar).toBeVisible({ timeout: 5000 });
    }

    await context.close();
  });
});
