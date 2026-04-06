# 📚 Документация Field Mapper

## Обзор

Эта папка содержит полную документацию проекта Field Mapper — платформы точного земледелия.

---

## 📖 Структура документации

```
docs/
├── index.md                          # Главный индекс документации
├── CONTEXT.md                        # Контекст проекта
├── REFACTORING.md                    # История рефакторинга 2026
│
├── getting-started/
│   └── installation.md               # Быстрый старт и установка
│
├── user-guide/
│   ├── fields.md                     # Управление полями
│   ├── ndvi.md                       # NDVI анализ и зонирование
│   ├── kmz-export.md                 # Экспорт KMZ для дронов
│   └── isoxml.md                     # ISOXML экспорт для техники ⭐ NEW
│
├── developer-guide/
│   ├── architecture.md               # Архитектура системы
│   ├── API.md                        # API Reference ⭐ NEW
│   ├── contributing.md               # Вклад в проект
│   └── testing.md                    # Тестирование
│
└── changelog/
    └── CHANGELOG.md                  # История изменений
```

---

## 🎯 Быстрые ссылки

### Для пользователей

| Документ | Описание |
|----------|----------|
| [🚀 Установка](getting-started/installation.md) | Быстрый старт за 5 минут |
| [📋 Управление полями](user-guide/fields.md) | Создание, редактирование, экспорт |
| [🚁 NDVI анализ](user-guide/ndvi.md) | Загрузка TIFF, зонирование |
| [🚜 ISOXML экспорт](user-guide/isoxml.md) | Карты предписаний для техники |
| [📤 KMZ экспорт](user-guide/kmz-export.md) | Карты для дронов DJI |

### Для разработчиков

| Документ | Описание |
|----------|----------|
| [🏗️ Архитектура](developer-guide/architecture.md) | Backend, Frontend, Infrastructure |
| [📡 API Reference](developer-guide/API.md) | Полная документация API |
| [🧪 Тестирование](developer-guide/testing.md) | Backend и Frontend тесты |
| [🤝 Contributing](developer-guide/contributing.md) | Как внести вклад |

---

## 📊 Статистика документации

| Метрика | Значение |
|---------|----------|
| **Файлов документации** | 12 |
| **Страниц** | ~25 |
| **API endpoints** | 15+ |
| **Примеров кода** | 30+ |
| **Последнее обновление** | 24 марта 2026 |

---

## 🆕 Последние изменения

### Март 2026

- ✅ **ISOXML экспорт** — полное руководство по картам предписаний
- ✅ **API Reference** — документация всех endpoints
- ✅ **Улучшенное зонирование** — морфологическая обработка растров
- ✅ **Новый UI** — статистика зон и легенда на карте
- ✅ **22 теста** — интеграционные и модульные тесты

---

## 🔗 Внешние ресурсы

- [ISO 11783 стандарт](https://www.iso.org/standard/72947.html)
- [ISOXML TaskFile спецификация](https://www.isobus.net/)
- [John Deere Operations Center](https://operationscenter.johndeere.com/)
- [Claas Connect](https://www.claas-connect.com/)
- [Rasterio документация](https://rasterio.readthedocs.io/)
- [Leaflet JS](https://leafletjs.com/)

---

## 📝 Лицензия

Документация распространяется под той же лицензией что и проект Field Mapper.

---

*Последнее обновление: 24 марта 2026 г.*
