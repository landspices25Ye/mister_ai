# Mister AI - Dockerfile (v2.0)
# Python 3.12 + LangChain v1.0+ + psycopg3

FROM python:3.12-slim

# متغيرات بيئة
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# تثبيت system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نسخ وتثبيت المتطلبات
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# نسخ الكود
COPY . .

# إنشاء مجلد للسجلات
RUN mkdir -p /app/logs

# المنفذ
EXPOSE 8000

# فحص الصحة
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# بدء التطبيق
CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
