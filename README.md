# Mister AI

مشروع ذكاء اصطناعي لتشغيل بوت Telegram تعليمي يدعم المنهج الدراسي ويعمل مع خدمات مثل PostgreSQL و Qdrant و Redis.

## المتطلبات

- Git
- Docker Desktop أو Docker Engine
- Docker Compose
- Python 3.10+ (اختياري للتطوير المحلي)
- مفتاح OpenAI API

## العمل من GitHub على الجهاز المحلي

### 1) استنساخ المشروع

```bash
git clone https://github.com/LandSpices25Ye/mister_ai.git
cd mister_ai
```

### 2) إعداد المتغيرات البيئية

```bash
cp .env.example .env
nano .env
```

أدخل القيم المناسبة مثل:
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `POSTGRES_USER` و `POSTGRES_PASSWORD`
- `JWT_SECRET` و `SESSION_SECRET`

### 3) تشغيل المشروع عبر Docker

```bash
docker compose up -d --build
```

إذا كان Docker Compose القديم يستخدم الأمر التالي:

```bash
docker-compose up -d --build
```

### 4) فهرسة المنهج

```bash
docker compose exec app python scripts/ingest_curriculum.py
```

### 5) اختبار البوت

أرسل رسالة إلى البوت على Telegram بعد أن يصبح التشغيل جاهزًا.

---

## التطوير المحلي

إذا أردت تشغيل المشروع مباشرة على الجهاز بدون Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

ثم شغّل التطبيق كما هو مناسب للملف الرئيسي في المشروع.

---

## إدارة GitHub

### إضافة Remote

إذا لم يكن هناك Remote مضاف بعد:

```bash
git remote add origin https://github.com/<your-username>/mister_ai.git
```

### رفع التغييرات

```bash
git add .
git commit -m "Describe your changes"
git push -u origin main
```

### سحب التحديثات

```bash
git pull origin main
```

---

## هيكل المشروع

- `bot/` — كود البوت الرئيسي وطبقات المنطق
- `bot/core/` — وحدات RAG و LLM وإدارة الطلاب
- `curriculum/` — المحتوى التعليمي والمنهج
- `db/` — سكربتات قاعدة البيانات
- `prompts/` — ملفات التوجيه الخاصة بالذكاء الاصطناعي
- `scripts/` — أدوات مثل فهرسة المنهج
- `docker-compose.yml` — إعدادات الخدمات
- `Dockerfile` — بناء الصورة الخاصة بالتطبيق

---

## ملاحظات مهمة

- لا تشارك ملف `.env` في GitHub.
- تأكد من أن Docker يعمل قبل تشغيل المشروع.
- إذا واجهت مشكلة في الحاويات، استخدم:

```bash
docker compose ps
docker compose logs -f
```
