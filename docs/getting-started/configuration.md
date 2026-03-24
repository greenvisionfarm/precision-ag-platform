# Конфигурация

## Переменные окружения

### Основные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `FIELD_MAPPER_ENV` | `production` | Окружение (`production`, `test`, `development`) |
| `PORT` | `8888` | Порт Tornado сервера |
| `DATABASE_URL` | `sqlite:///fields.db` | Подключение к базе данных |
| `REDIS_HOST` | `localhost` | Хост Redis для Huey |
| `REDIS_PORT` | `6379` | Порт Redis |

### Docker Compose

В `docker-compose.yml` уже настроены все переменные:

```yaml
services:
  app:
    environment:
      - FIELD_MAPPER_ENV=production
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

---

## Настройка базы данных

### SQLite (по умолчанию)

```bash
# База данных создаётся автоматически при первом запуске
# Расположение: ./fields.db
```

### PostgreSQL (для production)

1. Установите адаптер:
```bash
pip install psycopg2-binary
```

2. Измените `DATABASE_URL`:
```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/field_mapper
```

3. Инициализируйте БД:
```bash
python db.py  # Создаст таблицы
```

---

## Настройка Redis

### Локальный Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Проверка
redis-cli ping  # PONG
```

### Docker Redis

```bash
docker run -d -p 6379:6379 --name field-mapper-redis redis:latest
```

### Настройка в приложении

```python
# app.py
from huey import RedisHuey

huey = RedisHuey(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379))
)
```

---

## Настройка GDAL

### Проверка установки

```bash
gdal-config --version
python -c "from osgeo import gdal; print(gdal.__version__)"
```

### Переменные окружения GDAL

```bash
# Linux
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal

# При установке Python пакета
pip install GDAL==$(gdal-config --version)
```

---

## Конфигурация приложения

### app.py

Основные настройки в `make_app()`:

```python
def make_app():
    return tornado.web.Application(
        handlers=[...],
        template_path="static",
        static_path="static",
        debug=os.getenv('FIELD_MAPPER_ENV') == 'development'
    )
```

### static/js/modules/api.js

Настройка API endpoints:

```javascript
const API = {
  baseURL: '',  // Пусто для same-origin
  // или
  baseURL: 'http://localhost:8888'  // Для CORS
};
```

---

## Безопасность

### Production чеклист

- [ ] Установите `FIELD_MAPPER_ENV=production`
- [ ] Используйте Nginx как reverse proxy
- [ ] Настройте HTTPS (Let's Encrypt)
- [ ] Ограничьте доступ к Redis (firewall)
- [ ] Используйте environment variables для секретов
- [ ] Включите rate limiting для API

### Nginx конфигурация

```nginx
server {
    listen 80;
    server_name field-mapper.example.com;

    location / {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📚 Следующие шаги

- [Управление полями](../user-guide/fields.md) — начало работы
- [Архитектура](../developer-guide/architecture.md) — для разработчиков
