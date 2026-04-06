# E2E Тесты Field Mapper

Комплексные end-to-end тесты для платформы Field Mapper с использованием **Playwright**.

## 📋 Возможности

- ✅ **Автотесты основных сценариев**: авторизация, поля, владельцы, загрузка файлов, UI
- ✅ **Скриншоты**: автоматически при неудачах и по запросу
- ✅ **Видео**: запись failing тестов
- ✅ **Мультибраузерность**: Chromium, Mobile Chrome (Pixel 5)
- ✅ **HTML отчёты**: подробные отчёты с скриншотами и trace
- ✅ **Параллельный запуск**: несколько воркеров для скорости
- ✅ **Автозапуск сервера**: тесты сами поднимают сервер на порту 8888

## 📊 Статистика тестов

| Файл | Тестов | Описание |
|------|--------|----------|
| `auth.spec.ts` | 4 | Авторизация, вход, logout |
| `fields.spec.ts` | 8 | CRUD полей, экспорт KMZ, NDVI |
| `owners.spec.ts` | 5 | CRUD владельцев |
| `upload.spec.ts` | 6 | Загрузка файлов, зоны, статистика |
| `ui.spec.ts` | 5 | UI, адаптивность, темы |
| **Всего** | **28** | **Полное покрытие основных сценариев** |

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Установить npm зависимости и Playwright
make install

# Или вручную
npm install
npx playwright install chromium
```

### 2. Запуск тестов

```bash
# Все E2E тесты (headless)
make test-e2e

# С открытым браузером (видеть что происходит)
make test-e2e-headed

# Режим отладки
make test-e2e-debug

# Только тесты авторизации
make test-e2e-auth

# Только тесты полей
make test-e2e-fields
```

### 3. Просмотр результатов

```bash
# Открыть HTML отчёт
make test-e2e-report

# Скриншоты находятся в: e2e/results/
```

## 📁 Структура

```
e2e/
├── fixtures/
│   └── fixtures.ts          # Базовые фикстуры и утилиты
├── tests/
│   ├── auth.spec.ts         # Тесты авторизации
│   ├── fields.spec.ts       # Тесты управления полями
│   ├── owners.spec.ts       # Тесты владельцев
│   ├── upload.spec.ts       # Тесты загрузки и NDVI
│   └── ui.spec.ts           # Тесты UI и адаптивности
└── results/                  # Скриншоты и результаты
```

## 📸 Скриншоты

### Автоматические скриншоты

Скриншоты делаются автоматически при неудаче теста:

```javascript
// В конфиге playwright.config.js
use: {
  screenshot: 'only-on-failure',
}
```

### Ручные скриншоты в тестах

```javascript
test('должна показывать главную страницу', async ({ page, takeScreenshot }) => {
  await page.goto('/');
  
  // Сделать скриншот с именем
  await takeScreenshot('main_page');
  
  // ...Assertions
});
```

Скриншоты сохраняются в: `e2e/results/{timestamp}_{name}.png`

## 🎯 Примеры тестов

### Базовый тест

```javascript
import { test, expect } from '@playwright/test';

test('должна отображать карту', async ({ page }) => {
  await page.goto('/');
  
  // Проверяем наличие карты
  await expect(page.locator('#map')).toBeVisible();
  
  // Делаем скриншот
  await page.screenshot({ path: 'e2e/results/map.png' });
});
```

### Тест с фикстурами

```javascript
import { test, expect, TEST_FIELD } from '../fixtures/fixtures';

test('должна создавать поле', async ({ page, createTestField }) => {
  // Создаём поле через API
  const fieldId = await createTestField({
    name: 'Моё Поле'
  });
  
  // Проверяем в UI
  await page.goto('/#fields');
  await expect(page.locator(`tr:has-text("Моё Поле")`)).toBeVisible();
});
```

### Тест с авторизацией

```javascript
import { test, expect, TEST_USER } from '../fixtures/fixtures';

test('должна позволять войти', async ({ authenticatedPage }) => {
  // authenticatedPage уже авторизован
  await authenticatedPage.goto('/');
  
  // Проверяем профиль
  await expect(authenticatedPage.locator('.profile-icon')).toBeVisible();
});
```

## 🔧 Конфигурация

### playwright.config.js

```javascript
module.exports = defineConfig({
  testDir: './e2e',
  timeout: 60 * 1000,
  retries: process.env.CI ? 2 : 1,
  workers: 2,
  use: {
    baseURL: 'http://localhost:8888',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    viewport: { width: 1920, height: 1080 },
  },
  webServer: {
    command: 'python app.py',
    port: 8888,
    timeout: 120 * 1000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
  ],
  reporter: [
    ['html', { outputFolder: 'e2e-results/html-report' }],
    ['json', { outputFile: 'e2e-results/results.json' }],
    ['junit', { outputFile: 'e2e-results/junit.xml' }],
  ],
});
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BASE_URL` | URL сервера | http://localhost:8888 |
| `CI` | CI режим | false |

## 📊 Отчётность

### HTML Отчёт

После запуска тестов:

```bash
make test-e2e-report
```

Откроется HTML отчёт с:
- ✅ Списком всех тестов
- ✅ Скриншотами неудач
- ✅ Видео failing тестов
- ✅ Trace viewer для отладки

### JSON Отчёт

Сохраняется в: `e2e-results/results.json`

### JUnit XML

Для CI/CD: `e2e-results/junit.xml`

## 🐛 Отладка

### Режим отладки

```bash
make test-e2e-debug
```

Откроется Playwright Inspector с пошаговым выполнением.

### Trace Viewer

После failing теста:

```bash
npx playwright show-trace e2e-results/trace.zip
```

Показывает:
- Скриншоты каждого шага
- DOM снимки
- Сетевые запросы
- Консоль браузера

### headed режим

```bash
make test-e2e-headed
```

Запускает тесты с видимым браузером.

## 🎯 Покрытые сценарии

### Авторизация
- [x] Просмотр главной страницы
- [x] Форма входа
- [x] Вход с корректными данными
- [x] Ошибка при неверном пароле

### Поля
- [x] Просмотр карты полей
- [x] Список полей
- [x] Создание нового поля
- [x] Редактирование поля
- [x] Удаление поля
- [x] Экспорт в KMZ
- [x] Просмотр деталей
- [x] Назначение владельца

### Владельцы
- [x] Просмотр списка
- [x] Создание владельца
- [x] Редактирование владельца
- [x] Удаление владельца
- [x] Валидация пустого имени

### Загрузка и NDVI
- [x] Вкладка загрузок
- [x] Загрузка файлов
- [x] Статус загрузки
- [x] История сканов
- [x] Просмотр зон
- [x] Экспорт ISOXML
- [x] Статистика по зонам

### UI и адаптивность
- [x] Десктопная версия
- [x] Мобильная версия
- [x] Планшетная версия
- [x] Тёмная тема
- [x] Навигация
- [x] Loading состояния
- [x] Обработка ошибок
- [x] Keyboard navigation

### Интеграция с API
- [x] REST API вызовы через фикстуры
- [x] Создание тестовых данных
- [x] Очистка после тестов

## 🚀 CI/CD

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm install
      - run: npx playwright install chromium
      - run: make ci
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: e2e-results
          path: e2e-results/
```

### Docker

```bash
make docker-test
```

## 📝 Best Practices

1. **Используйте фикстуры**: `createTestField`, `takeScreenshot`
2. **Делайте скриншоты**: после важных действий
3. **Проверяйте accessibility**: keyboard navigation, ARIA
4. **Тестируйте на мобильных**: Mobile Chrome проект
5. **Очищайте данные**: после тестов
6. **Используйте data-testid**: для стабильных селекторов

## 🔗 Полезные ссылки

- [Playwright Docs](https://playwright.dev)
- [Playwright Test](https://playwright.dev/docs/test-intro)
- [Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [Codegen](https://playwright.dev/docs/codegen)

## 🆘 Troubleshooting

### Тесты падают с timeout

```bash
# Увеличьте timeout в playwright.config.js
timeout: 120 * 1000,
```

### Браузер не запускается

```bash
# Переустановите браузеры
npx playwright install --force
```

### Скриншоты не сохраняются

Проверьте, что директория существует:
```bash
mkdir -p e2e/results
```

## 📞 Контакты

Вопросы и предложения: создавайте Issue на GitHub.
