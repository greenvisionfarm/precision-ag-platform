# Контекст проекта для Gemini

## Общая информация
*   **Название:** Field Mapper
*   **Путь к проекту:** `/home/vladibuyanov/PycharmProjects/field_mapper`
*   **Тип:** Open Source платформа точного земледелия (Precision Agriculture).
*   **Основная цель:** Полный цикл от полета дрона (DJI Mavic 3M) до карты предписаний для трактора.

## Архитектура
*   **Frontend:** SPA (Single Page Application), PWA, Leaflet.js. Клиентский роутинг через hash (#map, #fields, #owners).
*   **Backend:** Headless REST API на Tornado (Python).
*   **Данные:** SQLite (вектор), в будущем GeoTIFF (растр).

## Ключевой функционал
1.  **Земельный учет:** Границы полей, кадастровый учет, статус аренды/собственности, кадастровые номера. Полный цикл управления владельцами (добавление, удаление с очисткой связей).
2.  **Точность:** Расчет площадей в гектарах выполняется в равновеликой проекции **EPSG:3035 (LAEA Europe)**.
3.  **Экспорт в DJI Pilot (KMZ):** Генератор полетных заданий для Mavic 3M (XML template.kml). Поддержка кастомизации высоты (20-120м) и перекрытий (H/W overlap) через UI (SweetAlert2).
4.  **Тестирование:** Python (Pytest) для бэкенда и Node.js (Jest + JSDOM) для фронтенда.
5.  **Обработка данных дронов (Roadmap):**
    *   Загрузка мультиспектральных ортофотопланов (GeoTIFF).
    *   Расчет вегетационных индексов (NDVI, NDRE).
    *   Зонирование поля по продуктивности.
    *   Экспорт карт для дифференцированного внесения (VRA).

## Стек технологий
*   **Python:** Tornado, Peewee, GeoPandas, Shapely.
*   **JS:** jQuery, Leaflet, DataTables.
*   **UI:** CSS Variables, Dark Mode, Mobile First.
*   **PWA:** Manifest и Service Worker (версия v3+) для установки и офлайн-кэша.

---
*Последнее обновление: 8 марта 2026 г.*
