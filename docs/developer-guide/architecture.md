# Архитектура Field Mapper

## Обзор системы

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Browser)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Leaflet   │  │  DataTables │  │   FieldMapperApp    │  │
│  │    (Map)    │  │   (Tables)  │  │   (State Manager)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            HTTP/HTTPS
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Tornado Web Server (Python 3.12)           ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │   Handlers   │  │   Services   │  │    Utils     │  ││
│  │  │  (REST API)  │  │ (Business)   │  │ (Helpers)    │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
    ┌─────────▼─────────┐       ┌─────────▼─────────┐
    │   SQLite/Postgres │       │   Redis + Huey    │
    │    (Main Data)    │       │  (Task Queue)     │
    └───────────────────┘       └───────────────────┘
```

---

## Backend

### Структура модулей

```
src/
├── handlers/          # REST API контроллеры
│   ├── field_handlers.py    # CRUD полей
│   ├── owner_handlers.py    # Владельцы
│   ├── upload_handlers.py   # Загрузка файлов
│   └── field_commands.py    # Command pattern
│
├── services/          # Бизнес-логика
│   ├── gis_service.py         # GIS вычисления
│   ├── kmz_service.py         # KMZ экспорт (кэш)
│   └── raster_service.py      # NDVI анализ
│
└── utils/             # Утилиты
    ├── db_utils.py            # @db_connection
    └── validators.py          # Валидация
```

### Обработка запроса

```
HTTP Request → Handler → Service → Database
                     ↓
                  Validator
                     ↓
                  Response
```

**Пример:**
```python
# src/handlers/field_handlers.py
class FieldListHandler(FieldApiBaseHandler):
    @db_connection()
    def get(self):
        fields = Field.select().dicts()
        self.write({
            'type': 'FeatureCollection',
            'features': [serialize(f) for f in fields]
        })
```

---

## Frontend

### Модульная структура

```
static/js/
├── main.js              # FieldMapperApp класс
└── modules/
    ├── api.js           # API вызовы
    ├── router.js        # Маршрутизация по hash
    ├── tables.js        # DataTables инициализация
    ├── modals.js        # Модальные окна
    ├── uploads.js       # Загрузка файлов
    ├── stats.js         # Статистика и графики
    ├── theme.js         # Тёмная/светлая тема
    ├── field-detail.js  # Детали поля
    ├── map-callbacks.js # Leaflet callback'и
    ├── utils.js         # Утилиты
    └── map_manager.js   # Управление картой
```

### State Management

```javascript
class FieldMapperApp {
  constructor() {
    this.mapInitialized = false;
    this.currentView = 'map';
  }

  init() {
    initTheme();
    window.MapManager.initMainMap(...);
    this.setupRoutes();
  }
}
```

---

## База данных

### Модели (Peewee ORM)

```python
# db.py
class Owner(Model):
    name = CharField()

class Field(Model):
    name = CharField(null=True)
    geometry_wkt = TextField()
    owner = ForeignKeyField(Owner, backref='fields', null=True)
    status = CharField(null=True)
    parcel_number = CharField(null=True)
```

### Миграции

> В разработке: Alembic для миграций

---

## Асинхронные задачи

### Huey + Redis

```python
# src/tasks.py
@huey.task()
def process_ndvi_async(field_id: int, file_path: str):
    """Фоновая обработка NDVI."""
    zones = raster_service.calculate_zones(file_path)
    save_zones_to_db(field_id, zones)
```

**Поток:**
```
Upload → API → Task Queue → Worker → DB
           ↓
        Task ID
           ↓
      Polling ← Frontend
```

---

## Кэширование

### KMZ Export

```python
# src/services/kmz_service.py
from functools import lru_cache

@lru_cache(maxsize=128)
def generate_kmz(field_id: int, height: float, ...) -> bytes:
    # Кэш по параметрам
```

**Эффект:** Ускорение в 5-10 раз при повторном экспорте

---

## Безопасность

### Уровни защиты

1. **Input Validation:** `src/utils/validators.py`
2. **SQL Injection:** Peewee ORM (параметризованные запросы)
3. **XSS:** Tornado auto-escaping
4. **CORS:** Настройка в `app.py`

---

## Масштабирование

### Горизонтальное

- Несколько app контейнеров за Nginx
- Redis для session storage
- PostgreSQL вместо SQLite

### Вертикальное

- Увеличение RAM для worker
- SSD для базы данных
- CDN для статических файлов

---

## 📚 Ссылки

- [API Reference](api-reference.md) — REST endpoints
- [Тестирование](testing.md) — как писать тесты
- [Вклад в проект](contributing.md) — guidelines
