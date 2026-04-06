# Qwen Code — Контекст проекта Field Mapper

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
# origin    /home/vladibuyanov/PycharmProjects/field_mapper (fetch)
# upstream  https://github.com/greenvisionfarm/precision-ag-platform.git (fetch/push)
```

### Коммиты: Conventional Commits

```
<type>: <description>

[optional body]
```

**Types:**
- `feat` — новая фича
- `fix` — исправление бага
- `docs` — документация
- `style` — форматирование (без логики)
- `refactor` — рефакторинг
- `test` — тесты
- `chore` — обслуживание
- `perf` — оптимизация
- `security` — безопасность

**Примеры:**
```
feat: добавить экспорт ISOXML для карт-заданий
fix: исправить порядок отрисовки слоёв на карте
docs: обновить README с правильными ссылками
test: добавить интеграционные тесты для обработки TIFF
```

### Команды для git

```bash
# Статус + diff + лог
git status && git diff HEAD && git log -n 3

# Коммит
git add . && git commit -m "feat: описание"

# Push на GitHub
git push upstream master

# Pull изменений
git pull upstream master
```

### CI/CD

GitHub Actions автоматически запускает при push в `master` или PR:
- ✅ Python тесты (`pytest`)
- ✅ JavaScript тесты (`jest`, исключая `e2e/`)
- ✅ Python lint (`ruff`)
- ✅ JS lint (`eslint`)
- ✅ Deploy на GitHub Pages

---

## 🚀 Команды для разработки

### Запуск сервера
```bash
python app.py
# http://localhost:8888
```

### Тесты
```bash
# Backend
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ -v

# Frontend
npm test

# Все тесты
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ && npm test
```

### Docker
```bash
# Сборка и запуск
docker-compose up -d --build

# Логи
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
├── .ai-contexts/                   # Контекст для AI агентов
│   ├── gemini.md                   # Для Gemini
│   ├── qwen.md                     # Для Qwen Code
│   └── README.md                   # Описание
│
├── docs/                           # Документация
│   ├── index.html                  # GitHub Pages landing
│   ├── getting-started/            # Быстрый старт
│   ├── user-guide/                 # Руководство пользователя
│   ├── developer-guide/            # Для разработчиков
│   └── changelog/                  # История изменений
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
│       ├── main.test.js            # Тесты
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
│   ├── test_ndvi_service.py        # NDVI тесты
│   └── *.test.js                   # Frontend тесты
│
├── e2e/                            # E2E тесты (Playwright)
│   └── tests/
│       └── drone-ui.spec.ts        # UI тесты
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
- Автоматическое зонирование (3 зоны)
- Визуализация на карте

### 3. Экспорт DJI KMZ
- Формат WPML 1.0.6
- Совместимость с Mavic 3M
- Углы курса, перекрытия (overlap)
- Кэширование (lru_cache maxsize=128)

### 4. PWA
- Service Worker
- Offline кэш
- Локальные переводы (DataTables)

---

## 📊 Метрики проекта

| Метрика | Значение |
|---------|----------|
| **Python тесты** | 32 passed, 1 skipped |
| **JS тесты** | Проходят (Jest) |
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

## 🎯 Недавние изменения (6 апреля 2026)

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
- ✅ Закрытие меню кликом на контент

### Тесты
- ✅ test_ndvi_service.py — тесты зонирования
- ✅ main.test.js — исправлены JS тесты
- ✅ utils.js — добавлены showConfirm(), formatArea()

### Docker оптимизация
- ✅ Многоэтапная сборка
- ✅ Кэширование npm зависимостей
- ✅ .dockerignore: уменьшен контекст на ~40%

---

## 🧠 Подсказки для Qwen Code

### При работе с кодом:
1. **Type hints обязательны** для всех Python функций
2. **ES6 модули** для всего JavaScript
3. **jQuery** разрешён (legacy код)
4. **Декоратор `@db_connection`** для всех handler'ов
5. **Command pattern** для обновлений полей

### При добавлении функциональности:
1. Добавить тесты (Python или JS)
2. Обновить документацию в `docs/`
3. Обновить `docs/changelog/CHANGELOG.md`
4. Следовать Conventional Commits для сообщений коммитов

### Git workflow:
- Ветка `master` — стабильный код
- Коммиты через Conventional Commits
- Push на `upstream` (GitHub)
- CI запускается автоматически

### Тестирование:
- Запускать все тесты перед коммитом
- Минимальное покрытие: 80% для новой логики
- Python: `FIELD_MAPPER_ENV=test pytest tests/ -v`
- JS: `npm test -- --testPathIgnorePatterns=e2e/`

---

## 🔗 Ссылки

- **GitHub:** https://github.com/greenvisionfarm/precision-ag-platform
- **Issues:** https://github.com/greenvisionfarm/precision-ag-platform/issues
- **Projects:** https://github.com/orgs/greenvisionfarm/projects/7
- **Docs:** https://greenvisionfarm.github.io/precision-ag-platform/
- **Contributing:** CONTRIBUTING.md
- **Security:** SECURITY.md

---

*Последнее обновление: 6 апреля 2026 г.*
