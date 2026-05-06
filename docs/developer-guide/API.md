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

### Сравнение сканов поля

```http
GET /field/:id/compare?scans=1,2
```

**Ответ:** Разница в индексах между двумя временными точками.

---

## 🚁 Drone & Scans (Дроны и Сканирования)

### Загрузка архива со снимками DJI (Fast Mode)

```http
POST /api/drone/upload
Content-Type: multipart/form-data

drone_images: <ZIP архив со снимками>
data: {
  "field_id": 1,        // Опционально (автоопределение по GPS)
  "crop_type": "wheat", // Опционально
  "total_fertilizer_kg": 5000 // Для расчета VRA
}
```

### Получить список сканов поля

```http
GET /api/field/:id/scans
```

### Обновить культуру для скана

```http
POST /api/scan/:id/update_crop
Content-Type: application/json

{
  "crop_type": "corn"
}
```

---

## 📤 Export (Экспорт)

### Экспорт поля в KMZ (DJI)

```http
GET /api/field/export/kmz/:id
```

**Ответ:** Файл `.kmz` для загрузки в DJI Pilot/FlightHub.

### Экспорт поля в ISOXML (VRA)

```http
GET /api/field/export/isoxml/:id
```

**Ответ:** Файл `TASKDATA.XML` в формате ISOXML 4.0.

---

## 🚁 Raster (Растры)

### Загрузить GeoTIFF (NDVI)

```http
POST /api/raster/upload
Content-Type: multipart/form-data

raster_file: <GeoTIFF файл>
```

---

## 📊 Ошибки

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 400 | Неверный запрос |
| 404 | Не найдено |
| 500 | Внутренняя ошибка сервера |

---

*Последнее обновление: 6 мая 2026 г.*
