FROM python:3.12-slim

# Общие настройки
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Установка uv
RUN pip install uv

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей через uv
RUN uv sync --frozen

# Добавляем виртуальное окружение в PATH.
ENV PATH="/app/.venv/bin:$PATH"

# Копирование остальных файлов приложения в папку WORKDIR
COPY . .

