# Контекст проекта для Gemini

Этот файл служит напоминанием о ключевых аспектах проекта, используемых технологиях и принятых подходах.

## Общая информация

*   **Название проекта:** Field Mapper
*   **Тип проекта:** Single Page Application (SPA) с Headless Backend.
*   **Основная цель:** Управление геоданными полей, учет прав собственности и кадастровых номеров.

## Архитектура

*   **Backend:** Чистый REST API на Tornado. Больше не использует серверные шаблоны (Jinja2/Tornado templates).
*   **Frontend:** SPA на базе `static/index.html` и `static/js/main.js`.
*   **Роутинг:** Клиентский, через хэш-навигацию (`#map`, `#fields`, `#owners`).

## Стек технологий

### Backend
*   **Язык:** Python 3.12
*   **Веб-фреймворк:** [Tornado](https://www.tornadoweb.org/) (асинхронный API сервер)
*   **ORM:** [Peewee](http://docs.peewee-orm.com/) (SQLite)
*   **Гео-процессинг:** [GeoPandas](https://geopandas.org/), [Shapely](https://shapely.readthedocs.io/)

### Frontend
*   **Языки:** HTML5, CSS3 (CSS Variables, Mobile First), JS (ES6+)
*   **Библиотеки:** jQuery 3.7, Leaflet 1.9, Leaflet.draw, DataTables
*   **PWA:** Поддержка Manifest.json и Service Worker для мобильной установки и кэширования.
*   **Темы:** Светлая и Темная (автоматическая смена слоев карты).

## Функциональность

*   **Земельный учет:** Хранение `land_status` (Собственность/Аренда) и `parcel_number`.
*   **Интерактивность:** Рисование и редактирование полей на карте, инлайн-редактирование в таблицах.
*   **Загрузка:** Импорт Shape-файлов из ZIP-архивов.

---
*Последнее обновление: 8 марта 2026 г.*
