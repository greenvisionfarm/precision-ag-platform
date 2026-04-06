# Contributing to Field Mapper

Приветствуем контрибьюторов! Field Mapper — open-source платформа точного земледелия, и мы рады любому вкладу.

> ⚠️ **Важно:** Проект находится в активной разработке и **ещё не протестирован в полной мере в production условиях**. Используйте на свой страх и риск.

---

## 📋 Содержание

- [Code of Conduct](#code-of-conduct)
- [Как начать](#как-начать)
- [Git Workflow](#git-workflow)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Testing](#testing)
- [Documentation](#documentation)
- [AI-Assisted Development](#ai-assisted-development)

---

## Code of Conduct

Этот проект подчиняется [Code of Conduct](CODE_OF_CONDUCT.md). Участвуя, вы соглашаетесь с ним.

---

## Как начать

### 1. Форкните репозиторий

```bash
gh repo fork greenvisionfarm/precision-ag-platform
```

### 2. Клонируйте и настройте

```bash
git clone <your-fork-url>
cd precision-ag-platform
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install
```

### 3. Запустите

```bash
# Docker (рекомендуется)
docker-compose up -d --build

# Локально
python app.py
```

### 4. Запустите тесты

```bash
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/
npm test
```

---

## Git Workflow

### Ветки

| Ветка | Описание |
|-------|----------|
| `master` | Основная ветка, стабильный код |
| `feature/*` | Новые фичи |
| `fix/*` | Исправления багов |
| `docs/*` | Изменения в документации |
| `release/*` | Подготовка релиза |

### Процесс

1. Создайте ветку от `master`: `git checkout -b feature/my-feature`
2. Делайте коммиты с понятными сообщениями
3. Убедитесь, что тесты проходят
4. Создайте Pull Request

---

## Commit Messages

Используем [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]
```

**Types:**
- `feat` — новая фича
- `fix` — исправление бага
- `docs` — документация
- `style` — форматирование (без логики)
- `refactor` — рефакторинг
- `test` — тесты
- `chore` — обслуживание
- `perf` — оптимизация
- `security` — безопасность

**Примеры:**
```
feat: добавить экспорт ISOXML для карт-заданий
fix: исправить порядок отрисовки слоёв на карте
docs: обновить README с правильными ссылками
test: добавить интеграционные тесты для обработки TIFF
```

---

## Pull Requests

### Чеклист перед PR

- [ ] Тесты проходят (`pytest tests/` + `npm test`)
- [ ] Код отформатирован (`black .`, `eslint --fix`)
- [ ] Документация обновлена
- [ ] Коммиты следуют Conventional Commits
- [ ] Нет чувствительных данных в коммитах

### Описание PR

```markdown
## Описание
Что делает этот PR и зачем.

## Изменения
- Добавлено ...
- Исправлено ...
- Удалено ...

## Тестирование
Как проверить изменения.

## Скриншоты (для UI изменений)
До/После
```

---

## Testing

### Backend

```bash
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ -v
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ --cov=src
```

### Frontend

```bash
npm test
```

### E2E (Playwright)

```bash
npx playwright test
```

---

## Documentation

Документация находится в `docs/`. Структура:

```
docs/
├── getting-started/    # Установка и настройка
├── user-guide/         # Руководства пользователя
├── developer-guide/    # Для разработчиков
├── changelog/          # История изменений
└── index.md            # Оглавление
```

При добавлении фичи — обновите соответствующую документацию.

---

## AI-Assisted Development

> Этот проект создан и развивается при активной поддержке **AI-агентов** (Qwen Code, и др.). Это не недостаток, а особенность нашего workflow.

### Что это значит

- **Скорость разработки:** AI ускоряет написание кода, тестов и документации
- **Качество кода:** AI помогает следовать best practices
- **Документация:** AI помогает поддерживать документацию в актуальном состоянии

### Как контрибьютить с AI

Если вы тоже используете AI-ассистентов — это приветствуется! Главное:
- Код должен быть понятным и поддерживаемым
- Тесты должны покрывать новую функциональность
- Документация должна быть актуальной

---

## 🚀 Roadmap

См. [GitHub Issues](https://github.com/greenvisionfarm/precision-ag-platform/issues) и [GitHub Projects](https://github.com/orgs/greenvisionfarm/projects) для отслеживания прогресса.

---

## Вопросы?

Создайте [Issue](https://github.com/greenvisionfarm/precision-ag-platform/issues/new) — мы рады помочь!

Спасибо за вклад! 🌱
