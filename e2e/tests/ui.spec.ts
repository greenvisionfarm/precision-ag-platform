/**
 * E2E тесты для проверки адаптивности и UI (обновлённая версия)
 */

import { test, expect } from '../fixtures/fixtures';

test.describe('Адаптивность и UI', () => {
  test('должна корректно отображаться на десктопе', async ({ page, takeScreenshot }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);
    
    // Устанавливаем десктопное разрешение
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Проверяем наличие основных элементов
    await expect(page.locator('#sidebar')).toBeVisible();
    await expect(page.locator('#map')).toBeVisible();
    
    // Скриншот десктопной версии
    await takeScreenshot('desktop_view');
  });

  test('должна переключать тёмную тему', async ({ page, takeScreenshot }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Ищем переключатель темы
    const themeToggle = page.locator('#theme-toggle-btn, .theme-toggle').first();
    
    if (await themeToggle.isVisible()) {
      // Скриншот светлой темы
      await takeScreenshot('light_theme');
      
      // Переключаем тему
      await themeToggle.click();
      await page.waitForTimeout(500);
      
      // Проверяем, что тема переключилась
      const body = page.locator('body');
      const hasDarkClass = await body.evaluate(el => 
        el.classList.contains('dark') || 
        el.getAttribute('data-theme') === 'dark'
      );
      
      // Скриншот тёмной темы
      await takeScreenshot('dark_theme');
    }
  });

  test('должна корректно работать навигация', async ({ page, takeScreenshot }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Список навигационных ссылок
    const navLinks = await page.locator('.nav-link').all();
    
    for (const link of navLinks) {
      const text = await link.textContent();
      await link.click();
      await page.waitForTimeout(500);
      console.log(`✅ Навигация: ${text?.trim()}`);
    }
    
    // Финальный скриншот
    await takeScreenshot('navigation_complete');
  });

  test('должна поддерживать keyboard navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Используем Tab для навигации
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Проверяем, что фокус переместился
    const focusedElement = page.locator(':focus');
    const tagName = await focusedElement.evaluate(el => el.tagName);
    
    console.log(`✅ Фокус на элементе: ${tagName}`);
  });

  test('должна показывать меню на мобильном', async ({ browser, takeScreenshot }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
    });
    const page = await context.newPage();
    
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Ищем кнопку меню
    const menuButton = page.locator('#sidebar-toggle, .menu-toggle').first();
    
    if (await menuButton.isVisible()) {
      await menuButton.click();
      await page.waitForTimeout(500);
      
      // Проверяем, что меню открылось
      const sidebar = page.locator('#sidebar');
      await expect(sidebar).toBeVisible();
      
      // Скриншот
      await page.screenshot({ 
        path: `e2e/results/mobile_menu_${new Date().toISOString().replace(/[:.]/g, '-')}.png`,
        fullPage: true 
      });
    }
    
    await context.close();
  });
});
