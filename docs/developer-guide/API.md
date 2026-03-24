# API Reference

Field Mapper REST API для управления полями, зонами и экспортом.

**Base URL:** `http://localhost/api`

---

## 📍 Fields (Поля)

### Получить все поля

```http
GET /fields
```

**Ответ:**
```json
{
  "fields": [
    {
      "id": 1,
      "name": "Поле №1",
      "area": "50.5 га",
      "owner": "Иванов И.И.",
      "land_status": "Аренда",
      "parcel_number": "55:12:001:01",
      "geometry": {...}
    }
  ]
}
```

### Получить поле по ID

```http
GET /field/:id
```

**Ответ:**
```json
{
  "id": 1,
  "name": "Поле №1",
  "area": "50.5 га",
  "owner": "Иванов И.И.",
  "land_status": "Аренда",
  "parcel_number": "55:12:001:01",
  "geometry": {...},
  "zones": [
    {
      "id": 1,
      "name": "Низкая",
      "avg_ndvi": 0.25,
      "color": "#ff4d4d",
      "geometry_wkt": "POLYGON(...)"
    }
  ]
}
```

### Добавить поле

```http
POST /field/add
Content-Type: application/json

{
  "name": "Новое поле",
  "geometry_wkt": "POLYGON ((...))",
  "area": "50.5",
  "land_status": "Аренда",
  "parcel_number": "55:12:001:01",
  "owner_id": 1
}
```

### Удалить поле

```http
POST /field/delete/:id
```

### Обновить поле

```http
POST /field/:action/:field_id
Content-Type: application/json

// action: rename, assign_owner, update_details, update_geometry
```

---

## 📤 Export (Экспорт)

### Экспорт поля в KMZ (DJI)

```http
GET /field/export/kmz/:id
```

**Ответ:** Файл `.kmz` для загрузки в DJI Pilot/FlightHub

### Массовый экспорт всех полей в KMZ

```http
GET /field/export/kmz/all
```

**Ответ:** ZIP архив с KMZ файлами

### Экспорт поля в ISOXML

```http
GET /field/export/isoxml/:id
```

**Ответ:** Файл `TASKDATA.XML` в формате ISOXML 4.0

**Параметры:**
- `:id` — ID поля

**Требования:**
- Поле должно иметь зоны (после загрузки TIFF)

**Пример использования:**
```bash
curl -O http://localhost/api/field/export/isoxml/1
```

---

## 🚁 Upload (Загрузка)

### Загрузить GeoTIFF (NDVI)

```http
POST /upload
Content-Type: multipart/form-data

raster_file: <GeoTIFF файл>
```

**Ответ:**
```json
{
  "message": "Файл принят. Обработка NDVI для поля 'Поле №1' запущена в фоне.",
  "task_id": "9e3b87b3-43d5-4afd-bf83-31355ba2f33f",
  "field_id": 1
}
```

### Получить статус задачи

```http
GET /task/:task_id
```

**Ответ:**
```json
{
  "status": "completed",
  "result": true
}
```

---

## 👥 Owners (Владельцы)

### Получить всех владельцев

```http
GET /owners
```

### Добавить владельца

```http
POST /owner/add
Content-Type: application/json

{
  "name": "Иванов И.И."
}
```

### Удалить владельца

```http
POST /owner/delete/:id
```

---

## 📊 Ошибки

### Формат ошибок

```json
{
  "error": "Описание ошибки"
}
```

### Коды статусов

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 400 | Неверный запрос |
| 404 | Не найдено |
| 500 | Внутренняя ошибка сервера |

### Примеры ошибок

**Поле не найдено:**
```http
HTTP/1.1 404 Not Found
{
  "error": "Поле не найдено"
}
```

**Нет зон для экспорта:**
```http
HTTP/1.1 404 Not Found
{
  "error": "Нет зон для экспорта"
}
```

---

## 🔧 Примеры использования

### Python

```python
import requests

# Получить все поля
response = requests.get('http://localhost/api/fields')
fields = response.json()['fields']

# Экспорт ISOXML
response = requests.get('http://localhost/api/field/export/isoxml/1')
with open('TASKDATA.XML', 'wb') as f:
    f.write(response.content)
```

### JavaScript (fetch)

```javascript
// Получить поле с зонами
const response = await fetch('/api/field/1');
const field = await response.json();
console.log(field.zones);

// Экспорт ISOXML
window.open('/api/field/export/isoxml/1', '_blank');
```

### cURL

```bash
# Получить все поля
curl http://localhost/api/fields

# Загрузить TIFF
curl -X POST -F "raster_file=@field_ndvi.tif" http://localhost/api/upload

# Экспорт ISOXML
curl -O http://localhost/api/field/export/isoxml/1
```

---

## 📚 Дополнительные ресурсы

- [ISOXML документация](../user-guide/isoxml.md)
- [Руководство по NDVI](../user-guide/ndvi.md)
- [Исходный код API](../../app.py)

---

*Последнее обновление: 24 марта 2026 г.*
