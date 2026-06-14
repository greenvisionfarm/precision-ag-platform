# Pipeline Architecture: Drone Processing

Этот каталог содержит модульную реализацию обработки мультиспектральных данных DJI Mavic 3M.

## Структура модулей

### Быстрый путь (Fast Mode)

```
Files (DJI) → provider_dji (Metadata) → drone_processing_service (Grid) → raster_service (Zones)
```

### Путь ортомозаики (Orthomosaic)

```
Files (DJI) → orthomosaic_service (Stitching + GeoTIFF) → drone_processing_service (NDVI Points) → raster_service (Zones)
```

---

## Модули

### 1. `core_math.py` (Functional Core)
**Ответственность:** Чистая математика, алгоритмы и статистика.
- **Вход:** Массивы (numpy), таблицы (pandas), списки словарей.
- **Выход:** Числовые показатели, агрегированные данные, веса VRA.

### 2. `provider_dji.py` (Hardware Adapter)
**Ответственность:** Работа с низкоуровневыми данными DJI.
- **Вход:** Пути к файлам (TIF, JPG).
- **Выход:** Метаданные (GPS, EXIF), сырые массивы пикселей.

### 3. `drone_processing_service.py` (Fast Orchestrator)
**Ответственность:** Быстрая обработка без склейки.
- Координация от загрузки папки до генерации TIF и зон.
- Интерполяция NDVI по GPS-точкам (scipy.griddata).

### 4. `orthomosaic_service.py` (Orthomosaic Orchestrator)
**Ответственность:** Склейка дрон-фото в ортомозаику.
- `cv2.Stitcher_SCANS` для склейки RGB JPG.
- Геореференсирование по GPS из EXIF.
- Сохранение как GeoTIFF через rasterio.

### 5. `raster_service.py` (Zoning)
**Ответственность:** Зонирование NDVI растров.
- KMeans или Percentiles для разделения на зоны.
- Морфологическая обработка (median_filter, binary_closing).

### 6. `crop_classifier.py` (Classification)
**Ответственность:** Автоматическое определение культуры.
- NDVI профиль + текстура + дата съёмки.

### 7. `analysis_service.py` (Analysis)
**Ответственность:** Анализ и сравнение сканов.

### 8. `isoxml_service.py` (ISOXML Export)
**Ответственность:** Генерация ISOXML TaskFile для техники.

### 9. `kmz_service.py` (KMZ Export)
**Ответственность:** Генерация KMZ для DJI Pilot.

### 10. `gis_service.py` (GIS Utilities)
**Ответственность:** GIS вычисления и трансформации.

---

## AI Context: Как работать с файлами

1. **Задача по формулам/VRA:** Дай только `core_math.py`.
2. **Задача по DJI:** Дай `provider_dji.py`.
3. **Задача по склейке:** Дай `orthomosaic_service.py`.
4. **Задача по общей логике:** Дай `drone_processing_service.py`.

---

*Последнее обновление: 14 июня 2026 г.*
