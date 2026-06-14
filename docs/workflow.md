# Workflow: Drone Photos → Prescription Maps

Этот документ описывает полный цикл обработки данных от снимков дрона до карты предписаний (VRA) для сельскохозяйственной техники.

---

## Обзор процесса

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Загрузка   │───▶│  Обработка  │───▶│    VRA      │───▶│   Экспорт   │───▶│  Техника    │
│   снимков   │    │    NDVI     │    │  Зоны и     │    │  ISOXML /   │    │  John Deere │
│  (ZIP/TIFF) │    │  Зонирование│    │   Нормы     │    │   KMZ       │    │   Claas     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Этап 1: Загрузка данных

### Вариант A: GeoTIFF (спутник или готовый растр)

```bash
POST /api/raster/upload
Content-Type: multipart/form-data
Cookie: session=<session_id>

field_id: 123
file: orthomosaic.tif
```

**Происходит:**
1. Файл сохраняется в `uploads/`
2. Создаётся запись `FieldScan` со статусом `processed='pending'`
3. Запускается фоновая задача `process_geotiff_task`

### Вариант B: Снимки дрона (ZIP)

```bash
POST /api/drone/upload
Content-Type: multipart/form-data
Cookie: session=<session_id>

field_id: 123
zip: drone_photos.zip
crop_type: auto          # auto | wheat | corn | sunflower | ...
total_fertilizer_kg: 500  # Общая масса удобрения (опционально)
```

**Происходит:**
1. ZIP сохраняется в `uploads/`
2. Запускается фоновая задача `process_drone_fast_task`

---

## Этап 2: Обработка и зонирование

### Быстрый путь (Drone Fast Mode) — Рекомендуется

Используется для работы на **обычных ПК** без тяжёлых зависимостей (OpenDroneMap, Pix4D).

```
1. Распаковка ZIP → извлечение TIF/TIFF файлов
2. Извлечение GPS и NDVI/NDRE из EXIF каждого снимка
3. Интерполяция точек в растровую сетку (2м разрешение, EPSG:3035)
4. Зонирование по перцентилям: 4 зоны (P20, P50, P80)
5. Расчёт VRA норм (если указана масса удобрения)
6. Классификация культуры по NDVI профилю
7. Сохранение зон в БД
```

**Код:** `src/tasks.py::process_drone_fast_task`

### Полный путь (Orthomosaic)

```
1. Склейка RGB JPG через cv2.Stitcher_SCANS
2. Геореференсирование по GPS из EXIF
3. NDVI расчёт (NIR - RED) / (NIR + RED) по GPS-точкам
4. Зонирование по перцентилям: 4 зоны
5. Расчёт VRA норм (если указана масса удобрения)
6. Классификация культуры по NDVI профилю
7. Сохранение зон в БД
```

**Код:** `src/tasks.py::process_orthomosaic_task` → `src/services/orthomosaic_service.py`

---

## Этап 3: Зоны и VRA нормы

После обработки каждая зона содержит:

| Поле | Описание |
|------|----------|
| `name` | Название зоны ("Высокая", "Средняя", "Низкая", "Очень низкая") |
| `geometry_wkt` | Геометрия зоны в WKT (EPSG:4326) |
| `avg_ndvi` | Средний NDVI в зоне |
| `color` | Цвет для отображения (#008000, #ffff00, #ffa500, #ff0000) |
| `rate_kg_ha` | Норма внесения в кг/га (VRA) |

### Расчёт VRA норм

Расчёт автоматически выполняется при указании `total_fertilizer_kg`:

```
total_fertilizer_kg = 500  (например, 500 кг аммиачной селитры)
field_area_ha = 10          (площадь поля в гектарах)

→ Зона 1 (Высокая NDVI): 120 кг/га
→ Зона 2 (Средняя NDVI): 180 кг/га
→ Зона 3 (Низкая NDVI):  240 кг/га
→ Зона 4 (Очень низкая): 300 кг/га
```

Алгоритм балансировки: `src/services/core_math.py::calculate_vra_redistribution`

---

## Этап 4: Классификация культуры

Автоматически определяется по:
- NDVI профилю (гистограмма значений)
- Дате съёмки (сезонность)
- Текстуре поля (рядность, паттерн)

**Результаты сохраняются в `FieldScan`:**
- `crop_type` — тип культуры (wheat, corn, sunflower, ...)
- `crop_confidence` — уверенность классификации (0-1)

**Поддерживаемые культуры:**

| Культура | Пик NDVI | Месяц пика | Нормы (кг/га) |
|----------|----------|------------|---------------|
| Пшеница | 0.75 | Июнь | 120-240 |
| Кукуруза | 0.85 | Июль | 150-350 |
| Подсолнечник | 0.65 | Июль | 80-160 |
| Соя | 0.55 | Август | 40-80 |
| Рапс | 0.80 | Май | 140-260 |
| Ячмень | 0.70 | Июнь | 100-200 |
| Сахарная свёкла | 0.70 | Август | 120-240 |
| Картофель | 0.60 | Июль | 150-300 |

**Код:** `src/services/crop_classifier.py`

---

## Этап 5: Экспорт

### ISOXML (John Deere, Claas, Valtra)

```bash
POST /api/fields/{field_id}/export-isoxml
Content-Type: application/json
Cookie: session=<session_id>

{
  "scan_id": 456,
  "product_name": "Аммиачная селитра"
}
```

**Создаётся TaskFile в формате ISO 11783-10:**
- Section boundaries (границы зон)
- TaskDataWithProduct (нормы внесения)
- Product: Аммиачная селитра (34% N)

**Код:** `src/services/isoxml_service.py::generate_isoxml_task_file`

### KMZ (DJI drones)

```bash
POST /api/kmz/generate
Content-Type: application/json
Cookie: session=<session_id>

{
  "field_id": 123,
  "flight_height": 30,
  "overlap": 75
}
```

**Создаётся WPML 1.0.6 файл:**
- Waypoint'и с координатами
- Курс и угол камеры
- Совместимость с DJI Pilot 2

**Код:** `src/services/kmz_service.py::generate_dji_kmz`

---

## Этап 6: Загрузка на технику

### John Deere Operations Center
1. Скачайте ISOXML файл (.zip)
2. Откройте Operations Center → Data → Import
3. Выберите файл → Импорт
4. Назначьте задание на трактор

### Claas Telematics
1. Скачайте ISOXML файл
2. Откройте Claas Connect → Task Data
3. Импортируйте файл
4. Синхронизируйте с терминалом

### DJI (для повторного полёта)
1. Скопируйте KMZ на microSD карту
2. Вставьте в DJI RC Pro Enterprise
3. Откройте DJI Pilot 2 → Миссии
4. Выберите импортированный маршрут

---

## Архитектура обработки

```
┌─────────────────────────────────────────────────────────────┐
│                      Tornado App (8888)                      │
├─────────────────────────────────────────────────────────────┤
│  Handlers:                                                   │
│  ├── upload_handlers.py   — Загрузка GeoTIFF/ZIP             │
│  ├── drone_handlers.py    — Управление дрон-снимками         │
│  ├── field_handlers.py    — CRUD полей                       │
│  └── isoxml_handlers.py   — Экспорт ISOXML                   │
├─────────────────────────────────────────────────────────────┤
│  Services:                                                   │
│  ├── raster_service.py    — NDVI зонирование (KMeans/Perc)   │
│  ├── drone_processing_service.py — Быстрая обработка дрона   │
│  ├── crop_classifier.py   — Классификация культуры           │
│  ├── core_math.py         — Расчёт VRA норм                  │
│  ├── isoxml_service.py    — Генерация ISOXML TaskFile        │
│  └── kmz_service.py       — Генерация DJI KMZ               │
├─────────────────────────────────────────────────────────────┤
│  Background (Huey + Redis):                                  │
│  ├── process_geotiff_task  — Обработка GeoTIFF               │
│  └── process_drone_fast_task — Быстрая обработка дрона       │
└─────────────────────────────────────────────────────────────┘
```

---

## Требования к данным

### Снимки дрона (ZIP)

Формат файлов в ZIP:
```
DJI_20260501_120000_001_NIR.TIF    # Near-Infrared
DJI_20260501_120000_001_RED.TIF    # Red
DJI_20260501_120000_001_RE.TIF     # Red Edge (опционально)
```

Требования:
- Файлы `.TIF` или `.TIFF`
- EXIF: GPS координаты (Latitude, Longitude)
- Разрешение: любой (рекомендуется 2м на пиксель)

### GeoTIFF

- Формат: GeoTIFF (.tif)
- Банды: 1 (NDVI) или 4+ (RGBN)
- CRS: EPSG:4326 или EPSG:3035
- Максимальный размер: ~1 GB

---

## Часто задаваемые вопросы

### Почему "быстрый путь" без ортомозаики?

Ортомозаика (stitching) требует тяжёлых зависимостей:
- OpenDroneMap (~2 GB)
- Pix4D (коммерческий)
- Photogrammetry библиотеки

**Быстрый путь** работает на любом ПК:
- Интерполяция точек через GPS → растровая сетка
- 2м разрешение (достаточно для VRA)
- Без внешних зависимостей

### Как работает классификация культуры?

1. Анализ NDVI гистограммы (среднее, стандартное отклонение, перцентили)
2. Анализ текстуры (FFT для выявления рядности)
3. Сезонность (месяц съёмки vs пик культуры)
4. Взвешенная оценка по 3 факторам

### Можно ли изменить зоны после обработки?

Да. Используйте:
- `DELETE /api/fields/{field_id}/zones?scan_id={scan_id}` — удалить зоны скана
- `POST /api/fields/{field_id}/zones` — создать зоны вручную
- `PUT /api/fields/{field_id}/zones/{zone_id}` — изменить зону

---

*Последнее обновление: 13 июня 2026 г.*
