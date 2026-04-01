# Аутентификация и мульти-тенантность

> Руководство по системе аутентификации и управления компаниями

**Версия:** v2026.3  
**Дата:** 1 апреля 2026 г.

---

## 📋 Оглавление

1. [Обзор](#обзор)
2. [Быстрый старт](#быстрый-старт)
3. [Миграция БД](#миграция-бд)
4. [Система ролей](#система-ролей)
5. [API аутентификации](#api-аутентификации)
6. [Локализация](#локализация)
7. [Изоляция данных](#изоляция-данных)

---

## Обзор

Field Mapper v2026.3 представляет систему мульти-тенантности, где каждая компания (фермерское хозяйство) имеет изолированные данные и пользователей.

### Ключевые возможности

- ✅ **Мульти-тенантность**: Полная изоляция данных между компаниями
- ✅ **Ролевая модель**: 5 уровней доступа (Owner, Admin, Agronomist, Operator, Viewer)
- ✅ **Аутентификация**: Secure session tokens на основе HMAC-SHA256
- ✅ **Локализация**: Поддержка RU/EN/SK языков
- ✅ **Профили**: Управление профилем и настройками компании

---

## Быстрый старт

### 1. Миграция базы данных

```bash
python src/db_migrate.py
```

### 2. Создание тестовых данных

```bash
python seed_auth.py
```

Будут созданы:
- 3 компании (RU, SK, EN)
- 6 пользователей с разными ролями
- Тестовые владельцы

### 3. Запуск сервера

```bash
python app.py
```

### 4. Вход в систему

Используйте одну из учётных записей:

| Компания | Email | Пароль | Роль | Язык |
|----------|-------|--------|------|------|
| АгроТех | admin@agrotech.ru | admin123 | Owner | RU |
| АгроТех | agronom@agrotech.ru | user123 | Agronomist | RU |
| Green Fields | admin@greenfields.sk | admin123 | Owner | SK |
| Green Fields | operator@greenfields.sk | user123 | Operator | SK |
| Demo Farm | admin@demofarm.com | admin123 | Owner | EN |

---

## Миграция БД

### Структура таблиц

#### Company
```sql
CREATE TABLE company (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at DATETIME,
    is_active INTEGER DEFAULT 1,
    settings_json TEXT
);
```

#### User
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    password_salt VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    company_id INTEGER NOT NULL,
    role VARCHAR(50) DEFAULT 'operator',
    is_active INTEGER DEFAULT 1,
    is_verified INTEGER DEFAULT 0,
    created_at DATETIME,
    last_login DATETIME,
    language VARCHAR(10) DEFAULT 'ru',
    settings_json TEXT,
    FOREIGN KEY (company_id) REFERENCES company(id)
);
```

#### Field (обновлена)
```sql
ALTER TABLE field ADD COLUMN company_id INTEGER;
ALTER TABLE field ADD COLUMN updated_at DATETIME;
```

---

## Система ролей

### Иерархия ролей

| Роль | Уровень | Описание |
|------|---------|----------|
| **Owner** | 5 | Владелец компании (полный доступ) |
| **Admin** | 4 | Администратор (управление пользователями) |
| **Agronomist** | 3 | Агроном (просмотр и анализ данных) |
| **Operator** | 2 | Оператор (загрузка данных, экспорт) |
| **Viewer** | 1 | Наблюдатель (только просмотр) |

### Права доступа

| Действие | Owner | Admin | Agronomist | Operator | Viewer |
|----------|-------|-------|------------|----------|--------|
| Просмотр полей | ✅ | ✅ | ✅ | ✅ | ✅ |
| Добавление полей | ✅ | ✅ | ✅ | ✅ | ❌ |
| Редактирование | ✅ | ✅ | ✅ | ✅ | ❌ |
| Удаление полей | ✅ | ✅ | ❌ | ❌ | ❌ |
| Экспорт карт | ✅ | ✅ | ✅ | ✅ | ❌ |
| Загрузка сканов | ✅ | ✅ | ✅ | ✅ | ❌ |
| Управление пользователями | ✅ | ✅ | ❌ | ❌ | ❌ |
| Настройки компании | ✅ | ✅ | ❌ | ❌ | ❌ |
| Удаление компании | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## API аутентификации

### POST /api/auth/login

Вход пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "remember": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Успешный вход!",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "Иван",
    "last_name": "Петров",
    "role": "owner",
    "language": "ru",
    "company": {
      "id": 1,
      "name": "АгроТех",
      "slug": "agro-tech"
    }
  }
}
```

### POST /api/auth/register

Регистрация нового пользователя и компании.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "company_name": "Моя Компания",
  "first_name": "Иван",
  "last_name": "Петров",
  "language": "ru"
}
```

### POST /api/auth/logout

Выход пользователя (уничтожение сессии).

### GET /api/auth/profile

Получение данных профиля.

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "Иван",
    "last_name": "Петров",
    "role": "owner",
    "language": "ru",
    "is_verified": false,
    "created_at": "2026-04-01T10:00:00",
    "last_login": "2026-04-01T12:00:00",
    "company": {
      "id": 1,
      "name": "АгроТех",
      "slug": "agro-tech",
      "settings": {}
    }
  }
}
```

### PUT /api/auth/profile

Обновление профиля пользователя.

**Request:**
```json
{
  "first_name": "Иван",
  "last_name": "Иванов",
  "language": "en",
  "password": "old_password",
  "new_password": "new_password123"
}
```

### GET /api/auth/company

Получение данных компании.

**Response:**
```json
{
  "company": {
    "id": 1,
    "name": "АгроТех",
    "slug": "agro-tech",
    "created_at": "2026-04-01T10:00:00",
    "settings": {},
    "users": [
      {
        "id": 1,
        "email": "admin@agrotech.ru",
        "first_name": "Иван",
        "last_name": "Петров",
        "role": "owner",
        "language": "ru"
      }
    ]
  }
}
```

---

## Локализация

### Поддерживаемые языки

| Код | Язык | Native |
|-----|------|--------|
| ru | Русский | Русский |
| en | English | English |
| sk | Slovak | Slovenčina |

### Использование в JavaScript

```javascript
// Автоматическое применение языка пользователя
AuthModule.getCurrentLanguage(); // 'ru'

// Перевод ключей
const message = AuthModule.translate('auth.login', 'en'); // 'Login'
```

### Использование в Python

```python
from src.utils.i18n import t

# Перевод на указанный язык
message = t('auth.login', 'en')  # 'Login'
message_ru = t('auth.login')     # 'Вход' (язык по умолчанию)
```

### Ключи локализации

Основные ключи:

| Ключ | RU | EN | SK |
|------|-----|----|----|
| nav.home | Главная | Home | Domov |
| nav.fields | Поля | Fields | Polia |
| auth.login | Вход | Login | Prihlásenie |
| auth.register | Регистрация | Register | Registrácia |
| profile.title | Профиль | Profile | Profil |
| settings.language | Язык | Language | Jazyk |

---

## Изоляция данных

### Принцип работы

Каждый запрос фильтруется по компании текущего пользователя:

```python
# В handlers
def get(self):
    user = self.get_current_user()
    
    # Фильтрация полей по компании
    fields = Field.select().where(
        Field.company == user.company
    )
```

### Middleware авторизации

```python
from src.middleware import require_auth, AuthenticatedRequestHandler

class MyHandler(AuthenticatedRequestHandler):
    @require_auth
    def get(self, field_id):
        # Доступно только авторизованным
        user = self.current_user
        company_id = self.current_company_id
```

### Декораторы прав доступа

```python
from src.middleware import require_role
from src.models.auth import UserRole

class AdminHandler(AuthenticatedRequestHandler):
    @require_role(UserRole.ADMIN)
    def post(self):
        # Доступно только Admin и выше
        pass
```

---

## Безопасность

### Хранение паролей

- SHA-256 хэширование с уникальной солью
- Соль: 32 байта (64 hex символа)
- Хэш: `SHA256(password + salt)`

### Session tokens

- HMAC-SHA256 подпись
- Время жизни: 24 часа (1 день) или 720 часов (30 дней) с "remember me"
- Хранение: in-memory + cookie

### Cookie настройки

```python
self.set_secure_cookie(
    'session_token',
    token,
    expires_days=1,
    httponly=True,
    samesite='Lax'
)
```

---

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SESSION_SECRET` | Секретный ключ для подписи токенов | Генерируется |
| `FIELD_MAPPER_DB` | Путь к базе данных | fields.db |
| `FIELD_MAPPER_ENV` | Окружение (test/production) | production |

---

## Тесты

### Запуск тестов авторизации

```bash
FIELD_MAPPER_ENV=test pytest tests/test_auth.py -v
```

### Покрытие тестами

- ✅ Модель User (хэширование, проверка пароля, роли)
- ✅ SessionManager (создание, проверка, уничтожение токенов)
- ✅ Tenant isolation (фильтрация по компаниям)
- ✅ Auth API (login, register, logout)

---

## Миграция с v2026.2

### Обратная совместимость

Старые данные (поля, владельцы) автоматически привязываются к компании "Default Company".

### Шаги миграции

1. Сделать бэкап БД
2. Выполнить миграцию: `python src/db_migrate.py`
3. Создать пользователей: `python seed_auth.py`
4. Протестировать вход

---

*Документ обновляется с каждой версией. Последнее изменение: 1 апреля 2026 г.*
