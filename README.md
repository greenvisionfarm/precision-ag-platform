# Field Mapper

Field Mapper — это веб-приложение для визуализации и управления географическими данными полей. Построено как современное SPA (Single Page Application) с Python-бэкендом.

## Основные возможности

- **SPA Архитектура:** Мгновенное переключение между картой и списками без перезагрузки страницы.
- **PWA (Progressive Web App):** Приложение можно установить на смартфон, поддерживает офлайн-кэширование статики.
- **Земельный учет:** Учет статуса полей (Собственность / Аренда / Субаренда) и кадастровых номеров.
- **Интерактивная карта:** Рисование и редактирование границ полей прямо в браузере.
- **Темная тема:** Полная поддержка темного режима, включая карты и таблицы.
- **Загрузка Shape-файлов:** Импорт данных из ZIP-архивов.

## Стек технологий

- **Backend:** Tornado (Python), Peewee ORM, GeoPandas.
- **Frontend:** HTML5/CSS3 (Variables), jQuery, Leaflet.js, DataTables.

## Установка и запуск

1. `python -m venv venv`
2. `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python app.py`
5. Откройте [http://localhost:8888](http://localhost:8888).

## API Эндпоинты

- `GET /api/fields`: Все поля в формате GeoJSON.
- `GET /api/fields_data`: Данные для таблиц.
- `GET /api/owners`: Список владельцев.
- `PUT /api/field/update_details/<id>`: Обновление статуса земли и кадастрового номера.
- `PUT /api/field/rename/<id>`: Переименование поля.
- `DELETE /api/field/delete/<id>`: Удаление поля.
