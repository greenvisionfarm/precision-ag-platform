# Field Mapper (Open Source Precision Ag Platform)

**Field Mapper** — это открытая веб-платформа для фермеров и агрономов. Она превращает данные с дронов (особенно мультиспектральных, таких как DJI Mavic 3M) в карты предписаний для сельскохозяйственной техники.

Наша цель — дать фермерам простой инструмент для **точного земледелия** (Precision Agriculture), который позволяет:
1.  Управлять земельным банком (границы, кадастр, аренда).
2.  Загружать ортофотопланы полей.
3.  Анализировать здоровье растений (NDVI, NDRE).
4.  Создавать карты для дифференцированного внесения (VRA) удобрений и СЗР.

## Основные возможности

### 🌱 Управление полями (Land Management)
- **Интерактивная карта:** Рисование и редактирование границ.
- **Детали поля:** Просмотр подробной информации, мини-карта и управление конкретным участком.
- **Земельный учет:** Статус (Собственность/Аренда), кадастровые номера.
- **Импорт/Экспорт:** Загрузка контуров из Shapefile и экспорт полетных заданий в DJI KMZ.
- **DJI Pilot Ready:** Генерация `template.kml` для Mavic 3M (настройка высоты, перекрытий).
- **Кадастр:** Интеграция с официальными слоями (WMS).

### 🚁 Агро-аналитика
- **Анализ NDVI:** Загрузка мультиспектральных данных в формате GeoTIFF.
- **Умное зонирование:** Автоматическая векторизация растра в 3 зоны продуктивности (Низкая, Средняя, Высокая) за считанные секунды.
- **Визуализация:** Отображение зон вегетации прямо поверх карты полей.
- **Оптимизация:** Обработка данных "на лету" без хранения тяжелых оригиналов (экономия места на сервере).

## Архитектура

Проект следует принципам модульности для облегчения тестирования и расширения:

- **Backend:** Python 3.12 (Tornado)
    - `src/handlers/`: REST API контроллеры (Command pattern)
    - `src/services/`: Гео-вычисления и логика экспорта (с кэшированием)
    - `src/utils/`: Утилиты (валидация, декораторы БД)
    - `db.py`: Модели данных SQLite (Peewee, type hints)
- **Frontend:** SPA (HTML5, CSS3, Leaflet.js, ES6 модули)
    - `static/js/modules/`: Модули (utils, router, tables, modals, uploads, stats, theme, field-detail, map-callbacks)
    - `static/js/main.js`: Класс FieldMapperApp для управления состоянием
- **PWA:** Поддержка офлайн-работы через Service Worker
- **Task Queue:** Huey + Redis для фоновых задач

## Установка и запуск

### 🐳 Быстрый старт через Docker (Рекомендуется)
Самый простой способ запустить весь стек (API, Worker, Redis, Nginx):

1. **Запустите проект:**
   ```bash
   docker-compose up -d --build
   ```
2. **Проверьте работу:** Откройте [http://localhost](http://localhost) (порт 80, через Nginx) или [http://localhost:8888](http://localhost:8888) (напрямую к API).
3. **Остановка:** `docker-compose down`.

> **Оптимизация:** Dockerfile оптимизирован для быстрой сборки (кэширование npm, многоэтапная сборка). Время сборки с кэшем: ~1.5-2 минуты.

### 🛠️ Локальная разработка (без Docker)
1. Создайте и активируйте окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # для Linux/macOS
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   npm install
   ```
3. Запустите приложение:
   ```bash
   python app.py
   ```
4. Откройте [http://localhost:8888](http://localhost:8888).

## Тестирование

### Запуск тестов в Docker
Для гарантии идентичности среды выполнения тесты можно запустить внутри контейнера:

```bash
# Все тесты (Python + JS)
docker-compose run --rm app npm test && docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest

# Только Python тесты
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest

# Только JS тесты
docker-compose run --rm app npm test
```

### Локальный запуск
Проект использует изолированную среду для тестов, чтобы не затронуть рабочую базу данных `fields.db`.

- **Backend:** `FIELD_MAPPER_ENV=test ./venv/bin/pytest` (14 passed, 1 skipped)
- **Frontend (JS Unit):** `npm test` (Jest + JSDOM)

## Рефакторинг и качество кода

В проекте проведён масштабный рефакторинг (2026):

### Backend улучшения:
- ✅ Декоратор `@db_connection` для управления подключением к БД
- ✅ Валидация входных данных (`src/utils/validators.py`)
- ✅ Type hints во всех модулях
- ✅ Command pattern для обновлений полей (`src/handlers/field_commands.py`)
- ✅ Кэширование KMZ экспорта (lru_cache)
- ✅ Модульная структура пакетов (`src/handlers/`, `src/services/`, `src/utils/`)

### Frontend улучшения:
- ✅ ES6 модули для всего JavaScript кода
- ✅ Класс `FieldMapperApp` для инкапсуляции состояния
- ✅ Разделение ответственности между модулями
- ✅ Обработка ошибок API вызовов
- ✅ Страница загрузок — выделена в отдельный UI с улучшенным дизайном

Подробности в [REFACTORING_PLAN.md](REFACTORING_PLAN.md)

## Структура проекта

```
field_mapper/
├── app.py                      # Точка входа приложения
├── db.py                       # Модели данных Peewee
├── requirements.txt            # Python зависимости
├── package.json                # Node.js зависимости
├── docker-compose.yml          # Docker оркестрация
├── Dockerfile                  # Оптимизированная сборка
├── src/
│   ├── handlers/               # REST API контроллеры
│   │   ├── field_handlers.py   # Обработчики полей
│   │   ├── owner_handlers.py   # Обработчики владельцев
│   │   ├── upload_handlers.py  # Обработчики загрузки
│   │   └── field_commands.py   # Command pattern для обновлений
│   ├── services/               # Бизнес-логика
│   │   ├── gis_service.py      # GIS вычисления
│   │   ├── kmz_service.py      # KMZ экспорт (с кэшированием)
│   │   └── raster_service.py   # Растровая аналитика
│   └── utils/                  # Утилиты
│       ├── db_utils.py         # Декораторы БД
│       └── validators.py       # Валидация данных
├── static/
│   ├── index.html              # Главный HTML
│   ├── css/                    # Стили
│   └── js/
│       ├── main.js             # Класс FieldMapperApp
│       └── modules/            # ES6 модули
│           ├── api.js          # API вызовы
│           ├── router.js       # Маршрутизация
│           ├── tables.js       # DataTables
│           ├── modals.js       # Модальные окна
│           ├── uploads.js      # Загрузка файлов
│           ├── stats.js        # Статистика и графики
│           ├── theme.js        # Тема оформления
│           ├── field-detail.js # Детали поля
│           ├── map-callbacks.js# Callback'и карты
│           ├── utils.js        # Утилиты
│           └── map_manager.js  # Управление картой
└── tests/                      # Тесты
    ├── test_app.py             # Backend тесты
    └── *.test.js               # Frontend тесты
```

## Лицензия

Open Source проект для развития точного земледелия.
