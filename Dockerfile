# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt (если есть) или устанавливаем зависимости напрямую
COPY . .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir \
    django==5.2 \
    mysqlclient \
    pillow \
    python-decouple

# Применяем миграции
RUN python manage.py makemigrations
RUN python manage.py migrate

# Активируем существующих пользователей для обратной совместимости
RUN python manage.py activate_existing_users

# Создаем директорию для статических файлов
RUN mkdir -p /app/static

# Открываем порт
EXPOSE 8000

# Команда для запуска
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
