# Field Mapper — Контекст проекта

## Общая информация

| Параметр | Значение |
|----------|----------|
| **Название** | Field Mapper |
| **Тип** | Precision Agriculture Platform |
| **Цель** | Цикл от полёта дрона до карты предписаний (VRA) |
| **Лицензия** | Open Source |
| **Деплой** | `make deploy` → Docker на `192.168.31.196:8080` |

---

## Архитектура

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

## Быстрый старт

### Локальный запуск
```bash
pip install -r requirements.txt
npm install
python app.py
```

### Docker
```bash
docker-compose up -d --build
```

### Деплой на сервер
```bash
make deploy
# Или вручную:
ssh vladibuyanov@192.168.31.196
cd /opt/field_mapper
git pull origin master
docker compose up -d --build
```

---

## Структура проекта

```
field_mapper/
├── app.py                          # Точка входа (Tornado)
├── db.py                           # Модели Peewee
├── requirements.txt                # Python зависимости
│
├── src/
│   ├── handlers/                   # REST API
│   │   ├── auth_handlers.py        # Авторизация
│   │   ├── field_handlers.py       # CRUD полей
│   │   ├── owner_handlers.py       # Владельцы
│   │   ├── upload_handlers.py      # Загрузка файлов
│   │   ├── drone_handlers.py       # Дрон-снимки
│   │   └── field_commands.py       # Command pattern
│   │
│   ├── services/                   # Бизнес-логика
│   │   ├── raster_service.py       # NDVI зонирование
│   │   ├── drone_processing_service.py  # Обработка дрона
│   │   ├── crop_classifier.py      # Классификация культуры
│   │   ├── core_math.py            # Расчёт VRA норм
│   │   ├── isoxml_service.py       # ISOXML экспорт
│   │   ├── kmz_service.py          # KMZ экспорт
│   │   └── gis_service.py          # GIS вычисления
│   │
│   ├── models/                     # Модели данных
│   │   ├── auth.py                 # Пользователи, сессии
│   │   └── field.py                # Поля, зоны, сканы
│   │
│   └── utils/                      # Утилиты
│       ├── db_utils.py             # db_connection()
│       ├── auth.py                 # SessionManager
│       └── validators.py           # Валидация
│
├── static/                         # Frontend
│   ├── index.html
│   ├── css/style.css
│   └── js/modules/                 # ES6 модули
│
├── tests/                          # Тесты
├── docs/                           # Документация
└── Makefile                        # Команды деплоя
```

---

## Ключевой функционал

### 1. Земельный учет
- Границы полей (GeoJSON, Shapefile)
- Владельцы (CRUD)
- Площади в EPSG:3035 (гектары)
- Кадастровые номера

### 2. NDVI Анализ
- Загрузка GeoTIFF (до 1 GB)
- Фоновая обработка (Huey + Redis)
- Автоматическое зонирование (KMeans / Percentiles)
- Классификация культуры по NDVI профилю
- Визуализация на карте

### 3. VRA (Variable Rate Application)
- Автоматический расчёт норм внесения
- 4 зоны по продуктивности
- Балансировка массы удобрения
- Сохранение норм в БД

### 4. Экспорт
- **ISOXML** — John Deere, Claas, Valtra (ISO 11783-10)
- **KMZ** — DJI drones (WPML 1.0.6)
- **Shapefile** — Геометрия зон

### 5. Безопасность (Исправлено)
- bcrypt хеширование паролей
- Авторизация на всех handler'ах
- Мульти-тенантность (изоляция компаний)
- Защита от XSS, CSRF, path traversal

---

## Workflow: Drone → Prescription

```
Загрузка снимков (ZIP/TIFF)
        ↓
Обработка NDVI (быстрый путь / ортомозаика)
        ↓
Зонирование (4 зоны по перцентилям)
        ↓
Классификация культуры (авто)
        ↓
Расчёт VRA норм (если указана масса)
        ↓
Экспорт (ISOXML / KMZ)
        ↓
Загрузка на технику
```

Подробности: [docs/workflow.md](workflow.md)

---

## Тестирование

### Backend (Pytest)
```bash
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ -v
```

### Frontend (Jest)
```bash
npm test
```

---

## Недавние изменения (Июнь 2026)

### Безопасность (Критические исправления)
- ✅ bcrypt хеширование паролей
- ✅ Авторизация на 8 не защищённых handler'ах
- ✅ Единая модель Owner (убран дублирующийся класс)
- ✅ db_connection() с reference counting
- ✅ KMZ кэш (убран lru_cache для multi-tenant)
- ✅ Изоляция данных по компаниям

### Pipeline: Drone → Prescription
- ✅ rate_kg_ha поле в FieldZone
- ✅ Сохранение VRA норм в БД
- ✅ ISOXML использует сохранённые нормы
- ✅ Автоматическая классификация культуры

### Workflow
- ✅ Создан docs/workflow.md — полное описание цикла
- ✅ Обновлён CONTEXT.md

---

## Полезные ссылки

- [README.md](../README.md) — Основная документация
- [workflow.md](workflow.md) — Полный цикл Drone → Prescription
- [API Reference](developer-guide/API.md) — REST API
- [ISOXML Guide](user-guide/isoxml.md) — Экспорт для техники
- [Drone Guide](drone-imagery-guide.md) — Обработка снимков

---

*Последнее обновление: 13 июня 2026 г.*
