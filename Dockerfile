FROM python:3.11-slim

# 1️⃣ Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg unzip curl git xvfb fonts-liberation jq \
    libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libdrm2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# 2️⃣ Установка Google Chrome
RUN wget -q -O /usr/share/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 3️⃣ Chrome уже установлен, ChromeDriver не нужен для Playwright

# 4️⃣ Python-зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5️⃣ Playwright и Chromium
RUN pip install playwright==1.55.0 && playwright install --with-deps chromium

# 6️⃣ Копируем проект
COPY . .

RUN mkdir -p logs downloads
ENV DISPLAY=:99

CMD ["python", "-m", "app"]
