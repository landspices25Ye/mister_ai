# Mister AI - Student Manager
# bot/core/student_manager.py

"""
إدارة بيانات الطلاب وتقدمهم
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime

import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor

logger = logging.getLogger(__name__)

class StudentManager:
    def __init__(self):
        self.db_conn = self._init_db()

    def _init_db(self):
        """تهيئة اتصال قاعدة البيانات"""
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                database=os.getenv("POSTGRES_DB", "mister_ai"),
                user=os.getenv("POSTGRES_USER", "mister_ai"),
                password=os.getenv("POSTGRES_PASSWORD")
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_student_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """استرجاع بيانات الطالب بواسطة معرف Telegram"""
        with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM students WHERE telegram_id = %s",
                (telegram_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None

    def create_student(self, telegram_id: int, name: str, grade: str) -> Dict:
        """إنشاء طالب جديد"""
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO students (telegram_id, name, grade, joined_at, last_active_at) "
                "VALUES (%s, %s, %s, NOW(), NOW()) RETURNING *",
                (telegram_id, name, grade)
            )
            self.db_conn.commit()
            student = cursor.fetchone()
            return dict(student)

    def update_student_activity(self, student_id: str) -> None:
        """تحديث آخر نشاط للطالب"""
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                "UPDATE students SET last_active_at = NOW(), total_messages = total_messages + 1 "
                "WHERE id = %s",
                (student_id,)
            )
            self.db_conn.commit()

    def create_session(self, student_id: str) -> str:
        """إنشاء جلسة جديدة للطالب"""
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO sessions (student_id, started_at) VALUES (%s, NOW()) RETURNING id",
                (student_id,)
            )
            self.db_conn.commit()
            return cursor.fetchone()[0]

    def end_session(self, session_id: str) -> None:
        """إنهاء جلسة الطالب"""
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                "UPDATE sessions SET ended_at = NOW() WHERE id = %s",
                (session_id,)
            )
            self.db_conn.commit()

    def save_message(
        self,
        session_id: str,
        student_id: str,
        role: str,
        content: str,
        retrieved_lesson_ids: Optional[List[str]] = None,
        llm_model: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        latency_ms: int = 0
    ) -> None:
        """حفظ رسالة في قاعدة البيانات"""
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages "
                "(session_id, student_id, role, content, retrieved_lesson_ids, llm_model, tokens_input, tokens_output, latency_ms) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    session_id,
                    student_id,
                    role,
                    content,
                    retrieved_lesson_ids,
                    llm_model,
                    tokens_input,
                    tokens_output,
                    latency_ms
                )
            )
            self.db_conn.commit()

    def update_student_progress(
        self,
        student_id: str,
        lesson_id: str,
        mastery_status: str = "learning",
        quiz_score: Optional[float] = None
    ) -> None:
        """تحديث تقدم الطالب في درس معين"""
        with self.db_conn.cursor() as cursor:
            # تحقق إذا كان السجل موجود
            cursor.execute(
                "SELECT * FROM student_progress WHERE student_id = %s AND lesson_id = %s",
                (student_id, lesson_id)
            )
            
            if cursor.fetchone():
                # تحديث السجل
                update_query = "UPDATE student_progress SET "
                params = []
                
                if mastery_status:
                    update_query += "mastery_status = %s, "
                    params.append(mastery_status)
                
                if quiz_score is not None:
                    update_query += "last_quiz_score = %s, best_quiz_score = GREATEST(best_quiz_score, %s), "
                    params.extend([quiz_score, quiz_score])
                
                update_query += "attempts_count = attempts_count + 1, last_attempt_at = NOW() "
                update_query += "WHERE student_id = %s AND lesson_id = %s"
                params.extend([student_id, lesson_id])
                
                cursor.execute(update_query, params)
            else:
                # إنشاء سجل جديد
                cursor.execute(
                    "INSERT INTO student_progress "
                    "(student_id, lesson_id, mastery_status, last_quiz_score, best_quiz_score, attempts_count, last_attempt_at) "
                    "VALUES (%s, %s, %s, %s, %s, 1, NOW())",
                    (student_id, lesson_id, mastery_status, quiz_score, quiz_score)
                )
            
            self.db_conn.commit()

    def close(self):
        """إغلاق اتصال قاعدة البيانات"""
        if self.db_conn:
            self.db_conn.close()