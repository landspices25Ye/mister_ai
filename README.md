# 🤖 Mister AI - المعلم الذكي

> مساعد تعليمي افتراضي بالذكاء الاصطناعي لطلاب الثانوية في اليمن
> مبني على **FastAPI + Telegram Bot + RAG + OpenAI**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 نظرة عامة

**مستر AI** هو بوت تعليمي ذكي يعمل على **Telegram** (وقريباً WhatsApp)، يقدم:
- 🎓 دروساً في الرياضيات (الصف الثالث الثانوي - علمي)
- 🤖 شروحات بأسلوب سقراطي (يوجّه الطالب للتفكير بدل الإجابة المباشرة)
- 📝 تدريبات واختبارات تفاعلية
- 📊 تتبّع تقدّم الطالب
- 🔍 بحث ذكي في المنهج (RAG)

---

## 🏗️ البنية المعمارية

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│   FastAPI   │────▶│    OpenAI   │
│    Bot      │     │     App     │     │     LLM     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
            ┌─────▼─────┐    ┌──────▼──────┐
            │ PostgreSQL │    │   Qdrant    │
            │ (Metadata) │    │ (Vectors)   │
            └───────────┘    └─────────────┘
                  │
            ┌─────▼─────┐
            │   Redis   │
            │  (Cache)  │
            └───────────┘
```

---

## 📂 هيكل المشروع

```
mister_ai/
├── bot/
│   ├── main.py              # نقطة الدخول الرئيسية
│   └── core/
│       ├── llm_client.py    # عميل LLM (OpenAI)
│       ├── rag.py           # Pipeline لاسترجاع الدروس
│       └── student_manager.py # إدارة بيانات الطلاب
├── curriculum/
│   └── math-3sec/
│       ├── ch01_derivatives/    # الفصل الأول (مكتمل)
│       ├── ch02_applications/   # هيكل
│       ├── ch03_integration/    # هيكل
│       └── shared/questions_bank/
├── prompts/
│   └── system_prompt.md     # دليل المعلم (System Prompt)
├── db/
│   └── schema.sql           # مخطط قاعدة البيانات
├── data/                    # ملفات مؤقتة
├── scripts/                 # سكربتات مساعدة
├── simulations/             # محاكاة المحادثات
├── .env.example             # قالب متغيرات البيئة
├── docker-compose.yml       # إعداد الحاويات
├── Dockerfile               # بناء الصورة
└── requirements.txt         # المكتبات المطلوبة
```

---

## 🚀 البدء السريع

### 1. المتطلبات
- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **مفتاح OpenAI API** ([احصل عليه من هنا](https://platform.openai.com/api-keys))
- **توكن Telegram Bot** ([أنشئ بوت من @BotFather](https://t.me/BotFather))

### 2. الإعداد
```bash
# استنساخ المستودع
git clone https://github.com/landspices25Ye/mister_ai.git
cd mister_ai

# إنشاء ملف .env
cp .env.example .env
nano .env  # أضف المفاتيح الفعلية
```

### 3. التشغيل
```bash
# بناء وتشغيل الحاويات
docker-compose up -d --build

# عرض السجلات
docker-compose logs -f app

# فحص حالة الحاويات
docker-compose ps
```

### 4. التحقق
- افتح `http://localhost:8000` للتحقق من أن FastAPI يعمل
- افتح Telegram وتحدث مع البوت الخاص بك

---

## 🔧 متغيرات البيئة

| المتغير | الوصف | القيمة الافتراضية |
|---------|-------|-------------------|
| `TELEGRAM_BOT_TOKEN` | توكن بوت Telegram | _(مطلوب)_ |
| `OPENAI_API_KEY` | مفتاح OpenAI API | _(مطلوب)_ |
| `OPENAI_MODEL` | نموذج LLM المستخدم | `gpt-4o-mini` |
| `POSTGRES_USER` | اسم مستخدم PostgreSQL | `mister_ai_user` |
| `POSTGRES_PASSWORD` | كلمة مرور PostgreSQL | _(مطلوب)_ |
| `POSTGRES_DB` | اسم قاعدة البيانات | `mister_ai` |
| `QDRANT_HOST` | اسم مضيف Qdrant | `qdrant` |
| `REDIS_HOST` | اسم مضيف Redis | `redis` |
| `SYSTEM_PROMPT_PATH` | مسار ملف System Prompt | `/app/prompts/system_prompt.md` |

---

## 📊 الخدمات

| الخدمة | المنفذ | الوصف |
|--------|--------|-------|
| `app` | 8000 | التطبيق الرئيسي (FastAPI + Telegram) |
| `postgres` | 5432 | قاعدة البيانات الرئيسية |
| `qdrant` | 6333 | قاعدة البيانات المتجهية (RAG) |
| `redis` | 6379 | التخزين المؤقت |
| `adminer` | 8080 | واجهة إدارة قاعدة البيانات |

---

## 🛠️ استكشاف الأخطاء وإصلاحها

### الحاوية `app` تشتغل وتغلق فوراً
**السبب الشائع:** متغيرات البيئة غير معرّفة.

**الحل:**
1. تأكد من وجود ملف `.env` ومن صحة القيم
2. تحقق من السجلات: `docker-compose logs app`
3. تأكد من أن جميع المجلدات المطلوبة موجودة (مثل `prompts/`, `curriculum/`)

### خطأ في الاتصال بـ Qdrant
**الحل:** تأكد من أن خدمة `qdrant` تعمل:
```bash
docker-compose ps qdrant
```

### خطأ في الاتصال بـ PostgreSQL
**الحل:** تحقق من أن خدمة `postgres` بدأت بنجاح ومن أن بيانات الاعتماد صحيحة.

---

## 📚 الوثائق الإضافية

- 📖 [دليل المعلم (System Prompt)](prompts/system_prompt.md)
- 📖 [مخطط قاعدة البيانات](db/schema.sql)
- 📖 [هيكل المنهج](curriculum/math-3sec/README.md)

---

## 🤝 المساهمة

المشروع تطوعي ومفتوح للمساهمة. للمساهمة:
1. Fork المستودع
2. أنشئ فرعاً جديداً (`git checkout -b feature/amazing-feature`)
3. Commit التعديلات (`git commit -m 'Add amazing feature'`)
4. Push إلى الفرع (`git push origin feature/amazing-feature`)
5. افتح Pull Request

---

## 📜 الرخصة

MIT License - انظر ملف [LICENSE](LICENSE) للتفاصيل.

---

## 👤 المؤسس

**الأستاذ أحمد المغز** - مبادرة تطوعية لخدمة الطلاب اليمنيين

---

## 🙏 شكر وتقدير

- وزارة التربية والتعليم اليمنية (للمصدر الرسمي للمناهج)
- OpenAI (لتوفير نماذج LLM)
- Telegram (لتوفير منصة بوت مجانية)
- مجتمع FastAPI و Python
