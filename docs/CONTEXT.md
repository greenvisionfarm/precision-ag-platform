# Field Mapper — Контекст проекта

## 📋 Общая информация

| Параметр | Значение |
|----------|----------|
| **Название** | Field Mapper |
| **Тип** | Precision Agriculture Platform |
| **Цель** | Цикл от полёта дрона до карты предписаний (VRA) |
| **Лицензия** | Open Source |
| **Ветка** | `feature/refactoring-2026` (готова к merge) |

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
| **Frontend** | jQuery, Leaflet, DataTables, Chart.js |
| **Infrastructure** | Docker, Redis, Nginx |
| **Tests** | Pytest, Jest, JSDOM |

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
└── docs/
    ├── README.md                   # Основная документация
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

## 🧪 Тестирование

### Backend (Pytest)
```bash
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ -v
```

**Статус:** 14 passed, 1 skipped

### Frontend (Jest)
```bash
npm test
```

---

## 📊 Метрики

| Метрика | Значение |
|---------|----------|
| **Тесты** | 14 passed, 1 skipped |
| **Файлов изменено** | 35 (рефакторинг 2026) |
| **Строк добавлено** | ~2700 |
| **Строк удалено** | ~950 |
| **Размер образа** | ~1.5 GB (с GIS) |
| **Время сборки** | ~6 мин (с кэшем) |

---

## 📝 Недавние изменения (2026)

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

- [README.md](README.md) — Основная документация
- [TODO.md](TODO.md) — Roadmap проекта
- [REFACTORING_PLAN.md](REFACTORING_PLAN.md) — Итоги рефакторинга 2026

---

*Последнее обновление: 24 марта 2026 г.*
