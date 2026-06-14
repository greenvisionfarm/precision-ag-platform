# Интеграция с DJI Mavic 3M

Field Mapper оптимизирован для работы с мультиспектральными данными дронов DJI (особенно Mavic 3M и Phantom 4 Multispectral).

## Режимы обработки

### Быстрый режим (Fast Grid Mode)

Не требует создания ортофотоплана. Каждый снимок — одна NDVI-точка.

1. ZIP-архив с "сырыми" снимками
2. Извлечение GPS из XMP (тег 700) и EXIF
3. Нормализация: `Reflectance = (DN - BlackLevel) / (Exposure * Gain)`
4. Интерполяция точек в растровую сетку (2м, EPSG:3035)
5. Зонирование по перцентилям: 4 зоны (P20, P50, P80)

**Код:** `src/services/drone_processing_service.py`

### Режим ортомозаики (Orthomosaic)

Склейка RGB JPG в единое изображение через OpenCV.

1. Фильтрация RGB JPG (`_D.JPG`) из архива
2. Склейка через `cv2.Stitcher_SCANS`
3. Геореференсирование по GPS из EXIF → GeoTIFF
4. NDVI анализ по GPS-точкам (fast path) или по растрору
5. Зонирование и классификация культуры

**Код:** `src/services/orthomosaic_service.py`

### Выбор режима

Режим задаётся параметром `processing_mode` в запросе:

```json
{
  "field_id": 123,
  "processing_mode": "fast|orthomosaic",
  "crop_type": "auto",
  "total_fertilizer_kg": 2000
}
```

## Нормализация данных

Формула для NDVI/NDRE:
```
Reflectance = (DN - BlackLevel) / (Exposure * Gain)
```

- **DN**: Значение пикселя (Digital Number)
- **BlackLevel**: Уровень черного сенсора
- **Exposure**: Выдержка
- **Gain**: Усиление сенсора

## Группировка файлов

Система автоматически распознает каналы DJI по суффиксам:
- `_NIR.TIF` — Ближний инфракрасный
- `_R.TIF` / `_RED.TIF` — Красный
- `_RE.TIF` — Крайний красный (Red Edge)
- `_G.TIF` — Зеленый
- `_D.JPG` — RGB (стандартная камера)

## Экспорт в DJI Pilot

Экспортируемые KMZ файлы совместимы с **DJI Pilot 2** (WPML формат). Они включают:
- Границы поля
- Точки маршрута для сканирования
- Стилизацию зон по цветам

---

*Последнее обновление: 14 июня 2026 г.*
