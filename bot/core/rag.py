# Mister AI - RAG Pipeline
# bot/core/rag.py

"""
Pipeline لاسترجاع الدروس ذات الصلة من Qdrant وإرسالها لـ LLM
"""

import os
import logging
from typing import List, Dict, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import ScoredPoint
from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RetrievedLesson(BaseModel):
    lesson_id: str
    chapter_id: str
    chunk_text: str
    score: float

class RAGPipeline:
    def __init__(self):
        self.qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.collection_name = "mister_ai_curriculum"
        self.embedding_model = "text-embedding-3-small"
        self.top_k = 3  # عدد الدروس المسترجعة
        self.min_score = 0.7  # الحد الأدنى للتشابه

    async def generate_embedding(self, text: str) -> List[float]:
        """توليد embedding للنص"""
        response = await self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def retrieve_relevant_lessons(self, query: str) -> List[RetrievedLesson]:
        """استرجاع الدروس ذات الصلة من Qdrant"""
        try:
            embedding = await self.generate_embedding(query)
            
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=self.top_k,
                score_threshold=self.min_score
            )
            
            lessons = []
            for result in results:
                lessons.append(RetrievedLesson(
                    lesson_id=result.payload["lesson_id"],
                    chapter_id=result.payload["chapter_id"],
                    chunk_text=result.payload["chunk_text"],
                    score=result.score
                ))
            
            logger.info(f"Retrieved {len(lessons)} lessons for query: {query}")
            return lessons
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []

    def format_retrieved_lessons(self, lessons: List[RetrievedLesson]) -> str:
        """تنسيق الدروس المسترجعة للنظام"""
        if not lessons:
            return "لا توجد دروس ذات صلة في المنهج."
        
        formatted = "\n\n--- الدروس ذات الصلة من المنهج ---\n"
        for i, lesson in enumerate(lessons, 1):
            formatted += (
                f"**الدرس {i}:** {lesson.lesson_id} (الفصل: {lesson.chapter_id})\n"
                f"**التشابه:** {lesson.score:.2f}\n"
                f"**المحتوى:**\n{lesson.chunk_text}\n\n"
            )
        
        return formatted

    async def generate_response_with_rag(
        self,
        query: str,
        system_prompt: str,
        student_context: Dict
    ) -> str:
        """توليد رد باستخدام RAG"""
        # استرجاع الدروس ذات الصلة
        lessons = await self.retrieve_relevant_lessons(query)
        
        # تنسيق السياق
        context = self.format_retrieved_lessons(lessons)
        
        # بناء الرسائل
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": (
                f"اسم الطالب: {student_context.get('name', 'غير معروف')}\n"
                f"صفه: {student_context.get('grade', 'غير محدد')}\n"
                f"\n{context}"
            )}
        ]
        
        # إضافة تاريخ المحادثة
        for msg in student_context.get("history", [])[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": query})
        
        # استدعاء LLM
        try:
            response = await self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            # استخراج IDs الدروس المستخدمة
            lesson_ids = [lesson.lesson_id for lesson in lessons]
            
            return response.choices[0].message.content.strip(), lesson_ids
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return "عذراً، حصل خطأ تقني. الرجاء المحاولة لاحقاً.", []