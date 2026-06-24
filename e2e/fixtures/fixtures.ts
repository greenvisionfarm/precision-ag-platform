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
 * Тестовые данные для поля (уникальные координаты чтобы не конфликтовать)
 */
export function makeTestField(overrides?: Partial<typeof TEST_FIELD_BASE>) {
  const ts = Date.now();
  const base = 48.0 + (ts % 1000) * 0.00001;
  const lon = 19.0 + (ts % 777) * 0.00001;
  return {
    ...TEST_FIELD_BASE,
    name: `E2E Поле ${ts}`,
    geometry: {
      type: 'Polygon' as const,
      coordinates: [[[lon, base], [lon + 0.01, base], [lon + 0.01, base + 0.01], [lon, base + 0.01], [lon, base]]],
    },
    ...overrides,
  };
}

const TEST_FIELD_BASE = {
  name: 'Тестовое Поле E2E',
  geometry: {
    type: 'Polygon' as const,
    coordinates: [[[19.0, 48.0], [19.01, 48.0], [19.01, 48.01], [19.0, 48.01], [19.0, 48.0]]],
  },
};

/** @deprecated Use makeTestField() instead to avoid coordinate conflicts */
export const TEST_FIELD = TEST_FIELD_BASE;

/**
 * Тестовые данные для владельца
 */
export const TEST_OWNER = {
  name: 'Тестовый Владелец E2E',
};

/**
 * Логин через API request context.
 * Если пользователь не существует — регистрирует его автоматически.
 */
async function apiLogin(request: APIRequestContext, baseURL?: string): Promise<boolean> {
  const base = baseURL || '';
  const response = await request.post(`${base}/api/auth/login`, {
    data: {
      email: TEST_USER.email,
      password: TEST_USER.password,
    },
  });
  if (response.ok()) return true;

  // Пользователь не найден — регистрируем
  const regResp = await request.post(`${base}/api/auth/register`, {
    data: {
      email: TEST_USER.email,
      password: TEST_USER.password,
      first_name: TEST_USER.firstName,
      last_name: TEST_USER.lastName,
      company_name: 'E2E Test Company',
    },
  });
  if (!regResp.ok()) return false;

  // Логинимся после регистрации
  const loginResp = await request.post(`${base}/api/auth/login`, {
    data: {
      email: TEST_USER.email,
      password: TEST_USER.password,
    },
  });
  return loginResp.ok();
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
  page: async ({ browser, baseURL }, use) => {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      baseURL,
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Авторизованный API request context с cookie
   */
  authedRequest: async ({ browser, baseURL }, use) => {
    const context = await browser.newContext({ baseURL });
    const request = context.request;
    
    // Логинимся через API — cookie автоматически сохранятся в контекст
    await apiLogin(request, baseURL);
    
    await use(request);
    await context.close();
  },

  /**
   * Страница с авторизованным пользователем
   */
  authenticatedPage: async ({ browser, baseURL }, use) => {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      baseURL,
    });
    
    // Логинимся через API в этом контексте
    await apiLogin(context.request, baseURL);
    
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Фикстура для входа тестового пользователя через UI
   */
  loginTestUser: async ({ page, baseURL }, use) => {
    const loginFn = async () => {
      await page.goto(`${baseURL || ''}/`);
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
  logout: async ({ page, baseURL }, use) => {
    const logoutFn = async () => {
      try {
        await page.request.post(`${baseURL || ''}/api/auth/logout`);
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
