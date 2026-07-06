# 🤖 Mister AI - المعلم الذكي v2.1

> مساعد تعليمي افتراضي بالذكاء الاصطناعي لطلاب الثانوية في اليمن
> مبني على **FastAPI + Telegram Bot + LangChain v1.3+ + Gemini 3.1 Flash Lite + RAG**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![LangChain 1.3+](https://img.shields.io/badge/LangChain-1.3+-green.svg)](https://python.langchain.com/)
[![Gemini 3.1 Flash Lite](https://img.shields.io/badge/Gemini-3.1--Flash--Lite-4285F4.svg)](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ ما الجديد في v2.1؟

| الميزة | قبل | بعد |
|--------|------|------|
| **LLM Provider** | OpenAI فقط | **Google Gemini + OpenAI** |
| **النموذج الافتراضي** | gpt-4o-mini | **gemini-3.1-flash-lite** |
| **Embeddings** | OpenAI فقط | **Gemini + OpenAI** |
| **Multi-Provider** | لا | **نعم (LLM_PROVIDER)** |
| **LangChain** | 1.0 | **1.3+** |
| **التكلفة** | مرتفعة | **منخفضة (Gemini Flash Lite)** |
| **السرعة** | جيدة | **عالية جداً (Flash Lite)** |

---

## 🎯 لماذا Gemini 3.1 Flash Lite؟

✅ **أسرع نموذج من Google** - مُحسّن للأداء العالي والكفاءة
✅ **أقل تكلفة** - مناسب للتطبيقات عالية التردد
✅ **دعم متعدد الوسائط** - نص، صورة، فيديو، صوت، PDF
✅ **أداء متقدم** - ينافس النماذج الأكبر بأداء قريب
✅ **مُحسّن للـ Agents** - مثالي للتطبيقات التعليمية التفاعلية
✅ **مجاناً للاستخدام الشخصي** - عبر Google AI Studio

---

## 🏗️ البنية المعمارية

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│  Telegram   │────▶│   FastAPI   │────▶│  LangChain v1.3 │
│    Bot      │     │     App     │     │   (LCEL Chains) │
└─────────────┘     └──────┬──────┘     └────────┬────────┘
                           │                     │
                  ┌────────┴────────┐     ┌──────┴──────┐
                  │                 │     │             │
            ┌─────▼─────┐    ┌──────▼──────┐  ┌───────▼────────┐
            │ PostgreSQL │    │   Qdrant    │  │ Google Gemini │
            │ + SQLAlchemy│   │ VectorStore │  │ 3.1 Flash Lite│
            │  2.0 async  │    │ (langchain) │  │  (langchain)  │
            └───────────┘    └─────────────┘  └────────────────┘
                  │
            ┌─────▼─────┐
            │   Redis   │
            │  (Cache)  │
            └───────────┘
```

---

## 📋 المتطلبات

### 1. مفاتيح API المطلوبة
- **Google Gemini API Key** (مجاناً من [Google AI Studio](https://aistudio.google.com/app/apikey))
- **Telegram Bot Token** (من [@BotFather](https://t.me/BotFather))

### 2. المتطلبات التقنية
- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **Python 3.12+** (للتطوير المحلي)

---

## 🚀 البدء السريع

### 1. الإعداد
```bash
git clone https://github.com/landspices25Ye/mister_ai.git
cd mister_ai
cp .env.example .env
nano .env  # أضف GOOGLE_API_KEY و TELEGRAM_BOT_TOKEN
```

### 2. تشغيل البنية التحتية
```bash
# تشغيل PostgreSQL + Redis + Qdrant فقط
docker-compose up -d postgres redis qdrant

# انتظر حتى تكون الخدمات جاهزة
docker-compose ps
```

### 3. فهرسة المنهج في Qdrant
```bash
# تشغيل السكربت داخل الحاوية
docker-compose run --rm app python -m scripts.ingest_curriculum
```

### 4. تشغيل التطبيق
```bash
# تشغيل الحاوية الرئيسية
docker-compose up -d app

# عرض السجلات
docker-compose logs -f app
```

### 5. التحقق
- افتح `http://localhost:8000` للتحقق من FastAPI
- افتح `http://localhost:8000/health` لفحص الحالة
- افتح `http://localhost:8080` لـ Adminer (إدارة قاعدة البيانات)
- تحدث مع البوت على Telegram

---

## 🔧 متغيرات البيئة

راجع ملف `.env.example` للحصول على القائمة الكاملة.

**المتغيرات الأساسية:**
```env
# اختر المزود: "gemini" أو "openai"
LLM_PROVIDER=gemini

# Google Gemini
GOOGLE_API_KEY=***
GEMINI_MODEL=gemini-3.1-flash-lite

# Telegram
TELEGRAM_BOT_TOKEN=***
```

---

## 📊 الخدمات

| الخدمة | المنفذ | الوصف |
|--------|--------|-------|
| `app` | 8000 | التطبيق الرئيسي (FastAPI + Telegram) |
| `postgres` | 5432 | قاعدة البيانات |
| `qdrant` | 6333 | Vector DB |
| `redis` | 6379 | Cache |
| `adminer` | 8080 | إدارة قاعدة البيانات |

---

## 🛠️ استكشاف الأخطاء

### خطأ في استيراد langchain-google-genai
```bash
# تأكد من تثبيت الحزمة
pip install langchain-google-genai>=4.2.0

# أو داخل Docker
docker-compose build --no-cache app
```

### خطأ في الاتصال بـ Gemini
```bash
# تأكد من صحة GOOGLE_API_KEY
# احصل على مفتاح جديد من: https://aistudio.google.com/app/apikey
```

### خطأ في Qdrant
```bash
docker-compose ps qdrant
docker-compose logs qdrant
```

---

## 🔄 التبديل بين Gemini و OpenAI

لتغيير المزود، عدل ملف `.env`:

```env
# للاستخدام مع Google Gemini
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key

# للاستخدام مع OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
```

ثم أعد تشغيل الحاوية:
```bash
docker-compose restart app
```

---

## 📈 مقارنة بين Gemini و OpenAI

| الميزة | Gemini 3.1 Flash Lite | OpenAI gpt-4o-mini |
|--------|-----------------------|--------------------|
| **السعر** | مجاناً للاستخدام الشخصي | مدفوع |
| **السرعة** | عالية جداً | جيدة |
| **جودة الردود** | ممتازة | ممتازة |
| **دعم الوسائط** | نص + صورة + فيديو + صوت + PDF | نص فقط |
| **السياق** | 1 مليون توكن | 128 ألف توكن |
| **الاستجابة** | أقل من 300 مللي ثانية | 500-1000 مللي ثانية |
| **التوفر** | متاح عالمياً | متاح عالمياً |
| **التكلفة** | منخفضة جداً | منخفضة |

---

## 📚 الوثائق الإضافية

- 📖 [دليل المعلم (System Prompt)](prompts/system_prompt.md)
- 📖 [مخطط قاعدة البيانات](db/schema.sql)
- 📖 [هيكل المنهج](curriculum/math-3sec/README.md)
- 📖 [Google Gemini API Docs](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)
- 📖 [LangChain Google GenAI](https://python.langchain.com/docs/integrations/chat/google_generative_ai)

---

## 🤝 المساهمة

المشروع تطوعي ومفتوح للمساهمة.

---

## 📜 الرخصة

MIT License

---

## 👤 المؤسس

**الأستاذ أحمد المغز** - مبادرة تطوعية لخدمة الطلاب اليمنيين

---

## 🙏 شكر وتقدير

- Google DeepMind (لنموذج Gemini 3.1 Flash Lite)
- Google AI Studio (للـ API المجاني)
- وزارة التربية والتعليم اليمنية (للمصدر الرسمي للمناهج)
- مجتمع LangChain و Python
