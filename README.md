# Field Mapper

> Платформа точного земледелия с открытым исходным кодом

[![Tests](https://img.shields.io/badge/tests-32%20passed%2C%201%20skipped-green)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Node](https://img.shields.io/badge/node-20-green)]()
[![Docker](https://img.shields.io/badge/docker-ready-blue)]()
[![License](https://img.shields.io/badge/license-Open%20Source-green)]()

**Field Mapper** — веб-платформа для фермеров и агрономов, которая превращает данные с дронов (DJI Mavic 3M, NDVI снимки) в карты предписаний для сельскохозяйственной техники.

![Field Mapper Interface](docs/assets/screenshot.png)

---

## 🚀 Возможности

| 🌱 **Управление полями** | 🚁 **NDVI анализ** | 📤 **Экспорт** | 🚜 **Карты предписаний** |
|-------------------------|-------------------|---------------|-------------------------|
| Границы на карте | Загрузка GeoTIFF | **ISOXML** (John Deere, Claas) | Автоматический расчёт норм |
| Владельцы и кадастр | Автоматическое зонирование | DJI KMZ (WPML 1.0.6) | 3 зоны продуктивности |
| Импорт/экспорт KMZ | Крупные агрегированные зоны | Shapefile | Нормы: 150/250/350 кг/га |
| Статистика и отчёты | **История сканов** | Массовый экспорт ZIP | Статистика по зонам |
| | **Удаление сканов** | | |
| | **Fullscreen режим** | | |

---

## ⚡ Быстрый старт

### Docker (рекомендуется)

```bash
docker-compose up -d --build
```

Откройте [http://localhost](http://localhost)

### Локально

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && npm install
python app.py
```

Откройте [http://localhost:8888](http://localhost:8888)

📖 **Подробная инструкция:** [docs/getting-started/installation.md](docs/getting-started/installation.md)

---

## 📚 Документация

| Раздел | Описание |
|--------|----------|
| [🚀 Быстрый старт](docs/getting-started/installation.md) | Установка и настройка |
| [👤 Руководство пользователя](docs/user-guide/fields.md) | Управление полями, NDVI, экспорт |
| [🚜 Карты предписаний](docs/user-guide/isoxml.md) | ISOXML экспорт, нормы внесения |
| [👨‍💻 Для разработчиков](docs/developer-guide/architecture.md) | Архитектура, API, тестирование |
| [📋 Changelog](docs/changelog/CHANGELOG.md) | История изменений |
| [📅 Roadmap](TODO.md) | Планы развития |
| [🤖 AI Contexts](.ai-contexts/) | Контекст для AI ассистентов |

---

## 🏗️ Архитектура

```
┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   Tornado   │
│  (80/443)   │     │   (8888)    │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    │   /Postgres │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Redis+Huey │
                    │  (Queue)    │
                    └─────────────┘
```

**Стек:**
- **Backend:** Python 3.12 (Tornado, Peewee, Huey, GDAL, Rasterio, Scikit-learn)
- **Frontend:** jQuery, Leaflet, DataTables, Chart.js, ES6 Modules
- **Infrastructure:** Docker, Redis, Nginx

📖 **Подробнее:** [docs/developer-guide/architecture.md](docs/developer-guide/architecture.md)

---

## ✅ Тесты

```bash
# Backend
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/

# Frontend
npm test

# В Docker
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest tests/
docker-compose run --rm app npm test
```

**Статус:** 32 passed, 1 skipped

---

## 🤝 Вклад в проект

Приветствуются:
- Баг-репорты и фич-реквесты (GitHub Issues)
- Pull Request'ы с исправлениями и улучшениями
- Документация и переводы
- Тесты и CI/CD

📖 **Инструкция:** [docs/developer-guide/contributing.md](docs/developer-guide/contributing.md)

---

## 📊 Метрики проекта

| Метрика | Значение |
|---------|----------|
| **Тесты** | 32 passed, 1 skipped |
| **Покрытие** | ~65% (backend) |
| **Размер образа** | ~1.5 GB (с GIS) |
| **Время сборки** | ~6 мин (с кэшем ~2 мин) |
| **Ветка** | `feature/refactoring-2026` (готова к merge) |

---

## 📝 Лицензия

Open Source проект для развития точного земледелия.

---

## 🔗 Контакты

- **Сайт:** [http://localhost:8888](http://localhost:8888)
- **GitHub:** [your-org/field-mapper](https://github.com/your-org/field-mapper)
- **Документация:** [docs/](docs/)

---

*Последнее обновление: 25 марта 2026 г.*
