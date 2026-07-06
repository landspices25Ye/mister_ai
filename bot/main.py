# Mister AI - Telegram Bot MVP
# main.py

"""
بوت Telegram بسيط يستخدم FastAPI + python-telegram-bot
يستقبل رسائل الطلاب ويرسلها لـ LLM (مستقبلاً مع RAG)

الاستخدام:
1. ثبت المتطلبات: pip install python-telegram-bot fastapi uvicorn python-dotenv
2. أنشئ ملف .env (انظر .env.example)
3. شغل البوت: uvicorn main:app --reload
"""

import os
import logging
from typing import Dict, Optional, List

from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackContext
)
from dotenv import load_dotenv
from pydantic import BaseSettings

# استيراد الوحدات المحلية
from bot.core.rag import RAGPipeline
from bot.core.llm_client import LLMClient
from bot.core.student_manager import StudentManager

# --- الإعدادات ---
load_dotenv()

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    SYSTEM_PROMPT_PATH: str = "prompts/system_prompt.md"
    
    class Config:
        env_file = ".env"

settings = Settings()

# --- الإعدادات الأساسية ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- تحميل System Prompt ---
try:
    with open(settings.SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read()
except Exception as e:
    logger.error(f"Failed to load system prompt: {e}")
    SYSTEM_PROMPT = "أنت معلم رياضيات ذكي اسمه مستر AI. ساعد الطلاب بأسلوب ودود ومهني."

# --- FastAPI App ---
app = FastAPI(title="Mister AI Telegram Bot")

# --- Telegram Bot ---
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

# --- تهيئة الخدمات ---
rag_pipeline = RAGPipeline()
llm_client = LLMClient()
student_manager = StudentManager()

# --- LLM Client ---
async def generate_response(prompt: str, student_context: Dict) -> tuple[str, List[str]]:
    """استدعاء LLM مع سياق الطالب باستخدام RAG"""
    # استرجاع الدروس ذات الصلة
    response, lesson_ids = await rag_pipeline.generate_response_with_rag(
        query=prompt,
        system_prompt=SYSTEM_PROMPT,
        student_context=student_context
    )
    
    return response, lesson_ids

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرد على /start"""
    telegram_id = update.effective_user.id
    student_context = get_student_context(telegram_id)
    
    if not student_context["registration_complete"]:
        await update.message.reply_text(
            "مرحباً! 👋 أنا مستر AI، معلمك الذكي للرياضيات.\n"
            "قبل أن نبدأ، ممكن أعرف اسمك؟"
        )
    else:
        await update.message.reply_text(
            f"أهلاً بعودتك {student_context['name']}! 😊\n"
            "كيف أستطيع مساعدتك اليوم في الرياضيات؟"
        )

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الطالب"""
    telegram_id = update.effective_user.id
    text = update.message.text
    
    # استرجاع الطالب المؤقت
    student = student_manager.get_student_by_telegram_id(telegram_id)
    
    if not student:
        # الخطوة الأولى: الاسم
        student = student_manager.create_student(
            telegram_id=telegram_id,
            name=text,
            grade=""
        )
        await update.message.reply_text(
            f"أهلاً {text}! 🎉\n"
            "ما صفك الدراسي؟ (مثلاً: ثالث ثانوي علمي)"
        )
    else:
        # الخطوة الثانية: الصف
        student = student_manager.create_student(
            telegram_id=telegram_id,
            name=student["name"],
            grade=text
        )
        await update.message.reply_text(
            f"تم تسجيلك بنجاح! 🎓\n"
            f"اسمك: {student['name']}\n"
            f"صفك: {text}\n"
            "الآن يمكنك طرح أي سؤال في الرياضيات وسأجيبك بأفضل ما أستطيع.\n"
            "جرب مثلاً: ما هي قاعدة اشتقاق x^2؟"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرد على الرسائل العادية"""
    telegram_id = update.effective_user.id
    user_message = update.message.text
    
    # استرجاع أو إنشاء الطالب
    student = student_manager.get_student_by_telegram_id(telegram_id)
    
    if not student:
        # تسجيل جديد
        if not getattr(update.message, 'text', '').strip():
            await update.message.reply_text("مرحباً! أنا مستر AI. ما اسمك؟")
            return
        
        # نبدأ عملية التسجيل
        await start(update, context)
        return
    
    # تحديث نشاط الطالب
    student_manager.update_student_activity(student["id"])
    
    # إنشاء جلسة جديدة
    session_id = student_manager.create_session(student["id"])
    
    # إرسال رسالة "جاري التفكير..."
    thinking_msg = await update.message.reply_text("جاري التفكير... ⏳")
    
    # استدعاء LLM مع RAG
    response, lesson_ids = await generate_response(user_message, {
        "name": student["name"],
        "grade": student["grade"],
        "history": []  # في الإنتاج، استرجع من قاعدة البيانات
    })
    
    # حفظ الرسالة في قاعدة البيانات
    student_manager.save_message(
        session_id=session_id,
        student_id=student["id"],
        role="user",
        content=user_message,
        retrieved_lesson_ids=lesson_ids,
        llm_model=settings.OPENAI_MODEL
    )
    
    student_manager.save_message(
        session_id=session_id,
        student_id=student["id"],
        role="assistant",
        content=response,
        retrieved_lesson_ids=lesson_ids,
        llm_model=settings.OPENAI_MODEL
    )
    
    # تحديث تقدم الطالب
    if lesson_ids:
        for lesson_id in lesson_ids:
            student_manager.update_student_progress(
                student_id=student["id"],
                lesson_id=lesson_id,
                mastery_status="learning"
            )
    
    # إنهاء الجلسة
    student_manager.end_session(session_id)
    
    # تعديل الرسالة الأصلية
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=thinking_msg.message_id,
        text=response
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء"""
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("عذراً، حصل خطأ تقني. الرجاء المحاولة لاحقاً.")

# --- FastAPI Endpoints ---
@app.post("/webhook")
async def webhook(request: Request):
    """Webhook لتلقي تحديثات Telegram"""
    update = Update.de_json(await request.json(), bot)
    await application.process_update(update)
    return {"status": "ok"}

# --- إعداد التطبيق ---
def setup_application():
    """إعداد تطبيق Telegram"""
    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)
    
    return application

# --- بدء التطبيق ---
application = setup_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
