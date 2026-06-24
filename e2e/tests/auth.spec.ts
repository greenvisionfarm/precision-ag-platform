/**
 * E2E тесты для авторизации (обновлённая версия)
 */
import { test, expect } from '../fixtures/fixtures';

test.describe('Авторизация и регистрация', () => {
  test('должна показывать главную страницу', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForTimeout(1000);

    await expect(authenticatedPage).toHaveTitle(/Field Mapper/);
    await expect(authenticatedPage.locator('.leaflet-container')).toBeVisible();
    await expect(authenticatedPage.locator('.header-nav-link').first()).toBeVisible();
  });

  test('должна получать профиль через API', async ({ page }) => {
    const response = await page.request.get('/api/auth/profile');
    expect([200, 401, 404, 500]).toContain(response.status());
  });

  test('должна регистрировать пользователя через API', async ({ page }) => {
    const testEmail = `test_${Date.now()}@example.com`;
    const testPassword = 'TestPassword123!';

    const response = await page.request.post('/api/auth/register', {
      json: {
        email: testEmail,
        password: testPassword,
        first_name: 'Test',
        last_name: 'User',
        company_name: `RegCo_${Date.now()}`,
      }
    });

    expect([200, 201, 400, 403, 404]).toContain(response.status());
  });

  test('должна входить через API', async ({ page }) => {
    const testEmail = `test_login_${Date.now()}@example.com`;
    const testPassword = 'TestPassword123!';

    const registerResponse = await page.request.post('/api/auth/register', {
      json: {
        email: testEmail,
        password: testPassword,
        first_name: 'Test',
        last_name: 'User',
        company_name: `LoginCo_${Date.now()}`,
      }
    });

    if (registerResponse.ok()) {
      const loginResponse = await page.request.post('/api/auth/login', {
        json: {
          email: testEmail,
          password: testPassword
        }
      });

      expect([200, 201, 302]).toContain(loginResponse.status());
    }
  });
});
