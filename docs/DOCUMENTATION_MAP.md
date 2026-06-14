# Documentation Map — Field Mapper

> Полная карта документации проекта. Автоматически сгенерирована и будет обновляться.

---

## 1. Дерево документации

```
field_mapper/
├── README.md                          [203] Главный README проекта
├── ROADMAP.md                         [24]  Дорожная карта
│
├── docs/
│   ├── README.md                      [102] Обзор структуры docs/
│   ├── index.md                       [34]  Лендинг документации (TOC)
│   ├── CONTEXT.md                     [222] Контекст проекта для разработчиков
│   ├── workflow.md                    [295] Полный цикл Drone → Prescription
│   ├── REFACTORING.md                 [126] Итоги рефакторинга 2026 ⚠️ STALE
│   ├── drone-imagery-guide.md         [256] Руководство по дрон-снимкам
│   │
│   ├── getting-started/
│   │   ├── installation.md            [178] Установка (Docker + Local)
│   │   ├── docker.md                  [181] Настройка Docker Compose
│   │   ├── configuration.md           [174] Конфигурация (env vars, DB, Redis)
│   │   └── QUICKSTART_AUTH.md         [111] Быстрый старт: Auth + Multi-tenancy
│   │
│   ├── user-guide/
│   │   ├── fields.md                  [122] Управление полями
│   │   ├── ndvi.md                    [117] NDVI анализ
│   │   ├── isoxml.md                  [175] Карты предписаний ISOXML
│   │   ├── kmz-export.md             [156] Экспорт KMZ для DJI
│   │   └── authentication.md          [435] Auth + Multi-tenancy (полный)
│   │
│   ├── developer-guide/
│   │   ├── architecture.md            [217] Архитектура приложения
│   │   ├── API.md                     [129] API Reference (краткий)
│   │   ├── api-reference.md           [335] API Reference (полный)
│   │   ├── testing.md                 [264] Тестирование (Pytest + Jest)
│   │   ├── contributing.md            [287] Вклад в проект ⚠️ дублирует legal/
│   │   └── dji-integration.md         [40]  Интеграция с DJI Mavic 3M
│   │
│   ├── changelog/
│   │   └── CHANGELOG.md              [135] История изменений
│   │
│   ├── archive/
│   │   ├── OPTIMIZATIONS.md           [94]  Оптимизации (архив)
│   │   └── REFACTORING_PLAN.md        [126] План рефакторинга (архив) ⚠️ DUPLICATE
│   │
│   └── legal/
│       ├── CONTRIBUTING.md            [216] Вклад в проект (оф.)
│       ├── CODE_OF_CONDUCT.md         [57]  Кодекс поведения
│       └── SECURITY.md               [29]  Политика безопасности
│
├── src/services/
│   └── README.md                      [35]  Pipeline архитектура (services)
│
├── e2e/
│   └── README.md                      [377] E2E тестирование (Playwright)
│
├── libs/
│   ├── dji-drone-meta/README.md       [13]  DJI metadata extraction
│   └── ag-isoxml/README.md            [28]  ISOXML TaskFile generator
│
├── .ai/
│   ├── README.md                      [80]  Индекс AI контекстов
│   ├── gemini.md                      [316] AI контекст для Gemini
│   ├── qwen.md                        [391] AI контекст для Qwen Code
│   ├── GEMINI.md                      [53]  Краткий контекст Gemini
│   └── QWEN.md                        [6]   Заметки Qwen (deploy)
│
└── .github/
    ├── PULL_REQUEST_TEMPLATE.md       [36]  Шаблон PR
    └── ISSUE_TEMPLATE/blank.md        [22]  Шаблон Issue
```

**Итого:** 40 файлов, ~5400 строк

---

## 2. Документы по доменам

### 🟢 Продукт (Product)
Документы, описывающие что делает платформа и как ей пользоваться.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `README.md` | Лицевая страница проекта | Все |
| `docs/user-guide/fields.md` | Управление полями | Фермер/Агроном |
| `docs/user-guide/ndvi.md` | NDVI анализ | Фермер/Агроном |
| `docs/user-guide/isoxml.md` | Карты предписаний | Фермер/Агроном |
| `docs/user-guide/kmz-export.md` | Экспорт KMZ для DJI | Фермер/Агроном |
| `docs/user-guide/authentication.md` | Auth + Multi-tenancy | Фермер/Агроном |
| `docs/drone-imagery-guide.md` | Обработка дрон-снимков | Фермер/Агроном |
| `docs/workflow.md` | Полный цикл Drone → Prescription | Фермер/Агроном |
| `ROADMAP.md` | Дорожная карта | Команда |

### 🔵 Архитектура (Architecture)
Документы, описывающие внутреннее устройство системы.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `docs/CONTEXT.md` | Контекст проекта (дерево, стек, features) | Разработчик |
| `docs/developer-guide/architecture.md` | Архитектура (диаграммы, модули) | Разработчик |
| `src/services/README.md` | Pipeline архитектуры services | Разработчик |
| `docs/developer-guide/dji-integration.md` | DJI интеграция | Разработчик |

### 🟡 API
Документация REST API.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `docs/developer-guide/API.md` | API Reference (краткий) | Разработчик |
| `docs/developer-guide/api-reference.md` | API Reference (полный) | Разработчик |

### 🟠 Инфраструктура (Infrastructure)
Документы по развёртыванию и конфигурации.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `docs/getting-started/installation.md` | Установка | DevOps/Разработчик |
| `docs/getting-started/docker.md` | Docker Compose | DevOps/Разработчик |
| `docs/getting-started/configuration.md` | Конфигурация | DevOps/Разработчик |
| `docs/getting-started/QUICKSTART_AUTH.md` | Auth быстрый старт | Разработчик |

### 🔴 Процессы (Processes)
Как вносить вклад, тестировать, оформлять PR.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `docs/legal/CONTRIBUTING.md` | Вклад в проект (оф.) | Разработчик |
| `docs/developer-guide/contributing.md` | Вклад в проект ⚠️ | Разработчик |
| `docs/developer-guide/testing.md` | Тестирование | Разработчик |
| `e2e/README.md` | E2E тестирование | Разработчик |
| `.github/PULL_REQUEST_TEMPLATE.md` | Шаблон PR | Разработчик |
| `.github/ISSUE_TEMPLATE/blank.md` | Шаблон Issue | Разработчик |
| `docs/legal/CODE_OF_CONDUCT.md` | Кодекс поведения | Все |
| `docs/legal/SECURITY.md` | Политика безопасности | Все |

### 🟣 Операции (Operations)
Changelog, оптимизации, рефакторинг.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `docs/changelog/CHANGELOG.md` | История изменений | Все |
| `docs/archive/OPTIMIZATIONS.md` | Оптимизации (архив) | Разработчик |
| `docs/REFACTORING.md` | Итоги рефакторинга ⚠️ | Разработчик |
| `docs/archive/REFACTORING_PLAN.md` | План рефакторинга ⚠️ | Разработчик |

### ⚪ Исследования / AI Context
Контекстные файлы для AI-агентов и библиотеки.

| Файл | Назначение | Аудитория |
|------|-----------|-----------|
| `.ai/README.md` | Индекс AI контекстов | AI/Разработчик |
| `.ai/gemini.md` | AI контекст Gemini | AI |
| `.ai/qwen.md` | AI контекст Qwen | AI |
| `.ai/GEMINI.md` | Краткий контекст Gemini | AI |
| `.ai/QWEN.md` | Заметки Qwen | AI |
| `libs/dji-drone-meta/README.md` | DJI metadata lib | Разработчик |
| `libs/ag-isoxml/README.md` | ISOXML lib | Разработчик |

---

## 3. Single Source of Truth (SSoT)

Документы, которые являются **единственным authoritative источником** для своей области. Все остальные документы должны ссылаться на них, а не дублировать.

| Домен | SSoT Файл | Что покрывает |
|-------|-----------|---------------|
| **Установка** | `docs/getting-started/installation.md` | Docker, local, Redis, зависимости |
| **Конфигурация** | `docs/getting-started/configuration.md` | Env vars, DB, Redis, GDAL, security |
| **Auth & Multi-tenancy** | `docs/user-guide/authentication.md` | Роли, API auth, data isolation, bcrypt |
| **NDVI Analysis** | `docs/user-guide/ndvi.md` | Upload, zoning, VRA, DJI support |
| **Drone Processing** | `docs/drone-imagery-guide.md` | Fast/orthomosaic modes, API, troubleshooting |
| **Workflow** | `docs/workflow.md` | Полный цикл Drone → Prescription |
| **API Reference** | `docs/developer-guide/api-reference.md` | Все endpoints, request/response |
| **Architecture** | `docs/developer-guide/architecture.md` | Системные диаграммы, модули |
| **Changelog** | `docs/changelog/CHANGELOG.md` | Все версии и изменения |
| **Contributing** | `docs/legal/CONTRIBUTING.md` | PR process, standards, workflow |
| **Security** | `docs/legal/SECURITY.md` | Vulnerability reporting, policy |
| **Project Context** | `docs/CONTEXT.md` | Единый контекст для разработчиков |
| **AI Context (Qwen)** | `.ai/qwen.md` | Полный контекст для Qwen Code |
| **AI Context (Gemini)** | `.ai/gemini.md` | Полный контекст для Gemini |
| **Services Pipeline** | `src/services/README.md` | Архитектура services |

---

## 4. Кандидаты на удаление / архивирование

### 🔴 Удалить (дубликаты / полностью stale)

| Файл | Причина | Действие |
|------|---------|----------|
| `docs/archive/REFACTORING_PLAN.md` | Точный дубликат `docs/REFACTORING.md` | **Удалить** |
| `docs/REFACTORING.md` | Ссылается на ветку `feature/refactoring-2026` (слито в марте), устаревшие метрики, ссылка на удалённый lru_cache | **Перенести в archive/** |

### 🟡 Архивировать (полезно, но неактуально)

| Файл | Причина | Действие |
|------|---------|----------|
| `docs/archive/OPTIMIZATIONS.md` | Уже в archive/,acceptable staleness | Оставить как есть |

### 🟠 Дедуплицировать (два источника для одного домена)

| Домен | Файл A | Файл B | Рекомендация |
|-------|--------|--------|-------------|
| Contributing | `docs/legal/CONTRIBUTING.md` (216 строк, актуальный) | `docs/developer-guide/contributing.md` (287 строк, stale: сломанная ссылка на TODO.md, неверные относительные пути) | **Удалить** `developer-guide/contributing.md`, перенести уникальное в `legal/CONTRIBUTING.md` |
| API Reference | `docs/developer-guide/API.md` (129 строк, краткий) | `docs/developer-guide/api-reference.md` (335 строк, полный) | **Удалить** `API.md`, оставить `api-reference.md` как SSoT |
| AI Context (Gemini) | `.ai/gemini.md` (316 строк, полный) | `.ai/GEMINI.md` (53 строки, краткий) | **Удалить** `GEMINI.md`, оставить `gemini.md` как SSoT |
| AI Context (Qwen) | `.ai/qwen.md` (391 строка, полный) | `.ai/QWEN.md` (6 строк, заметки deploy) | **Удалить** `QWEN.md`, перенести deploy-заметки в `qwen.md` |
| Auth Quick Start | `docs/getting-started/QUICKSTART_AUTH.md` (111 строк) | `docs/user-guide/authentication.md` (435 строк, полный) | **Удалить** `QUICKSTART_AUTH.md`, он ссылается на SHA-256 (неверно) |

### 📊 Итого по рекомендациям

| Действие | Кол-во файлов |
|----------|--------------|
| **Удалить** | 6 (REFACTORING_PLAN.md, developer-guide/contributing.md, API.md, GEMINI.md, QWEN.md, QUICKSTART_AUTH.md) |
| **Перенести в archive/** | 1 (REFACTORING.md) |
| **Обновить (NEEDS_UPDATE)** | 17 |
| **Оставить как есть (OK)** | 16 |

---

## 5. Матрица связей: Документы ↔ Команды/Роли

### Роли

| Роль | Описание |
|------|----------|
| **Фермер** | Конечный пользователь, загружает данные, смотрит карты |
| **Агроном** | АNALYZES NDVI, создаёт предписания, управляет полями |
| **Разработчик** | Пишет код, тестирует, делает PR |
| **DevOps** | Разворачивает, мониторит, деплоит |
| **AI Agent** | Использует контекстные файлы для генерации кода |

### Матрица

| Документ | Фермер | Агроном | Разработчик | DevOps | AI Agent |
|----------|:------:|:-------:|:-----------:|:------:|:--------:|
| **README.md** | 👁 | 👁 | 👁 | 👁 | |
| **ROADMAP.md** | | | 👁 | | |
| **user-guide/fields.md** | ✅ | ✅ | | | |
| **user-guide/ndvi.md** | ✅ | ✅ | | | |
| **user-guide/isoxml.md** | ✅ | ✅ | | | |
| **user-guide/kmz-export.md** | ✅ | ✅ | | | |
| **user-guide/authentication.md** | 👁 | 👁 | 👁 | | |
| **drone-imagery-guide.md** | ✅ | ✅ | 👁 | | |
| **workflow.md** | 👁 | ✅ | 👁 | | |
| **getting-started/installation.md** | | | ✅ | ✅ | |
| **getting-started/docker.md** | | | 👁 | ✅ | |
| **getting-started/configuration.md** | | | 👁 | ✅ | |
| **developer-guide/architecture.md** | | | ✅ | 👁 | |
| **developer-guide/api-reference.md** | | | ✅ | | 👁 |
| **developer-guide/testing.md** | | | ✅ | | |
| **developer-guide/dji-integration.md** | | | ✅ | | |
| **changelog/CHANGELOG.md** | | | 👁 | | |
| **legal/CONTRIBUTING.md** | | | ✅ | | |
| **legal/SECURITY.md** | | | 👁 | 👁 | |
| **src/services/README.md** | | | ✅ | | |
| **e2e/README.md** | | | ✅ | | |
| **.ai/gemini.md** | | | 👁 | | ✅ |
| **.ai/qwen.md** | | | 👁 | | ✅ |
| **libs/*/README.md** | | | ✅ | | |
| **CONTEXT.md** | | | ✅ | | ✅ |

**Легенда:** ✅ = основной пользователь, 👁 = читает/ссылается

---

## 6. Проблемы целостности (Cross-reference Errors)

| Проблема | Где | Что не так |
|----------|-----|-----------|
| **SHA-256 → bcrypt** | `QUICKSTART_AUTH.md:96`, `authentication.md:369`, `SECURITY.md:27` | Написано SHA-256, код использует bcrypt |
| **lru_cache удалён** | `REFACTORING.md:97`, `architecture.md:170-182`, `.ai/gemini.md:229`, `.ai/qwen.md:268` | Ссылки на удалённый код |
| **Сломанная ссылка TODO.md** | `developer-guide/contributing.md:49` | TODO.md удалён |
| **Сломанные ссылки на файлы** | `README.md:170,198` | CONTRIBUTING.md и SECURITY.md в корне не существуют (в `docs/legal/`) |
| **Сломанные пути .ai-contexts/** | `.ai/README.md:16,29`, `.ai/qwen.md:184-187` | Путь `.ai-contexts/` не существует, правильный `.ai/` |
| **Не упомянутые файлы** | `CONTEXT.md`, `architecture.md`, `services/README.md` | orthomosaic_service.py, analysis_service.py, provider_dji.py, middleware/, journal_handlers.py |
| **Orthomosaic не задокументирован** | `workflow.md`, `dji-integration.md`, `API.md`, `api-reference.md`, `CHANGELOG.md` | Новая фича не отражена |

---

## 7. Приоритеты обновления

### 🔴 Критично (вводит в заблуждение)
1. Исправить SHA-256 → bcrypt в 3 файлах
2. Удалить дубликаты (6 файлов)
3. Перенести REFACTORING.md в archive/

### 🟡 Важно (неполная/устаревшая информация)
4. Добавить orthomosaic в workflow.md, dji-integration.md, api-reference.md, CHANGELOG.md
5. Обновить деревья файлов в CONTEXT.md, architecture.md, services/README.md
6. Исправить сломанные ссылки (README.md, contributing.md)
7. Обновить test counts в testing.md, installation.md, e2e/README.md

### 🟢 Желательно (косметика)
8. Обновить даты "Last updated" во всех файлах
9. Обновить .ai/gemini.md и .ai/qwen.md (убрать lru_cache, добавить orthomosaic)
10. Обновить ROADMAP.md (orthomosaic done, следующие цели)
