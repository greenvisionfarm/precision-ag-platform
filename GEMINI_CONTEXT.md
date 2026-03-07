# Контекст проекта для Gemini

## Общая информация
*   **Название:** Field Mapper
*   **Тип:** Open Source платформа точного земледелия (Precision Agriculture).
*   **Основная цель:** Полный цикл от полета дрона (DJI Mavic 3M) до карты предписаний для трактора.

## Архитектура
*   **Frontend:** SPA (Single Page Application), PWA, Leaflet.js.
*   **Backend:** Headless REST API на Tornado (Python).
*   **Данные:** SQLite (вектор), в будущем GeoTIFF (растр).

## Ключевой функционал
1.  **Земельный банк:** Границы полей, кадастровый учет (Словакия), статус аренды.
2.  **Обработка данных дронов (Roadmap):**
    *   Загрузка мультиспектральных ортофотопланов (GeoTIFF).
    *   Расчет вегетационных индексов (NDVI, NDRE).
    *   Зонирование поля по продуктивности.
    *   Экспорт карт для дифференцированного внесения (VRA).

## Стек технологий
*   **Python:** Tornado, Peewee, GeoPandas, Shapely. *Планируется: Rasterio, NumPy.*
*   **JS:** jQuery, Leaflet, DataTables.
*   **UI:** CSS Variables, Dark Mode, Mobile First.

---
*Последнее обновление: 8 марта 2026 г.*
