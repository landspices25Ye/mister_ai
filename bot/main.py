# Mister AI - Telegram Bot MVP
# main.py

"""
بوت Telegram يستخدم FastAPI + LangChain v1.3+
- يستخدم ChatGoogleGenerativeAI (Gemini 3.1 Flash Lite) افتراضياً
- يدعم OpenAI كبديل
- يستخدم QdrantVectorStore من langchain-qdrant
- يستخدم SQLAlchemy 2.0 async + psycopg3
- أسلوب سقراطي في التدريس
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Tuple

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
import structlog

# تحميل متغيرات البيئة
load_dotenv()

# إعداد Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger(__name__)

# استيراد الوحدات المحلية
from bot.core.config import get_settings
from bot.core.llm_client import LLMClient
from bot.core.rag import RAGPipeline
from bot.core.student_manager import StudentManager


# ===== الإعدادات =====
settings = get_settings()

# طباعة معلومات المزود النشط
logger.info(f"🚀 Using LLM Provider: {settings.llm_provider}")
logger.info(f"🤖 Active Model: {settings.active_model}")
logger.info(f"📊 Active Embedding Model: {settings.active_embedding_model}")

# ===== تحميل System Prompt =====
SYSTEM_PROMPT = None
try:
    with open(settings.system_prompt_path, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read()
    logger.info(f"System prompt loaded from {settings.system_prompt_path}")
except FileNotFoundError:
    logger.warning(
        f"System prompt not found at {settings.system_prompt_path}, using default"
    )
    SYSTEM_PROMPT = (
        "أنت معلم رياضيات ذكي اسمه مستر AI. ساعد الطلاب بأسلوب ودود ومهني.\n"
        "استخدم أسلوب سقراطي: اسأل قبل أن تجيب. "
        "أعطِ أمثلة من الحياة الواقعية. شجّع الطالب دائماً."
    )
except Exception as e:
    logger.error(f"Failed to load system prompt: {e}")
    SYSTEM_PROMPT = "أنت معلم رياضيات ذكي اسمه مستر AI. ساعد الطلاب."


# ===== تهيئة الخدمات =====
rag_pipeline = RAGPipeline()
student_manager = StudentManager()


# ===== Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # البدء
    logger.info("Starting Mister AI...")
    try:
        await student_manager.initialize()
        rag_pipeline.ensure_collection_exists()
        logger.info("Mister AI started successfully")
    except Exception as e:
        logger.error(f"Failed to start: {e}")
    
    yield
    
    # الإغلاق
    logger.info("Shutting down Mister AI...")
    try:
        await student_manager.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# ===== FastAPI App =====
app = FastAPI(
    title="Mister AI Telegram Bot",
    description="بوت تعليمي ذكي لطلاب الثانوية",
    version="2.1.0",
    lifespan=lifespan,
)


# ===== Telegram Bot =====
bot = Bot(token=settings.telegram_bot_token)
telegram_app: Application = None


# ===== Telegram Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرد على /start"""
    telegram_id = update.effective_user.id
    student = await student_manager.get_student_by_telegram_id(telegram_id)
    
    if not student:
        await update.message.reply_text(
            "مرحباً! 👋 أنا مستر AI، معلمك الذكي للرياضيات.\n"
            "أنا أستخدم **Gemini 3.1 Flash Lite** لتقديم أفضل تجربة تعليمية.\n"
            "قبل أن نبدأ، ممكن أعرف اسمك؟"
        )
    else:
        await update.message.reply_text(
            f"أهلاً بعودتك {student['name']}! 😊\n"
            f"أنا مستخدم **{settings.active_model}** حالياً.\n"
            "كيف أستطيع مساعدتك اليوم في الرياضيات؟"
        )


async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الطالب"""
    telegram_id = update.effective_user.id
    text = update.message.text.strip()
    
    student = await student_manager.get_student_by_telegram_id(telegram_id)
    
    if not student:
        # الخطوة الأولى: الاسم
        await student_manager.create_student(
            telegram_id=telegram_id,
            name=text,
            grade="",
        )
        await update.message.reply_text(
            f"أهلاً {text}! 🎉\n"
            "ما صفك الدراسي؟ (مثلاً: ثالث ثانوي علمي)"
        )
    else:
        # الخطوة الثانية: الصف
        student = await student_manager.create_student(
            telegram_id=telegram_id,
            name=student["name"],
            grade=text,
        )
        await update.message.reply_text(
            f"تم تسجيلك بنجاح! 🎓\n"
            f"اسمك: {student['name']}\n"
            f"صفك: {text}\n"
            f"أنا أستخدم **{settings.active_model}** حالياً.\n"
            "الآن يمكنك طرح أي سؤال في الرياضيات وسأجيبك بأفضل ما أستطيع.\n"
            "جرب مثلاً: ما هي قاعدة اشتقاق x^2؟"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرد على الرسائل العادية"""
    telegram_id = update.effective_user.id
    user_message = update.message.text
    
    # استرجاع أو إنشاء الطالب
    student = await student_manager.get_student_by_telegram_id(telegram_id)
    
    if not student:
        # تسجيل جديد
        if not user_message.strip():
            await update.message.reply_text(
                "مرحباً! أنا مستر AI. ما اسمك؟"
            )
            return
        await start(update, context)
        return
    
    # تحديث نشاط الطالب
    await student_manager.update_student_activity(student["id"])
    
    # إنشاء جلسة جديدة
    session_id = await student_manager.create_session(student["id"])
    
    # إرسال رسالة "جاري التفكير..."
    thinking_msg = await update.message.reply_text("جاري التفكير... ⏳")
    
    # استدعاء RAG + LLM
    response, lesson_ids = await rag_pipeline.generate_response_with_rag(
        query=user_message,
        system_prompt=SYSTEM_PROMPT,
        student_context={
            "name": student["name"],
            "grade": student["grade"],
            "history": [],  # في الإنتاج، استرجع من قاعدة البيانات
        },
    )
    
    # حفظ الرسائل في قاعدة البيانات
    await student_manager.save_message(
        session_id=session_id,
        student_id=student["id"],
        role="user",
        content=user_message,
        retrieved_lesson_ids=lesson_ids,
        llm_model=settings.active_model,
    )
    await student_manager.save_message(
        session_id=session_id,
        student_id=student["id"],
        role="assistant",
        content=response,
        retrieved_lesson_ids=lesson_ids,
        llm_model=settings.active_model,
    )
    
    # تحديث تقدم الطالب
    if lesson_ids:
        for lesson_id in lesson_ids:
            await student_manager.update_student_progress(
                student_id=student["id"],
                lesson_id=lesson_id,
                mastery_status="learning",
            )
    
    # إنهاء الجلسة
    await student_manager.end_session(session_id)
    
    # تعديل الرسالة الأصلية بالرد
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=thinking_msg.message_id,
        text=response,
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=True)
    if update.effective_message:
        await update.effective_message.reply_text(
            "عذراً، حصل خطأ تقني. الرجاء المحاولة لاحقاً."
        )


# ===== FastAPI Endpoints =====
@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return {
        "app": "Mister AI",
        "version": "2.1.0",
        "status": "running",
        "langchain_version": "1.3+",
        "llm_provider": settings.llm_provider,
        "active_model": settings.active_model,
        "active_embedding_model": settings.active_embedding_model,
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
    }


@app.get("/health")
async def health():
    """فحص الحالة"""
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "active_model": settings.active_model,
    }


@app.get("/config")
async def get_config():
    """إرجاع إعدادات النظام"""
    return {
        "llm_provider": settings.llm_provider,
        "active_model": settings.active_model,
        "active_embedding_model": settings.active_embedding_model,
        "rag_top_k": settings.rag_top_k,
        "rag_score_threshold": settings.rag_score_threshold,
        "environment": settings.environment,
    }


@app.post("/webhook")
async def webhook(request: Request):
    """Webhook لتلقي تحديثات Telegram"""
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot)
        await telegram_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== إعداد Telegram Application =====
def setup_telegram_app() -> Application:
    """إعداد تطبيق Telegram"""
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالجة الأخطاء
    application.add_error_handler(error_handler)
    
    return application


# ===== بدء التطبيق =====
@app.on_event("startup")
async def startup_event():
    """أحداث البدء"""
    global telegram_app
    telegram_app = setup_telegram_app()
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Telegram application started")


@app.on_event("shutdown")
async def shutdown_event():
    """أحداث الإغلاق"""
    global telegram_app
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    logger.info("Telegram application stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bot.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.log_level.lower(),
    )
