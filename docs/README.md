# Документация Field Mapper

## Обзор

Эта папка содержит полную документацию проекта Field Mapper — платформы точного земледелия.

---

## Структура документации

```
docs/
├── index.md                              # Главный индекс (TOC)
├── CONTEXT.md                            # Контекст проекта для разработчиков
├── workflow.md                           # Полный цикл Drone → Prescription
├── drone-imagery-guide.md                # Обработка дрон-снимков
├── DOCUMENTATION_MAP.md                  # Карта документации
│
├── getting-started/
│   ├── installation.md                   # Установка (Docker + Local)
│   ├── docker.md                         # Docker Compose
│   └── configuration.md                  # Конфигурация (env vars)
│
├── user-guide/
│   ├── fields.md                         # Управление полями
│   ├── ndvi.md                           # NDVI анализ
│   ├── isoxml.md                         # Карты предписаний ISOXML
│   ├── kmz-export.md                     # Экспорт KMZ для DJI
│   └── authentication.md                 # Auth + Multi-tenancy
│
├── developer-guide/
│   ├── architecture.md                   # Архитектура системы
│   ├── api-reference.md                  # REST API (полный)
│   ├── dji-integration.md                # DJI Mavic 3M интеграция
│   └── testing.md                        # Тестирование
│
├── changelog/
│   └── CHANGELOG.md                      # История изменений
│
├── archive/
│   ├── OPTIMIZATIONS.md                  # Оптимизации (архив)
│   └── REFACTORING.md                    # Рефакторинг 2026 (архив)
│
└── legal/
    ├── CONTRIBUTING.md                   # Вклад в проект
    ├── CODE_OF_CONDUCT.md                # Кодекс поведения
    └── SECURITY.md                       # Политика безопасности
```

---

## Быстрые ссылки

### Для пользователей

| Документ | Описание |
|----------|----------|
| [Установка](getting-started/installation.md) | Docker и локальная установка |
| [Управление полями](user-guide/fields.md) | Создание, редактирование, экспорт |
| [NDVI анализ](user-guide/ndvi.md) | Загрузка TIFF, зонирование |
| [Дрон-снимки](drone-imagery-guide.md) | Fast/orthomosaic режимы |
| [ISOXML экспорт](user-guide/isoxml.md) | Карты предписаний для техники |
| [KMZ экспорт](user-guide/kmz-export.md) | Карты для дронов DJI |

### Для разработчиков

| Документ | Описание |
|----------|----------|
| [Архитектура](developer-guide/architecture.md) | Backend, Frontend, Infrastructure |
| [API Reference](developer-guide/api-reference.md) | Все REST endpoints |
| [DJI интеграция](developer-guide/dji-integration.md) | Мультиспектральные данные |
| [Тестирование](developer-guide/testing.md) | Backend и Frontend тесты |
| [Contributing](legal/CONTRIBUTING.md) | Как внести вклад |
| [Security](legal/SECURITY.md) | Политика безопасности |

---

*Последнее обновление: 14 июня 2026 г.*
