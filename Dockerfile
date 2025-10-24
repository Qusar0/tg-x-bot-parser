FROM python:3.11-slim

# 1️⃣ Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg unzip curl git xvfb fonts-liberation jq \
    libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libdrm2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# 2️⃣ Установка Python зависимостей
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3️⃣ Установка Playwright и Chromium
RUN pip install playwright==1.55.0 && \
    playwright install --with-deps chromium

# 4️⃣ Копирование кода приложения
COPY . .

# 5️⃣ Создание директорий и настройка окружения
RUN mkdir -p logs downloads
ENV DISPLAY=:99

CMD ["python", "-m", "app"]
