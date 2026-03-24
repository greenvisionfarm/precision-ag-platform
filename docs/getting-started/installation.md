# Установка Field Mapper

## Требования

- **Python:** 3.12+
- **Node.js:** 20+
- **Docker:** 20+ (опционально, рекомендуется)
- **Docker Compose:** 2.0+ (опционально)

---

## 🐳 Быстрый старт через Docker (Рекомендуется)

Самый простой способ запустить весь стек (API, Worker, Redis, Nginx):

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-org/field-mapper.git
cd field-mapper
```

### 2. Запуск через Docker Compose

```bash
docker-compose up -d --build
```

### 3. Проверка работы

Откройте в браузере:
- **Через Nginx:** [http://localhost](http://localhost) (порт 80)
- **Напрямую к API:** [http://localhost:8888](http://localhost:8888)

### 4. Остановка

```bash
docker-compose down
```

> **Оптимизация:** Dockerfile оптимизирован для быстрой сборки (кэширование npm, многоэтапная сборка). Время сборки с кэшем: ~1.5-2 минуты.

---

## 🛠️ Локальная установка (без Docker)

### 1. Установка системных зависимостей

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-gdal \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    nodejs \
    npm
```

#### macOS

```bash
brew install python@3.12 gdal proj geos nodejs
```

### 2. Установка Python зависимостей

```bash
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Установка Node.js зависимостей

```bash
npm install
```

### 4. Запуск приложения

```bash
python app.py
```

### 5. Открыть в браузере

[http://localhost:8888](http://localhost:8888)

---

## 🔧 Установка Redis (для фоновых задач)

Redis требуется для работы очереди задач Huey (NDVI анализ):

### Ubuntu/Debian

```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### macOS

```bash
brew install redis
brew services start redis
```

### Docker

```bash
docker run -d -p 6379:6379 redis:latest
```

---

## ✅ Проверка установки

### Backend тесты

```bash
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/ -v
```

**Ожидаемый результат:** 14 passed, 1 skipped

### Frontend тесты

```bash
npm test
```

---

## 🆘 Решение проблем

### Ошибка: `gdal-config not found`

```bash
# Ubuntu/Debian
sudo apt-get install libgdal-dev

# macOS
brew install gdal
```

### Ошибка: `ModuleNotFoundError: No module named 'tornado'`

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Ошибка: `Redis connection refused`

```bash
# Проверьте, что Redis запущен
redis-cli ping  # Должен ответить PONG

# Или отключите Huey в app.py для локальной разработки
```

---

## 📚 Следующие шаги

- [Настройка Docker](docker.md) — подробная инструкция по Docker Compose
- [Конфигурация](configuration.md) — переменные окружения и настройки
- [Руководство пользователя](../user-guide/fields.md) — начало работы
