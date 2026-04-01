// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Конфигурация Playwright для E2E тестов Field Mapper
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './e2e',

  /* Полное время ожидания всех тестов */
  timeout: 60 * 1000,

  /* Время ожидания для expect().toBe() */
  expect: {
    timeout: 5000
  },

  /* Запускать тесты параллельно */
  fullyParallel: true,

  /* Количество воркеров (потоков) */
  workers: 2,

  /* Запретить тесты .only() в CI */
  forbidOnly: !!process.env.CI,

  /* Повторные попытки при неудаче */
  retries: process.env.CI ? 2 : 1,

  /* Отчётность */
  reporter: [
    ['html', { outputFolder: 'e2e-results/html-report' }],
    ['json', { outputFile: 'e2e-results/results.json' }],
    ['junit', { outputFile: 'e2e-results/junit.xml' }],
    ['list']
  ],

  /* Общие настройки для всех тестов */
  use: {
    /* Базовый URL для всех тестов */
    baseURL: process.env.BASE_URL || 'http://localhost:8888',

    /* Делать скриншот при неудаче */
    screenshot: 'only-on-failure',

    /* Записывать видео при неудаче */
    video: 'retain-on-failure',

    /* Отслеживать консоль браузера */
    trace: 'retain-on-failure',

    /* Действия перед тестом */
    actionTimeout: 10000,

    /* Навигация */
    navigationTimeout: 30000,
  },

  /* Конфигурация браузеров */
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
    },

    /* Тесты на мобильных устройствах */
    {
      name: 'Mobile Chrome',
      use: { 
        ...devices['Pixel 5'],
      },
    },
  ],

  /* Сервер для запуска тестов */
  webServer: process.env.CI ? undefined : {
    command: 'python3 app.py',
    port: 8888,
    timeout: 120 * 1000,
    reuseExistingServer: !process.env.CI,
    env: {
      FIELD_MAPPER_ENV: 'test',
    },
  },
});
