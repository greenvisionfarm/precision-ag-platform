# Qwen Code — Контекст проекта Field Mapper

## 📋 Общая информация

| Параметр | Значение |
|----------|----------|
| **Название** | Field Mapper |
| **Тип** | Precision Agriculture Platform |
| **Цель** | Цикл от полёта дрона до карты предписаний (VRA) |
| **Лицензия** | Open Source |
| **Ветка** | `feature/refactoring-2026` (готова к merge) |
| **Последнее обновление** | 24 марта 2026 г. |

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
| **Tests** | Pytest (16 passed), Jest (8 passed) |

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
docker-compose exec -e FIELD_MAPPER_ENV=test app pytest tests/
docker-compose exec app npm test
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
├── .ai-contexts/                   # Контекст для AI агентов
│   ├── gemini.md                   # Для Gemini
│   └── qwen.md                     # Для Qwen Code
│
├── docs/                           # Документация
│   ├── index.md                    # Главная
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
└── docs/
    ├── TODO.md                     # Roadmap
    └── REFACTORING_PLAN.md         # Итоги рефакторинга
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
| **Python тесты** | 16 passed, 1 skipped |
| **JS тесты** | 8 passed |
| **Файлов изменено** | 35+ (рефакторинг 2026) |
| **Строк добавлено** | ~2700 |
| **Строк удалено** | ~950 |
| **Размер образа** | ~1.5 GB (с GIS) |
| **Время сборки** | ~6 мин (с кэшем ~2 мин) |
| **Коммитов** | 15 |

---

## 🎯 Недавние изменения (2026)

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

### Документация
- ✅ docs-as-code структура
- ✅ 14 файлов документации
- ✅ .ai-contexts/ для AI агентов

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

### Тестирование:
- Запускать все тесты перед коммитом
- Минимальное покрытие: 80% для новой логики
- Python: `FIELD_MAPPER_ENV=test pytest tests/ -v`
- JS: `npm test`

---

## 🔗 Ссылки

- **README.md** — Основная документация
- **docs/** — Полная документация
- **TODO.md** — Дорожная карта
- **.ai-contexts/gemini.md** — Контекст для Gemini

---

*Последнее обновление: 24 марта 2026 г.*
