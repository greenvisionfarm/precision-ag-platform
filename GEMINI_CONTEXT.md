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
    *   `static/js/main.js` — точка входа, роутинг (hash-based), UI-логика.
*   **Backend:** Модульный Tornado API.
    *   `src/handlers/` — контроллеры (fields, owners, upload, field_handlers).
    *   `src/services/` — бизнес-логика (GIS расчеты, KMZ генерация, raster_service).
    *   `db.py` — Peewee модели и управление БД.
*   **Данные:** SQLite (вектор), GeoTIFF (растр NDVI). Лимит загрузки: 1 ГБ.

## Ключевой функционал
1.  **Земельный учет:** Границы полей, кадастровый учет, статус аренды/собственности.
2.  **Агро-аналитика:** Загрузка GeoTIFF (NDVI), автоматическая векторизация растра в 3 зоны продуктивности (Низкая/Средняя/Высокая) через K-Means.
3.  **Точность:** Расчет площадей в EPSG:3035 (LAEA Europe).
4.  **Экспорт DJI KMZ (WPML 1.0.6):**
    *   Полная совместимость с DJI Pilot 2 (Mavic 3M).
    *   Поддержка параметров: Высота, Фронтальное/Боковое перекрытие, Угол курса (Course Angle).
    *   Автоматическая настройка мультиспектральной съемки (`visable,narrow_band`).
    *   Человекочитаемые имена файлов (напр. `Severny_uchastok_100m.kmz`).
5.  **PWA:** Поддержка офлайн-режима через Service Worker; локальное хранение ресурсов (переводы DataTables встроены в JS для обхода CORS и работы без интернета).

## Стек технологий
*   **Python:** Tornado, Peewee, GeoPandas, Shapely, Rasterio, Scikit-learn.
*   **JS:** jQuery, Leaflet, DataTables, SweetAlert2.
*   **UI:** CSS Variables, Dark Mode, Mobile First.

---
*Последнее обновление: 15 марта 2026 г.*
