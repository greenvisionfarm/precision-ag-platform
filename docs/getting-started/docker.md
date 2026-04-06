# Настройка Docker

Field Mapper использует Docker Compose для развёртывания полного стека приложений.

## 📦 Компоненты

| Сервис | Описание | Порт |
|--------|----------|------|
| **app** | Tornado API сервер | 8888 |
| **worker** | Huey worker для фоновых задач | — |
| **redis** | Redis для очереди задач | 6379 |
| **nginx** | Reverse proxy | 80/443 |

## 🚀 Запуск

### 1. Сборка и запуск

```bash
docker-compose up -d --build
```

### 2. Проверка статуса

```bash
docker-compose ps
```

**Ожидаемый результат:**
```
NAME                STATUS              PORTS
field_mapper_app    Up 10 seconds       0.0.0.0:8888->8888/tcp
field_mapper_worker Up 10 seconds       
field_mapper_redis  Up 10 seconds       6379/tcp
field_mapper_nginx  Up 10 seconds       0.0.0.0:80->80/tcp
```

### 3. Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только app
docker-compose logs -f app

# Только worker
docker-compose logs -f worker
```

### 4. Остановка

```bash
docker-compose down
```

### 5. Полная очистка (с удалением данных)

```bash
docker-compose down -v
```

---

## 🔧 Управление

### Перезапуск сервиса

```bash
docker-compose restart app
```

### Выполнение команд в контейнере

```bash
# Python консоль
docker-compose exec app python

# Запуск тестов
docker-compose exec -e FIELD_MAPPER_ENV=test app pytest tests/

# npm команды
docker-compose exec app npm test
```

### Обновление

```bash
# Pull изменений из git
git pull

# Пересборка и перезапуск
docker-compose up -d --build
```

---

## 🧪 Тестирование в Docker

### Backend тесты

```bash
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest tests/ -v
```

### Frontend тесты

```bash
docker-compose run --rm app npm test
```

### Все тесты сразу

```bash
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest tests/ && \
docker-compose run --rm app npm test
```

---

## 📁 Тома (Volumes)

Данные сохраняются в Docker volumes:

| Volume | Описание |
|--------|----------|
| `app_data` | Исходный код приложения |
| `redis_data` | Данные Redis (очереди задач) |
| `uploads` | Загруженные файлы (Shapefile, GeoTIFF) |
| `database` | SQLite база данных |

### Просмотр volumes

```bash
docker volume ls | grep field_mapper
```

### Очистка volume

```bash
docker volume rm field_mapper_database
```

---

## 🛠️ Отладка

### Вход в контейнер app

```bash
docker-compose exec app bash
```

### Проверка переменных окружения

```bash
docker-compose exec app env
```

### Проверка подключения к Redis

```bash
docker-compose exec app redis-cli -h redis ping
```

---

## 📊 Метрики

| Параметр | Значение |
|----------|----------|
| **Размер образа app** | ~1.5 GB (с GIS библиотеками) |
| **Время сборки** | ~6 мин (с кэшем ~2 мин) |
| **Потребление RAM** | ~500 MB (app + worker) |
| **Redis RAM** | ~50 MB |

---

## 📚 Следующие шаги

- [Конфигурация](configuration.md) — переменные окружения
- [Управление полями](../user-guide/fields.md) — руководство пользователя
