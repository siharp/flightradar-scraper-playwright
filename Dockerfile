# ---------- Stage 1 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .

# install ke folder khusus (bukan global)
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# path
ENV PATH="/install/bin:$PATH"
ENV PYTHONPATH="/install/lib/python3.11/site-packages"

# install chromium only
RUN playwright install chromium

# ---------- Stage 2 ----------
FROM python:3.11-slim

WORKDIR /app

# install minimal OS deps
RUN apt-get update && apt-get install -y \
    libatk-bridge2.0-0 libatk1.0-0 libnss3 \
    libx11-6 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2 libxkbcommon0 \
    libxfixes3 libxext6 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# copy hanya dependency (bukan seluruh python)
COPY --from=builder /install /usr/local

# copy hanya browser
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# copy hanya folder penting
COPY . /app

ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]