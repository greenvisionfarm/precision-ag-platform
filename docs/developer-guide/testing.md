# Тестирование

## Обзор

Field Mapper использует два типа тестов:

| Тип | Фреймворк | Покрытие |
|-----|-----------|----------|
| **Backend** | Pytest | API, сервисы, БД |
| **Frontend** | Jest + JSDOM | UI логика, маршрутизация |

---

## Backend тесты (Pytest)

### Запуск

```bash
# Локально
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ -v

# В Docker
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest tests/ -v
```

### Структура тестов

```
tests/
├── test_app.py              # Интеграционные тесты API
├── test_services.py         # Тесты сервисов
├── test_bulk_export.py      # Массовый экспорт KMZ
└── test_raster_service.py   # NDVI анализ
```

### Пример теста

```python
# tests/test_app.py
def test_api_field_get(client):
    """GET /api/fields/:id возвращает поле."""
    field = create_test_field()
    
    response = client.get(f'/api/fields/{field.id}')
    data = json.loads(response.body)
    
    assert response.code == 200
    assert data['id'] == field.id
    assert data['name'] == 'Test Field'
```

### Фикстуры

```python
# tests/conftest.py
@pytest.fixture
def client():
    """Tornado test client."""
    return make_test_client()

@pytest.fixture
def test_db():
    """Test database (in-memory SQLite)."""
    database = SqliteDatabase(':memory:')
    database.bind([Field, Owner])
    database.create_tables([Field, Owner])
    yield database
    database.drop_tables([Field, Owner])
```

---

## Frontend тесты (Jest)

### Запуск

```bash
# Локально
npm test

# В Docker
docker-compose run --rm app npm test

# Watch mode
npm test -- --watch
```

### Структура тестов

```
static/js/
├── main.test.js             # Тесты маршрутизации и UI
├── modules/
│   └── *.test.js            # Тесты модулей
```

### Пример теста

```javascript
// static/js/main.test.js
describe('Field Mapper Frontend', () => {
  test('Routing: should show fields view', () => {
    window.location.hash = '#fields';
    global.handleRoute();
    
    const viewFields = document.getElementById('view-fields');
    expect(viewFields.style.display).not.toBe('none');
  });
});
```

### Моки

```javascript
// Моки для jQuery
global.$ = jest.fn((selector) => ({
  on: jest.fn(),
  show: jest.fn(),
  hide: jest.fn(),
}));

// Моки для API
jest.mock('./modules/api.js', () => ({
  default: {
    getFields: jest.fn().mockResolvedValue({ features: [] }),
  }
}));
```

---

## Покрытие

### Backend

```bash
# Установка pytest-cov
pip install pytest-cov

# Запуск с покрытием
FIELD_MAPPER_ENV=test pytest --cov=src --cov-report=html tests/
```

**Текущее покрытие:** ~60%

### Frontend

```bash
# Запуск с покрытием
npm test -- --coverage
```

**Текущее покрытие:** ~40%

---

## Интеграционные тесты

### Полный цикл NDVI

```python
def test_ndvi_full_cycle(client, tmp_path):
    """Загрузка TIF → Задача → Проверка зон."""
    # 1. Загрузка файла
    with open('tests/fixtures/test.tif', 'rb') as f:
        response = client.post('/upload', files={'raster_file': f})
    
    data = json.loads(response.body)
    task_id = data['task_id']
    
    # 2. Ожидание задачи
    wait_for_task(task_id, timeout=30)
    
    # 3. Проверка зон в БД
    zones = Zone.select().where(Zone.field == data['field_id'])
    assert zones.count() == 3  # Low, Medium, High
```

---

## E2E тесты (Планируется)

### Playwright

```python
# tests/e2e/test_upload.py
def test_upload_shapefile(page):
    page.goto('http://localhost:8888')
    page.click('#sidebar-toggle')
    page.click('a[href="#uploads"]')
    page.set_input_files('#shapefile-input', 'tests/fixtures/fields.zip')
    page.click('#upload-button')
    page.wait_for_selector('.text-success')
    assert page.query_selector('.upload-status').text_content() == 'Успешно загружено!'
```

---

## Непрерывная интеграция (CI)

### GitHub Actions (пример)

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm install
      
      - name: Run backend tests
        run: FIELD_MAPPER_ENV=test pytest tests/
      
      - name: Run frontend tests
        run: npm test
```

---

## Отладка тестов

### Backend

```bash
# Запуск одного теста
pytest tests/test_app.py::test_api_field_get -v

# Запуск с логом
pytest tests/ -v -s

# Запуск до первого провала
pytest tests/ -x
```

### Frontend

```bash
# Запуск одного теста
npm test -- --testNamePattern="Routing"

# Отладка
npm test -- --inspect-brk
```

---

## 📚 Ссылки

- [Архитектура](architecture.md) — обзор системы
- [Вклад в проект](contributing.md) — guidelines
