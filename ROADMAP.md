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
- [ ] **Детекция сорняков** — выделять зоны с аномально высоким NDVI относительно основной культуры; отдельный слой на карте; экспорт зон сорняков
- [ ] **Детекция нор/ямок** — аномалии в NDVI + высота из PPK GPS (Ellh); ямки = низкий NDVI + низкая высота, кучи = высокий NDVI + высота
- [ ] **Карты для фиксед-винг дронов** — поддержка senseFly, Wingtra и других; другие форматы файлов, другое разрешение, другая геометрия полёта
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

## 🚜 Экспорт в терминалы техники (ISOXML / TaskData)

### Текущее состояние
- Генератор `ag-isoxml` producing невалидный XML (нет PRODUCTGROUP, BINAPPLICATIONZONE, GUID, TIME)
- Формат неприемлем ни для John Deere, ни для Claas, ни для Case IH

### Что делаем сейчас
- [ ] **Переписать генератор по ISO 11783-10** — добавить все обязательные элементы: TIME, OPERATIONTECHNIQUE, VEHICLE, CONTROLLER, PRODUCTGROUP, PRODUCT, BINAPPLICATIONZONE, PRESCRIPTIONZONE, PROCESSDATA, GUID
- [ ] **Генерировать TaskData.zip** — формат принимаемый всеми терминалами: TaskData.xml + Partfield.xml + TreatmentZone.xml + Product.xml (вместо裸 XML)
- [ ] **Валидация перед выдачей** — XSD-валидатор ISO 11783-10; если файл невалиден — не отдавать, показать ошибку пользователю
- [ ] **Экспорт в Shapefile (.shp)** — альтернативный формат; геометрия в .shp, нормы в .dbf; принимается всеми терминалами без исключения
- [ ] **Запросить эталонный файл у тестера** — попросить фермера с John Deere / Claas прислать USB с реальным TaskData.xml от дилера; разобрать структуру и переписать генератор по образцу

### Порядок реализации
1. Shapefile экспорт (быстрый, 100% совместимость)
2. TaskData.zip генератор (среднее, высокая совместимость)
3. ISOXML 11783-10 полный (сложное, максимальная совместимость)
4. Тест на реальном терминале

## 💡 Идеи на будущее (Backlog)
- [ ] Отправка тяжелой обработки в Cloud (для слабых ноутбуков)
- [ ] Интеграция с метеостанциями

## 📦 Выделение модулей для сообщества

### Готовые к публикации
- [ ] **`kmz-mission`** — вынести `kmz_service.py` в отдельный pip-пакет; чистая логика без БД; расчёт lawnmower-пути, оптимального курса, шага по перекрытию для DJI Pilot 2
- [ ] **`crop-classifier`** — вынести `crop_classifier.py` (555 строк); профили 12 культур (NDVI min/max/peak, сезонность, нормы внесения); определение по гистограмме
- [ ] **`ndvi-vra`** — вынести `raster_service.py` + `core_math.py`; KMeans/перцентильное зонирование, морфология, векторизация, компенсаторная модель VRA
- [ ] **`dji-drone-meta`** — расширить существующую библиотеку: добавить PPK GPS из `.MRK`, нормализацию Reflectance, группировку каналов; опубликовать на PyPI
- [ ] **`ag-isoxml`** — допилить существующую: добавить tests, docs, опубликовать на PyPI

### Порядок публикации
1. `dji-drone-meta` (уже есть, расширить)
2. `ag-isoxml` (уже есть, допилить)
3. `kmz-mission` (новая, простая)
4. `crop-classifier` (новая, средняя)
5. `ndvi-vra` (новая, сложная)

## 🔧 Рефакторинг

### Критичный
- [ ] **Разбить handlers по файлам** — `field_handlers.py` (458 строк), `upload_handlers.py` (539 строк) содержат по 4-5 handlers; каждый handler в отдельный файл
- [ ] **Декоратор error handling** — все handlers дублируют `try/except → 500 → {"error": str(e)}`; вынести в基 класс `@handle_errors` или middleware
- [ ] **Разделить tasks.py** — смешивает orchestration (huey .delay()) с бизнес-логикой; логику в services, в tasks только вызовы
- [ ] **Удалить дубли моделей из db.py** — модели уже в `src/models/`, дубли в `db.py:60-110` не используются

### Высокий
- [ ] **Пагинация API** — `/api/fields`, `/api/fields_data` без LIMIT; добавить `?page=1&per_page=50`
- [ ] **Базовый метод парсинга JSON** — `json.loads(self.request.body)` дублируется во всех PUT/POST; добавить `self.parse_json_body()` в基 класс
- [ ] **Prefetch / joined loading** — N+1 в `FieldScansHandler` (`scan.zones.count()`), `FieldsApiHandler` (json.loads для каждого поля)
- [ ] **Индексы в БД** — `field.company_id`, `fieldscan.field_id`, `fieldzone.scan_id`, `fieldzone.field_id`, `fieldjournal.field_id`

### Средний
- [ ] **Разделить drone_processing_service.py** — GPS извлечение, NDVI расчёт, grid создание, зонирование — каждый в отдельный модуль
- [ ] **TypedDict / Pydantic models** — handlers возвращают `dict` без типизации
- [ ] **Вынести hardcoded константы** — цвета зон, лимиты, нормы в `constants.py` или конфиг

## ✅ Завершено (Архив достижений)
- [x] Рефакторинг на ES6 модули и Tornado Handlers (Март 2026)
- [x] Оптимизация RAM (Windowed reading, WAL mode)
- [x] Покрытие критических путей тестами (NDVI, VRA, Zoning)
