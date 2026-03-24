# API Reference

REST API Field Mapper. Все endpoints возвращают JSON.

## Базовый URL

```
Production: https://your-domain.com/api
Development: http://localhost:8888/api
```

## Формат ответов

### Успех
```json
{
  "success": true,
  "data": {...}
}
```

### Ошибка
```json
{
  "success": false,
  "error": "Error message"
}
```

---

## Поля (Fields)

### Получить все поля

**GET** `/api/fields`

**Ответ:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": 1,
      "properties": {
        "name": "Поле 1",
        "area": 25.5,
        "owner": "Иванов И.И.",
        "status": "Собственность",
        "parcel_number": "12:34:567890:123"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      }
    }
  ]
}
```

---

### Получить поле по ID

**GET** `/api/fields/:id`

**Ответ:**
```json
{
  "id": 1,
  "name": "Поле 1",
  "area": 25.5,
  "area_unit": "га",
  "owner": {
    "id": 1,
    "name": "Иванов И.И."
  },
  "status": "Собственность",
  "parcel_number": "12:34:567890:123",
  "geometry": {
    "type": "Polygon",
    "coordinates": [...]
  }
}
```

---

### Создать поле

**POST** `/api/fields`

**Тело запроса:**
```json
{
  "name": "Новое поле",
  "geometry": {
    "type": "Polygon",
    "coordinates": [...]
  },
  "owner_id": 1,
  "status": "Аренда",
  "parcel_number": "12:34:567890:124"
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 42
}
```

---

### Обновить поле

**PUT** `/api/fields/:id`

**Тело запроса:**
```json
{
  "name": "Обновлённое название",
  "area": 30.0
}
```

---

### Удалить поле

**DELETE** `/api/fields/:id`

**Ответ:**
```json
{
  "success": true
}
```

---

### Экспорт KMZ одного поля

**GET** `/api/field/export/kmz/:id`

**Query параметры:**
- `height` (float): Высота полёта, м (по умолчанию: 100)
- `direction` (int): Направление, градусы (по умолчанию: 90)
- `overlap_h` (float): Горизонтальное перекрытие, % (по умолчанию: 70)
- `overlap_w` (float): Вертикальное перекрытие, % (по умолчанию: 65)

**Ответ:** Файл `.kmz` (binary)

---

### Экспорт всех полей (ZIP)

**GET** `/api/field/export/kmz/all`

**Ответ:** ZIP-архив с `.kmz` файлами всех полей

---

## Владельцы (Owners)

### Получить всех владельцев

**GET** `/api/owners`

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Иванов И.И.",
    "fields_count": 5,
    "total_area": 125.5
  }
]
```

---

### Создать владельца

**POST** `/api/owners`

**Тело запроса:**
```json
{
  "name": "Петров П.П."
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 2
}
```

---

### Удалить владельца

**DELETE** `/api/owners/:id`

---

## Загрузка файлов

### Загрузить Shapefile (ZIP)

**POST** `/upload`

**Content-Type:** `multipart/form-data`

**Параметры:**
- `shapefile_zip`: ZIP-архив с .shp, .shx, .dbf, .prj

**Ответ:**
```json
{
  "success": true,
  "fields_created": 3
}
```

---

### Загрузить NDVI (GeoTIFF)

**POST** `/upload`

**Content-Type:** `multipart/form-data`

**Параметры:**
- `raster_file`: GeoTIFF файл (.tif, .tiff)

**Ответ:**
```json
{
  "success": true,
  "task_id": "abc123",
  "field_id": 1
}
```

**Polling статуса:**
```bash
GET /api/tasks/:task_id
```

---

## Задачи (Tasks)

### Получить статус задачи

**GET** `/api/tasks/:task_id`

**Ответ:**
```json
{
  "task_id": "abc123",
  "status": "completed",
  "result": {
    "zones_created": 3,
    "area_processed": 25.5
  }
}
```

**Статусы:**
- `pending`: Ожидает выполнения
- `running`: Выполняется
- `completed`: Завершено
- `error`: Ошибка

---

## Статистика

### Получить статистику

**GET** `/api/stats`

**Ответ:**
```json
{
  "total_fields": 15,
  "total_area": 450.5,
  "area_unit": "га",
  "by_status": {
    "Собственность": 300.2,
    "Аренда": 150.3
  },
  "by_owner": [
    {"name": "Иванов И.И.", "area": 125.5},
    {"name": "Петров П.П.", "area": 80.0}
  ]
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 400 | Неверный запрос (валидация) |
| 404 | Ресурс не найден |
| 500 | Внутренняя ошибка сервера |

---

## Лимиты

| Endpoint | Лимит |
|----------|-------|
| Загрузка GeoTIFF | 1 GB |
| Загрузка Shapefile | 50 MB |
| Экспорт KMZ | 100 запросов/мин |

---

## 📚 Ссылки

- [Архитектура](architecture.md) — обзор системы
- [Тестирование](testing.md) — тесты API
