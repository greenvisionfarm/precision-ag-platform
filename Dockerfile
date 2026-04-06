# Этап 1: Сборка зависимостей (Python + JS)
FROM python:3.12-slim-bookworm AS builder

# Установка системных зависимостей для сборки GIS-библиотек и Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    g++ \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# 1. Сборка Python окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем requirements.txt раньше для кэширования слоя
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2. Сборка JS окружения (только production зависимости)
WORKDIR /build_js
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --only=production --ignore-scripts || \
    npm install --only=production --ignore-scripts

# Этап 2: Финальный образ (Runtime)
FROM python:3.12-slim-bookworm AS runtime

# Установка runtime-библиотек GIS
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    libproj25 \
    libgeos-c1v5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем Python venv
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем JS зависимости
COPY --from=builder /build_js/node_modules ./node_modules

# Установка рабочей директории
WORKDIR /app

# Копируем зависимости и код отдельно для кэширования
COPY package*.json ./
COPY requirements.txt ./
COPY . .

# Создаем папки для БД и загрузок
RUN mkdir -p /app/data /app/uploads

EXPOSE 8888

CMD ["python", "app.py"]
