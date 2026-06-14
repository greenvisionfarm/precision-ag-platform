# Field Mapper Roadmap 🚀

## 🎯 Текущая цель: Orthomosaic (Полная реализация)
- [x] **orthomosaic_service.py** — cv2.Stitcher + EXIF GPS + геореференсирование
- [x] **Huey task** — фоновая обработка склейки
- [x] **Handler endpoints** — загрузка + статус (processing_mode routing)
- [x] **Frontend toggle** — fast/orthomosaic mode + прогресс
- [x] **Tests** — unit + integration (22 tests)
- [x] **Документация** — исправлены stale docs

## 📋 Следующие цели
- [ ] **Фото поля для визуальной оценки** — сохранять первый `_D.JPG` из миссии как превью скана; миграция `FieldScan.preview_path`; блок "Фото поля" на странице деталей
- [ ] **PPK GPS в обработке** — использовать `.MRK` файл для уточнения позиций снимков при зонировании (вместо EXIF GPS ±5м → PPK ±2см)
- [ ] **Chunked reading** для очень больших GeoTIFF (>10GB)
- [ ] **Кэширование результатов кластеризации** (ускорение повторного анализа)
- [ ] **Progressive loading** геометрий на frontend (для полей с 1000+ полигонами)

## 🔥 Аудит производительности (для слабых устройств фермеров)

### Критичные
- [ ] **Streaming загрузки** — RasterUploadHandler, ShapefileUpload буферизуют файл в RAM (как было с drone)
- [ ] **Индексы в БД** — `field.company_id`, `fieldscan.field_id`, `fieldzone.scan_id`, `fieldzone.field_id`, `fieldjournal.field_id` — нет индексов, полный пересмотр таблицы на каждый запрос

### Высокие
- [ ] **Пагинация `/api/fields`** — возвращает ВСЕ поля GeoJSON без LIMIT, огромный ответ
- [ ] **Кластеризация на карте** — Leaflet рендерит ВСЕ поля сразу, без кластеризации, тормоза при 50+ полях
- [ ] **Streaming BulkKMZExport** — ZIP всех полей целиком в `io.BytesIO()`, OOM приmany fields
- [ ] **Streaming compare_scans** — загружает оба растра в RAM одновременно
- [ ] **Streaming ShapefileUpload** — `uploaded_file['body']` весь ZIP в памяти + geopandas копия

### Средние
- [ ] **Async FieldComparisonHandler** — compare_scans блокирует event loop
- [ ] **Server-side пагинация DataTables** — все данные грузятся в браузер сразу
- [ ] **Оптимизация проверки дубликатов** — O(N) с wkt_loads + intersects для каждого поля
- [ ] **Raster band в памяти** — `src.read(1)` весь банда в numpy для статистики NDVI
- [ ] **N+1 в FieldScansHandler** — `scan.zones.count()` отдельный COUNT на каждый скан

## 💡 Идеи на будущее (Backlog)
- [ ] Отправка тяжелой обработки в Cloud (для слабых ноутбуков)
- [ ] Поддержка новых форматов экспорта (Shapefile, GeoJSON)
- [ ] Интеграция с метеостанциями

## ✅ Завершено (Архив достижений)
- [x] Рефакторинг на ES6 модули и Tornado Handlers (Март 2026)
- [x] Оптимизация RAM (Windowed reading, WAL mode)
- [x] Покрытие критических путей тестами (NDVI, VRA, Zoning)
