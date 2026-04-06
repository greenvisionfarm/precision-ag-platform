# Вклад в проект (Contributing)

Приветствуем ваш интерес к проекту Field Mapper! Этот документ описывает процесс внесения изменений.

---

## 🚀 Быстрый старт для разработчиков

### 1. Форк и клонирование

```bash
# Форкните репозиторий на GitHub
# Затем клонируйте:
git clone https://github.com/YOUR-USERNAME/field-mapper.git
cd field-mapper
```

### 2. Настройка окружения

```bash
# Python окружение
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Node.js зависимости
npm install

# Docker (опционально)
docker-compose up -d
```

### 3. Запуск тестов

```bash
# Backend
FIELD_MAPPER_ENV=test pytest tests/

# Frontend
npm test
```

---

## 📋 Процесс внесения изменений

### 1. Выбор задачи

Посмотрите [TODO.md](../TODO.md) со списком задач:

- 🔥 **P0** — Критические (высокий приоритет)
- 🟠 **P1** — Важные
- 🟡 **P2** — Долгосрочные

### 2. Создание ветки

```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/issue-123
```

**Названия веток:**
- `feature/...` — новая функциональность
- `fix/...` — исправление бага
- `docs/...` — документация
- `refactor/...` — рефакторинг

### 3. Внесение изменений

Следуйте стандартам кода:

#### Python

```python
# Type hints обязательны
def calculate_area(geometry: dict) -> float:
    """Расчёт площади полигона.
    
    Args:
        geometry: GeoJSON geometry.
    
    Returns:
        Площадь в гектарах.
    """
    ...
```

#### JavaScript

```javascript
// ES6 модули
import { showMessage } from './utils.js';

/**
 * Инициализация карты.
 * @param {string} elementId - ID элемента.
 */
export function initMap(elementId) {
  ...
}
```

### 4. Коммиты

**Формат сообщений:**

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Типы:**
- `feat`: Новая функциональность
- `fix`: Исправление бага
- `docs`: Документация
- `style`: Форматирование
- `refactor`: Рефакторинг
- `test`: Тесты
- `chore`: Инфраструктура

**Примеры:**
```bash
git commit -m "feat(kmz): добавить кэширование экспорта"
git commit -m "fix(api): исправлена ошибка 500 при удалении поля"
git commit -m "docs(readme): обновлена инструкция по установке"
```

### 5. Push и Pull Request

```bash
git push origin feature/your-feature-name
```

Создайте Pull Request на GitHub:

1. Перейдите в ваш форк
2. Выберите ветку
3. Нажмите **Compare & pull request**
4. Заполните описание:
   - Что изменено
   - Почему это нужно
   - Скриншоты (для UI)
5. Назначьте ревьюеров

---

## 📝 Стандарты кода

### Python

- **Style:** PEP 8
- **Type hints:** Обязательны для всех функций
- **Docstrings:** Google style
- **Импорты:** Сортировка (stdlib, third-party, local)

**Инструменты:**
```bash
# Линтинг
flake8 src/

# Форматирование
black src/

# Типы
mypy src/
```

### JavaScript

- **Style:** Airbnb Base (без React)
- **Модули:** ES6
- **jQuery:** Допустим (legacy код)
- **Импорты:** Сначала node_modules, потом локальные

**Инструменты:**
```bash
# Линтинг
npm run lint

# Форматирование
npx prettier --write "static/js/**/*.js"
```

---

## 🧪 Требования к тестам

### Backend

- Покрытие для новой логики: **>80%**
- Обязательные сценарии:
  - Успешный путь
  - Ошибки валидации
  - Пограничные случаи

### Frontend

- Тесты для критической логики
- Проверка маршрутизации
- UI взаимодействия

---

## 📚 Документация

### Обновление документации

Если вы изменяете функциональность:

1. Обновите [user-guide](user-guide/)
2. Добавьте запись в [changelog](changelog/)
3. Обновите API Reference (если изменился API)

### Стиль документации

- Заголовки: Sentence case
- Код: Блоки с указанием языка
- Скриншоты: В папке `docs/assets/`

---

## 🔍 Code Review

### Чеклист ревьюера

- [ ] Код следует стандартам
- [ ] Тесты проходят
- [ ] Покрытие достаточное
- [ ] Документация обновлена
- [ ] Нет уязвимостей безопасности

### Время ответа

- PR с приоритетом **P0**: 24 часа
- PR с приоритетом **P1/P2**: 3-5 дней

---

## 🎯 Области вклада

### Backend

- Улучшение GIS вычислений
- Оптимизация NDVI анализа
- Новые форматы экспорта (ISOBUS, Shapefile)

### Frontend

- Улучшение UX карты
- Мобильная адаптация
- PWA функциональность

### Документация

- Переводы на другие языки
- Примеры использования
- Видео-туториалы

### Тесты

- E2E тесты (Playwright)
- Интеграционные тесты
- Увеличение покрытия

---

## 📞 Контакты

- **GitHub Issues:** Для багов и фич
- **Discussions:** Для вопросов
- **Email:** your-email@example.com

---

## 🙏 Благодарности

Спасибо всем контрибьюторам! 🎉

Посмотрите список участников на странице [Contributors](https://github.com/your-org/field-mapper/graphs/contributors).

---

*Последнее обновление: 24 марта 2026 г.*
