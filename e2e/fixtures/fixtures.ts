/**
 * Базовые фикстуры и утилиты для E2E тестов Field Mapper
 */

import { test as base, expect } from '@playwright/test';
import type { Page, APIRequestContext, BrowserContext } from '@playwright/test';

/**
 * Тестовые данные для авторизации
 */
export const TEST_USER = {
  email: 'test_e2e@example.com',
  password: 'TestPassword123!',
  firstName: 'Test',
  lastName: 'User',
};

/**
 * Тестовые данные для поля
 */
export const TEST_FIELD = {
  name: 'Тестовое Поле E2E',
  geometry: {
    type: 'Polygon',
    coordinates: [[[19.0, 48.0], [19.01, 48.0], [19.01, 48.01], [19.0, 48.01], [19.0, 48.0]]],
  },
};

/**
 * Тестовые данные для владельца
 */
export const TEST_OWNER = {
  name: 'Тестовый Владелец E2E',
};

/**
 * Логин через API request context
 */
async function apiLogin(request: APIRequestContext): Promise<boolean> {
  const response = await request.post('/api/auth/login', {
    data: {
      email: TEST_USER.email,
      password: TEST_USER.password,
    },
  });
  return response.ok();
}

/**
 * Расширенный тест с базовыми фикстурами
 */
export const test = base.extend<{
  page: Page;
  authedRequest: APIRequestContext;
  authenticatedPage: Page;
  loginTestUser: () => Promise<void>;
  logout: () => Promise<void>;
  createTestField: (fieldData?: Partial<typeof TEST_FIELD>) => Promise<number>;
  createTestOwner: (ownerData?: Partial<typeof TEST_OWNER>) => Promise<number>;
  takeScreenshot: (name: string) => Promise<void>;
}>({
  page: async ({ browser }, use) => {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Авторизованный API request context с cookie
   */
  authedRequest: async ({ browser }, use) => {
    const context = await browser.newContext();
    const request = context.request;
    
    // Логинимся через API — cookie автоматически сохранятся в контекст
    await apiLogin(request);
    
    await use(request);
    await context.close();
  },

  /**
   * Страница с авторизованным пользователем
   */
  authenticatedPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
    });
    
    // Логинимся через API в этом контексте
    await apiLogin(context.request);
    
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Фикстура для входа тестового пользователя через UI
   */
  loginTestUser: async ({ page }, use) => {
    const loginFn = async () => {
      await page.goto('/');
      await page.waitForTimeout(500);
      
      const emailInput = page.locator('input[type="email"], input[name="email"]').first();
      const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
      const loginButton = page.locator('button:has-text("Войти"), button[type="submit"]').first();
      
      if (await emailInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await emailInput.fill(TEST_USER.email);
        await passwordInput.fill(TEST_USER.password);
        await loginButton.click();
        await page.waitForTimeout(1000);
      }
    };
    await use(loginFn);
  },

  /**
   * Фикстура для выхода
   */
  logout: async ({ page }, use) => {
    const logoutFn = async () => {
      try {
        await page.request.post('/api/auth/logout');
      } catch (e) {
        // ignore
      }
    };
    await use(logoutFn);
  },

  /**
   * Создание тестового поля через API с авторизацией
   */
  createTestField: async ({ authedRequest }, use) => {
    const createFieldFn = async (fieldData?: Partial<typeof TEST_FIELD>) => {
      const data = { ...TEST_FIELD, ...fieldData };
      const response = await authedRequest.post('/api/field/add', {
        data: data,
      });
      expect(response.ok(), `createField failed: ${await response.text()}`).toBeTruthy();
      const result = await response.json();
      return result.id;
    };
    await use(createFieldFn);
  },

  /**
   * Создание тестового владельца через API с авторизацией
   */
  createTestOwner: async ({ authedRequest }, use) => {
    const createOwnerFn = async (ownerData?: Partial<typeof TEST_OWNER>) => {
      const data = { ...TEST_OWNER, ...ownerData };
      const response = await authedRequest.post('/api/owner/add', {
        data: data,
      });
      expect(response.ok(), `createOwner failed: ${await response.text()}`).toBeTruthy();
      const result = await response.json();
      return result.id;
    };
    await use(createOwnerFn);
  },

  /**
   * Сделать скриншот с именем
   */
  takeScreenshot: async ({ page }, use) => {
    const screenshotFn = async (name: string) => {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `e2e/results/${timestamp}_${name}.png`;
      await page.screenshot({ path: filename, fullPage: true }).catch(() => {});
      return filename;
    };
    await use(screenshotFn);
  },
});

/**
 * Экспорт expect для удобного импорта
 */
export { expect };
