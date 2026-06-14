# Документация Field Mapper

Добро пожаловать в документацию Field Mapper — платформы точного земледелия с открытым исходным кодом.

## Разделы документации

### Быстрый старт
- [Установка](getting-started/installation.md) — Docker и локальная установка
- [Настройка Docker](getting-started/docker.md) — запуск через Docker Compose
- [Конфигурация](getting-started/configuration.md) — переменные окружения и настройки

### Руководство пользователя
- [Управление полями](user-guide/fields.md) — создание, редактирование, экспорт
- [NDVI анализ](user-guide/ndvi.md) — загрузка и зонирование
- [Экспорт KMZ](user-guide/kmz-export.md) — создание заданий для DJI
- [ISOXML экспорт](user-guide/isoxml.md) — карты предписаний для техники
- [Auth & Multi-tenancy](user-guide/authentication.md) — роли, API auth, изоляция данных
- [Workflow: Drone → Prescription](workflow.md) — полный цикл обработки
- [Дрон-снимки](drone-imagery-guide.md) — fast/orthomosaic режимы

### Для разработчиков
- [Архитектура](developer-guide/architecture.md) — обзор системы
- [API Reference](developer-guide/api-reference.md) — все REST endpoints
- [Интеграция с DJI](developer-guide/dji-integration.md) — работа с мультиспектральными данными
- [Тестирование](developer-guide/testing.md) — запуск тестов
- [Pipeline: services](../src/services/README.md) — архитектура services

### Контекст проекта
- [CONTEXT.md](CONTEXT.md) — технический контекст для разработчиков

### История изменений
- [Changelog](changelog/CHANGELOG.md) — версии и изменения

---

*Последнее обновление: 14 июня 2026 г.*
