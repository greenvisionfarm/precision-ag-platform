# Контекст проекта для Gemini

## Общая информация
*   **Название:** Field Mapper
*   **Путь к проекту:** `/home/vladibuyanov/PycharmProjects/field_mapper`
*   **Тип:** Open Source платформа точного земледелия (Precision Agriculture).
*   **Основная цель:** Полный цикл от полета дрона (DJI Mavic 3M) до карты предписаний для трактора.

## Архитектура
*   **Frontend:** Модульное SPA.
    *   `static/js/modules/api.js` — взаимодействие с REST API.
    *   `static/js/modules/map_manager.js` — инкапсуляция Leaflet.js и ГИС-логики.
    *   `static/js/main.js` — точка входа, роутинг (hash-based: #map, #fields, #field/ID).
*   **Backend:** Модульный Tornado API.
    *   `src/handlers/` — контроллеры (fields, owners, upload, field_handlers).
    *   `src/services/` — бизнес-логика (GIS расчеты, KMZ генерация, raster_service).
    *   `db.py` — Peewee модели и управление миграциями.
*   **Данные:** SQLite (вектор), GeoTIFF (растр NDVI). Лимит загрузки увеличен до 1 ГБ для поддержки тяжелых ортофотопланов.

## Ключевой функционал
1.  **Земельный учет:** Границы полей, кадастровый учет, статус аренды/собственности. Отдельная страница деталей поля (`#field/ID`).
2.  **Интерактивность:** При клике на поле на карте открывается полноценное модальное окно (SweetAlert2) с детальной информацией, мини-картой и быстрым экспортом KMZ.
3.  **Агро-аналитика:** Загрузка GeoTIFF (NDVI), автоматическая векторизация растра в 3 зоны продуктивности (Низкая/Средняя/Высокая) через K-Means кластеризацию с отрисовкой на карте.
4.  **Точность:** Расчет площадей в EPSG:3035 (LAEA Europe) через `gis_service.py`.
5.  **Экспорт DJI:** Генерация полетных заданий через `kmz_service.py` (Mavic 3M compatible).
6.  **Безопасное тестирование:** Изоляция через `FIELD_MAPPER_ENV=test` (использует `test_fields.db`).


## Стек технологий
*   **Python:** Tornado, Peewee, GeoPandas, Shapely, Rasterio, Scikit-learn (K-Means).
*   **JS:** jQuery, Leaflet, DataTables.
*   **Архитектура API:**
    *   `GET /api/field/[ID]` — детальные данные поля + геометрия.
    *   `GET /api/fields_data` — список полей для таблиц.
    *   `POST /api/field/add` — создание нового поля.
    *   `POST /api/upload` — загрузка GeoTIFF/KMZ/Shapefile.
*   **UI:** CSS Variables, Dark Mode, Mobile First.
*   **PWA:** Manifest и Service Worker (версия v3+) для установки и офлайн-кэша.


---
*Последнее обновление: 15 марта 2026 г.*

