# Mister AI - Student Manager (psycopg3 + SQLAlchemy 2.0 async)
# bot/core/student_manager.py

"""
إدارة بيانات الطلاب وتقدمهم باستخدام:
- psycopg3 (الأحدث من psycopg2)
- SQLAlchemy 2.0 async
- asyncpg للـ async driver
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import select, update, insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Float,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY

from bot.core.config import get_settings

logger = logging.getLogger(__name__)


# ===== نماذج SQLAlchemy =====

class Base(DeclarativeBase):
    """القاعدة لجميع النماذج"""
    pass


class Student(Base):
    """نموذج الطالب"""
    __tablename__ = "students"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="uuid_generate_v4()"
    )
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    whatsapp_phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="ar")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[Dict] = mapped_column("metadata", JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Chapter(Base):
    """نموذج الفصل"""
    __tablename__ = "chapters"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Lesson(Base):
    """نموذج الدرس"""
    __tablename__ = "lessons"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty_level: Mapped[int] = mapped_column(Integer, default=1)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=45)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    learning_objectives: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    prerequisites: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Session(Base):
    """نموذج الجلسة"""
    __tablename__ = "sessions"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="uuid_generate_v4()"
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    session_metadata: Mapped[Dict] = mapped_column(JSONB, default=dict)


class Message(Base):
    """نموذج الرسالة"""
    __tablename__ = "messages"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="uuid_generate_v4()"
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_lesson_ids: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    llm_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StudentProgress(Base):
    """نموذج تقدّم الطالب"""
    __tablename__ = "student_progress"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="uuid_generate_v4()"
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    mastery_status: Mapped[str] = mapped_column(String(20), default="not_started")
    last_quiz_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_quiz_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_minutes: Mapped[int] = mapped_column(Integer, default=0)
    weak_topics: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mastered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# ===== إدارة قاعدة البيانات =====


class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self):
        self.settings = get_settings()
        self._engine = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    async def connect(self):
        """الاتصال بقاعدة البيانات"""
        if self._engine is None:
            self._engine = create_async_engine(
                self.settings.postgres_dsn_async,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
            )
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            logger.info(f"Connected to PostgreSQL: {self.settings.postgres_host}")
    
    async def disconnect(self):
        """قطع الاتصال بقاعدة البيانات"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Disconnected from PostgreSQL")
    
    @asynccontextmanager
    async def session(self):
        """إنشاء جلسة قاعدة بيانات"""
        if self._session_factory is None:
            await self.connect()
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


class StudentManager:
    """
    إدارة بيانات الطلاب - API عالي المستوى
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.db = DatabaseManager()
    
    async def initialize(self):
        """تهيئة قاعدة البيانات"""
        await self.db.connect()
        logger.info("StudentManager initialized")
    
    async def shutdown(self):
        """إغلاق قاعدة البيانات"""
        await self.db.disconnect()
    
    async def get_student_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """استرجاع بيانات الطالب بواسطة معرف Telegram"""
        async with self.db.session() as session:
            stmt = select(Student).where(Student.telegram_id == telegram_id)
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()
            
            if student is None:
                return None
            
            return {
                "id": str(student.id),
                "telegram_id": student.telegram_id,
                "name": student.name,
                "grade": student.grade,
                "preferred_language": student.preferred_language,
                "joined_at": student.joined_at,
                "last_active_at": student.last_active_at,
                "total_messages": student.total_messages,
                "is_active": student.is_active,
            }
    
    async def create_student(
        self,
        telegram_id: int,
        name: str,
        grade: str,
    ) -> Dict:
        """إنشاء طالب جديد"""
        async with self.db.session() as session:
            student = Student(
                telegram_id=telegram_id,
                name=name,
                grade=grade,
                joined_at=datetime.utcnow(),
                last_active_at=datetime.utcnow(),
            )
            session.add(student)
            await session.flush()
            await session.refresh(student)
            
            return {
                "id": str(student.id),
                "telegram_id": student.telegram_id,
                "name": student.name,
                "grade": student.grade,
                "preferred_language": student.preferred_language,
            }
    
    async def update_student_activity(self, student_id: str) -> None:
        """تحديث آخر نشاط للطالب"""
        async with self.db.session() as session:
            stmt = (
                update(Student)
                .where(Student.id == UUID(student_id))
                .values(
                    last_active_at=datetime.utcnow(),
                    total_messages=Student.total_messages + 1,
                )
            )
            await session.execute(stmt)
    
    async def create_session(self, student_id: str) -> str:
        """إنشاء جلسة جديدة"""
        async with self.db.session() as session:
            new_session = Session(
                student_id=UUID(student_id),
                started_at=datetime.utcnow(),
            )
            session.add(new_session)
            await session.flush()
            await session.refresh(new_session)
            return str(new_session.id)
    
    async def end_session(self, session_id: str) -> None:
        """إنهاء جلسة"""
        async with self.db.session() as session:
            stmt = (
                update(Session)
                .where(Session.id == UUID(session_id))
                .values(ended_at=datetime.utcnow())
            )
            await session.execute(stmt)
    
    async def save_message(
        self,
        session_id: str,
        student_id: str,
        role: str,
        content: str,
        retrieved_lesson_ids: Optional[List[str]] = None,
        llm_model: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """حفظ رسالة في قاعدة البيانات"""
        async with self.db.session() as session:
            message = Message(
                session_id=UUID(session_id),
                student_id=UUID(student_id),
                role=role,
                content=content,
                retrieved_lesson_ids=retrieved_lesson_ids or [],
                llm_model=llm_model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
            )
            session.add(message)
    
    async def update_student_progress(
        self,
        student_id: str,
        lesson_id: str,
        mastery_status: str = "learning",
        quiz_score: Optional[float] = None,
    ) -> None:
        """تحديث تقدم الطالب في درس معين"""
        async with self.db.session() as session:
            # التحقق من وجود سجل
            stmt = select(StudentProgress).where(
                (StudentProgress.student_id == UUID(student_id))
                & (StudentProgress.lesson_id == lesson_id)
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()
            
            if progress:
                # تحديث السجل
                progress.mastery_status = mastery_status
                if quiz_score is not None:
                    progress.last_quiz_score = quiz_score
                    progress.best_quiz_score = max(
                        progress.best_quiz_score or 0, quiz_score
                    )
                progress.attempts_count += 1
                progress.last_attempt_at = datetime.utcnow()
            else:
                # إنشاء سجل جديد
                progress = StudentProgress(
                    student_id=UUID(student_id),
                    lesson_id=lesson_id,
                    mastery_status=mastery_status,
                    last_quiz_score=quiz_score,
                    best_quiz_score=quiz_score,
                    attempts_count=1,
                    last_attempt_at=datetime.utcnow(),
                )
                session.add(progress)
