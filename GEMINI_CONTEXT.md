# Контекст проекта для Gemini

## Общая информация
*   **Название:** Field Mapper
*   **Тип:** Open Source платформа точного земледелия (Precision Agriculture).
*   **Цель:** Цикл от полета дрона (Mavic 3M) до карты предписаний (VRA).

## Архитектура (Docker-based)
Проект развернут в Docker-окружении (App, Worker, Redis, Nginx). 
В образ `app` включены все ГИС-зависимости (GDAL/PROJ), Python 3.12 и Node.js 20.

### Запуск тестов внутри Docker:
*   **Python (Pytest):**
    `docker compose exec -e FIELD_MAPPER_ENV=test app pytest tests/`
*   **JavaScript (Jest):**
    `docker compose exec app npm test`

## Ключевой функционал
1.  **Земельный учет:** Границы полей, кадастровый учет, площади в EPSG:3035.
2.  **Асинхронный NDVI Анализ:** Загрузка GeoTIFF (до 1 ГБ), фоновое зонирование (Huey + Redis).
3.  **Экспорт DJI KMZ (WPML 1.0.6):** Совместимость с Mavic 3M, углы курса, перекрытия.
4.  **PWA:** Офлайн-кэш, локальные переводы (DataTables).

## Стек технологий
*   **Backend:** Python 3.12 (Tornado, Peewee, Huey, Rasterio, Scikit-learn).
*   **Infrastructure:** Docker, Docker Compose, Redis, Nginx.
*   **Frontend:** Node.js 20, jQuery, Leaflet, DataTables, Jest.

---
*Последнее обновление: 15 марта 2026 г.*
