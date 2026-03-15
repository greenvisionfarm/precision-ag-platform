# Этап 1: Сборка зависимостей (Python + JS)
FROM python:3.12-slim-bookworm AS builder

# Установка системных зависимостей для сборки GIS-библиотек и загрузки Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    g++ \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Установка Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# 1. Сборка Python окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2. Сборка JS окружения
WORKDIR /build_js
COPY package*.json ./
RUN npm install

# Этап 2: Финальный образ (Runtime)
FROM python:3.12-slim-bookworm

# Установка runtime-библиотек GIS и Node.js для запуска тестов
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    libproj25 \
    libgeos-c1v5 \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Копируем Python venv
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка рабочей директории
WORKDIR /app

# Копируем JS зависимости
COPY --from=builder /build_js/node_modules ./node_modules
COPY package*.json ./

# Копируем исходный код
COPY . .

# Создаем папку для базы данных и загрузок
RUN mkdir -p /app/data /app/uploads

EXPOSE 8888

CMD ["python", "app.py"]
