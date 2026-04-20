# Field Mapper — Контекст проекта

## 📋 Общая информация

| Параметр | Значение |
|----------|----------|
| **Название** | Field Mapper |
| **GitHub Repo** | [greenvisionfarm/precision-ag-platform](https://github.com/greenvisionfarm/precision-ag-platform) |
| **Тип** | Precision Agriculture Platform |
| **Цель** | Цикл от полёта дрона до карты предписаний (VRA) |
| **Лицензия** | MIT |
| **Branch** | `master` (активная) |
| **Remote** | `upstream` → `https://github.com/greenvisionfarm/precision-ag-platform.git` |
| **GitHub Pages** | https://greenvisionfarm.github.io/precision-ag-platform/ |
| **Статус** | ⚠️ Активная разработка, не протестировано в production |
| **Последнее обновление** | 6 апреля 2026 г. |

---

## 🏗️ Архитектура

### Docker Compose
```
┌─────────────┐     ┌─────────────┐
│    Nginx    │────▶│     App     │
│   (80/443)  │     │  (Tornado)  │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │   (Huey)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Worker    │
                    │  (Huey)     │
                    └─────────────┘
```

### Стек технологий

| Компонент | Технология |
|-----------|------------|
| **Backend** | Python 3.12, Tornado, Peewee, Huey |
| **GIS** | GDAL, Rasterio, GeoPandas, EPSG:3035 |
| **Frontend** | jQuery, Leaflet, DataTables, Chart.js, ES6 Modules |
| **Infrastructure** | Docker, Redis, Nginx |
| **Tests** | Pytest (32 passed), Jest |
| **E2E** | Playwright |

---

## 🔀 Git Workflow

### Ветки

| Ветка | Описание |
|-------|----------|
| `master` | Основная ветка, стабильный код, авто-деплой на GitHub Pages |
| `feature/*` | Новые фичи (мержатся в master) |
| `fix/*` | Исправления багов |
| `docs/*` | Изменения в документации |
| `release/*` | Подготовка релиза (тегируются) |

### Remote

```bash
# origin — локальный форк/клон
# upstream — GitHub репозиторий
git remote -v
```

### Коммиты: Conventional Commits

```
<type>: <description>

[optional body]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `security`

**Примеры:**
```
feat: добавить экспорт ISOXML для карт-заданий
fix: исправить порядок отрисовки слоёв на карте
docs: обновить README с правильными ссылками
```

### CI/CD

GitHub Actions автоматически запускает при push в `master` или PR:
- ✅ Python тесты (`pytest`)
- ✅ JavaScript тесты (`jest`, исключая `e2e/`)
- ✅ Python lint (`ruff`)
- ✅ JS lint (`eslint`)
- ✅ Deploy на GitHub Pages

---

## 🚀 Быстрый старт

### Локальный запуск
```bash
# Установка зависимостей
pip install -r requirements.txt
npm install

# Запуск сервера
python app.py

# Тесты
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/
npm test
```

### Docker
```bash
# Сборка и запуск
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f app

# Тесты в Docker
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest tests/
docker-compose run --rm app npm test
```

---

## 📁 Структура проекта

```
field_mapper/
├── app.py                          # Точка входа (Tornado)
├── db.py                           # Модели Peewee
├── requirements.txt                # Python зависимости
├── package.json                    # Node.js зависимости
├── Dockerfile                      # Многоэтапная сборка
├── docker-compose.yml              # Оркестрация
│
├── .github/                        # GitHub configuration
│   ├── ISSUE_TEMPLATE/             # Шаблоны для issues
│   │   ├── bug_report.yml          # Баг-репорт
│   │   ├── feature_request.yml     # Фича-реквест
│   │   └── blank.md                # Пустой issue
│   ├── PULL_REQUEST_TEMPLATE.md    # Шаблон PR
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI
│
├── src/
│   ├── handlers/                   # REST API
│   │   ├── field_handlers.py       # CRUD полей
│   │   ├── owner_handlers.py       # Владельцы
│   │   ├── upload_handlers.py      # Загрузка файлов
│   │   └── field_commands.py       # Command pattern
│   │
│   ├── services/                   # Бизнес-логика
│   │   ├── gis_service.py          # GIS вычисления
│   │   ├── kmz_service.py          # KMZ экспорт (кэш)
│   │   └── raster_service.py       # NDVI анализ
│   │
│   └── utils/                      # Утилиты
│       ├── db_utils.py             # @db_connection
│       └── validators.py           # Валидация
│
├── static/
│   ├── index.html                  # Главный HTML
│   ├── css/
│   │   └── style.css               # Стили + темная тема
│   └── js/
│       ├── main.js                 # FieldMapperApp класс
│       └── modules/                # ES6 модули
│           ├── api.js              # API вызовы
│           ├── router.js           # Маршрутизация
│           ├── tables.js           # DataTables
│           ├── modals.js           # Модальные окна
│           ├── uploads.js          # Загрузка файлов
│           ├── stats.js            # Статистика
│           ├── theme.js            # Тема оформления
│           ├── field-detail.js     # Детали поля
│           ├── map-callbacks.js    # Leaflet callback'и
│           ├── utils.js            # Утилиты
│           └── map_manager.js      # Управление картой
│
├── tests/                          # Тесты
│   ├── test_app.py                 # Backend тесты
│   └── *.test.js                   # Frontend тесты
│
├── e2e/                            # E2E тесты (Playwright)
│   └── tests/
│       └── drone-ui.spec.ts        # UI тесты
│
├── docs/                           # Документация
│   ├── index.html                  # GitHub Pages landing
│   ├── getting-started/            # Быстрый старт
│   ├── user-guide/                 # Руководство пользователя
│   ├── developer-guide/            # Для разработчиков
│   └── changelog/                  # История изменений
│
├── SECURITY.md                     # Политика безопасности
├── CODE_OF_CONDUCT.md              # Code of Conduct
├── CONTRIBUTING.md                 # Гайдлайны для контрибьюторов
├── README.md                       # Главная документация
└── LICENSE                         # MIT License
```

---

## 🔑 Ключевой функционал

### 1. Земельный учет
- Границы полей (GeoJSON, Shapefile)
- Владельцы (CRUD)
- Площади в EPSG:3035 (гектары)
- Кадастровые номера

### 2. NDVI Анализ
- Загрузка GeoTIFF (до 1 GB)
- Фоновая обработка (Huey + Redis)
- Автоматическое зонирование
- Визуализация на карте

### 3. Экспорт DJI KMZ
- Формат WPML 1.0.6
- Совместимость с Mavic 3M
- Углы курса, перекрытия (overlap)
- Кэширование (lru_cache)

### 4. PWA
- Service Worker
- Offline кэш
- Локальные переводы (DataTables)

---

## 📊 Метрики

| Метрика | Значение |
|---------|----------|
| **Тесты** | 32 passed, 1 skipped |
| **Покрытие** | ~65% (backend) |
| **Размер образа** | ~1.5 GB (с GIS) |
| **Время сборки** | ~6 мин (~2 min с кэшем) |
| **GitHub Issues** | 28 (с labels и milestones) |
| **GitHub Project** | https://github.com/orgs/greenvisionfarm/projects/7 |

---

## 🗺️ Roadmap

| Milestone | Focus | Target |
|-----------|-------|--------|
| **v2026.3** | Orthomosaic, mobile UI | Apr 2026 |
| **v2026.4** | NDVI time series, yield prediction, OneSoil | May 2026 |
| **v2027.1** | PostgreSQL/PostGIS, CI/CD, monitoring | Jan 2027 |

---

## 📝 Недавние изменения (6 апреля 2026)

### Релизная подготовка
- ✅ Добавлен DISCLAIMER о не полностью протестированной платформе
- ✅ Создан SECURITY.md с политикой безопасности
- ✅ Создан CODE_OF_CONDUCT.md (Contributor Covenant)
- ✅ Создан CONTRIBUTING.md с полными гайдлайнами
- ✅ Созданы issue templates (bug report, feature request, blank)
- ✅ Создан PR template с чеклистом
- ✅ Создан GitHub Actions CI workflow (тесты + линтинг)
- ✅ Настроен GitHub Projects (https://github.com/orgs/greenvisionfarm/projects/7)
- ✅ Удалён TODO.md (roadmap перенесён в GitHub Issues/Milestones)
- ✅ Обновлён README — статус проекта, roadmap, ссылки

### Предыдущие изменения (24 марта 2026)
- ✅ Смержена `feature/refactoring-2026` → `master`
- ✅ Очищена git история (397 MB → 680 KB через git-filter-repo)
- ✅ БД удалены из git, .env в .gitignore
- ✅ Создано 28 GitHub Issues из TODO.md
- ✅ Созданы 3 GitHub Milestones
- ✅ Создан GitHub репозиторий и push кода
- ✅ Настроены GitHub Pages

### Рефакторинг
- ✅ Декоратор `@db_connection` для БД
- ✅ Валидация входных данных
- ✅ Type hints во всём Python коде
- ✅ Command pattern для обновлений полей
- ✅ Кэширование KMZ (lru_cache)
- ✅ ES6 модули для JavaScript
- ✅ Класс `FieldMapperApp`

### UI улучшения
- ✅ Страница загрузок (отдельный UI)
- ✅ Круглая кнопка меню с анимацией
- ✅ Адаптивный дизайн (десктоп + мобильные)

### Docker оптимизация
- ✅ Многоэтапная сборка
- ✅ Кэширование npm зависимостей
- ✅ Уменьшен контекст сборки на ~40%

---

## 🔗 Ссылки

- [GitHub](https://github.com/greenvisionfarm/precision-ag-platform)
- [Issues](https://github.com/greenvisionfarm/precision-ag-platform/issues)
- [Projects](https://github.com/orgs/greenvisionfarm/projects/7)
- [Docs](https://greenvisionfarm.github.io/precision-ag-platform/)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

---

*Последнее обновление: 6 апреля 2026 г.*
