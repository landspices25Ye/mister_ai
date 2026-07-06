# Mister AI - RAG Pipeline (LangChain v1.3+)
# bot/core/rag.py

"""
Pipeline متكامل لاسترجاع الدروس ذات الصلة وتوليد الردود
يدعم:
- Google Gemini (gemini-3.1-flash-lite)
- OpenAI (gpt-4o-mini)
- QdrantVectorStore
- LCEL (LangChain Expression Language)
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableParallel,
    RunnableLambda,
    RunnableConfig,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from bot.core.config import get_settings
from bot.core.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class RetrievedLesson:
    """درس مسترجع من Qdrant"""
    lesson_id: str
    chapter_id: str
    chunk_text: str
    score: float
    metadata: Dict


class RAGPipeline:
    """
    Pipeline كامل لـ RAG باستخدام LangChain v1.3+
    يدعم Google Gemini و OpenAI
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.settings = get_settings()
        self.llm_client = llm_client or LLMClient()
        
        # Qdrant client
        self._qdrant_client: Optional[QdrantClient] = None
        self._vector_store: Optional[QdrantVectorStore] = None
        self._retriever = None
    
    @property
    def qdrant_client(self) -> QdrantClient:
        """Lazy initialization لـ QdrantClient"""
        if self._qdrant_client is None:
            self._qdrant_client = QdrantClient(
                host=self.settings.qdrant_host,
                port=self.settings.qdrant_port,
            )
            logger.info(
                f"Connected to Qdrant: {self.settings.qdrant_host}:{self.settings.qdrant_port}"
            )
        return self._qdrant_client
    
    @property
    def vector_store(self) -> QdrantVectorStore:
        """Lazy initialization لـ QdrantVectorStore"""
        if self._vector_store is None:
            # تحديد بُعد الـ embeddings
            embedding_dim = 768 if self.settings.llm_provider == "gemini" else 1536
            
            self._vector_store = QdrantVectorStore.from_existing_collection(
                embedding=self.llm_client.embeddings,
                collection_name=self.settings.qdrant_collection,
                url=f"http://{self.settings.qdrant_host}:{self.settings.qdrant_port}",
                prefer_grpc=False,
            )
            logger.info(
                f"Loaded QdrantVectorStore: collection={self.settings.qdrant_collection}, "
                f"embedding_dim={embedding_dim}"
            )
        return self._vector_store
    
    @property
    def retriever(self):
        """إنشاء retriever مع إعدادات مخصصة"""
        if self._retriever is None:
            self._retriever = self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": self.settings.rag_top_k,
                    "score_threshold": self.settings.rag_score_threshold,
                },
            )
        return self._retriever
    
    def ensure_collection_exists(self) -> None:
        """
        التأكد من وجود المجموعة في Qdrant
        وإنشائها إذا لم تكن موجودة
        """
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.settings.qdrant_collection not in collection_names:
                logger.info(
                    f"Collection '{self.settings.qdrant_collection}' not found, creating..."
                )
                # تحديد بُعد الـ embeddings
                embedding_dim = 768 if self.settings.llm_provider == "gemini" else 1536
                
                self.qdrant_client.create_collection(
                    collection_name=self.settings.qdrant_collection,
                    vectors_config=qdrant_models.VectorParams(
                        size=embedding_dim,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info(f"Collection '{self.settings.qdrant_collection}' created")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}", exc_info=True)
            raise
    
    def format_docs(self, docs: List[Document]) -> str:
        """تنسيق المستندات المسترجعة للنظام"""
        if not docs:
            return "لا توجد دروس ذات صلة في المنهج."
        
        formatted = "\n\n--- الدروس ذات الصلة من المنهج ---\n"
        for i, doc in enumerate(docs, 1):
            lesson_id = doc.metadata.get("lesson_id", "غير معروف")
            chapter_id = doc.metadata.get("chapter_id", "غير معروف")
            formatted += (
                f"**الدرس {i}:** {lesson_id} (الفصل: {chapter_id})\n"
                f"**المحتوى:**\n{doc.page_content}\n\n"
            )
        return formatted
    
    def _format_retrieved_lessons(self, docs: List[Document]) -> List[RetrievedLesson]:
        """تحويل Documents إلى RetrievedLesson"""
        lessons = []
        for doc in docs:
            lessons.append(RetrievedLesson(
                lesson_id=doc.metadata.get("lesson_id", "unknown"),
                chapter_id=doc.metadata.get("chapter_id", "unknown"),
                chunk_text=doc.page_content,
                score=doc.metadata.get("score", 0.0),
                metadata=doc.metadata,
            ))
        return lessons
    
    def build_rag_chain(self, system_prompt: str):
        """
        بناء سلسلة RAG باستخدام LCEL
        
        السلسلة:
        1. استرجاع المستندات ذات الصلة من Qdrant
        2. دمجها مع System Prompt و System Context
        3. إرسالها لـ LLM
        4. إرجاع الرد
        """
        # قالب الـ Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("system", "{system_context}"),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{question}"),
        ])
        
        # دالة لتنسيق المستندات
        format_docs_runnable = RunnableLambda(self.format_docs)
        
        # بناء السلسلة باستخدام LCEL
        rag_chain = (
            RunnableParallel(
                question=RunnablePassthrough(),
                documents=self.retriever | format_docs_runnable,
            )
            | RunnableParallel(
                question=RunnableLambda(lambda x: x["question"]),
                system_context=RunnableLambda(
                    lambda x: (
                        f"اسم الطالب: {x.get('student_name', 'غير معروف')}\n"
                        f"صفه: {x.get('student_grade', 'غير محدد')}\n\n"
                        f"{x.get('documents', '')}"
                    )
                ),
                chat_history=RunnableLambda(lambda x: x.get("chat_history", [])),
            )
            | prompt
            | self.llm_client.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    async def retrieve_relevant_lessons(self, query: str) -> List[RetrievedLesson]:
        """
        استرجاع الدروس ذات الصلة من Qdrant
        
        Args:
            query: سؤال الطالب
        
        Returns:
            List[RetrievedLesson] من الدروس المسترجعة
        """
        try:
            # استخدام similarity_search_with_score للحصول على النقاط
            docs_with_scores = await self.vector_store.asimilarity_search_with_relevance_scores(
                query,
                k=self.settings.rag_top_k,
                score_threshold=self.settings.rag_score_threshold,
            )
            
            lessons = []
            for doc, score in docs_with_scores:
                lessons.append(RetrievedLesson(
                    lesson_id=doc.metadata.get("lesson_id", "unknown"),
                    chapter_id=doc.metadata.get("chapter_id", "unknown"),
                    chunk_text=doc.page_content,
                    score=float(score),
                    metadata=doc.metadata,
                ))
            
            logger.info(f"Retrieved {len(lessons)} lessons for query: {query[:50]}...")
            return lessons
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            return []
    
    async def generate_response_with_rag(
        self,
        query: str,
        system_prompt: str,
        student_context: Dict,
    ) -> Tuple[str, List[str]]:
        """
        توليد رد باستخدام RAG
        
        Args:
            query: سؤال الطالب
            system_prompt: System Prompt الرئيسي
            student_context: سياق الطالب (name, grade, history)
        
        Returns:
            Tuple[str, List[str]]: (الرد, IDs الدروس المستخدمة)
        """
        try:
            # 1. استرجاع الدروس ذات الصلة
            lessons = await self.retrieve_relevant_lessons(query)
            lesson_ids = [lesson.lesson_id for lesson in lessons]
            
            # 2. تنسيق المستندات
            docs = [
                Document(
                    page_content=lesson.chunk_text,
                    metadata={
                        "lesson_id": lesson.lesson_id,
                        "chapter_id": lesson.chapter_id,
                        "score": lesson.score,
                        **lesson.metadata,
                    }
                )
                for lesson in lessons
            ]
            context_str = self.format_docs(docs)
            
            # 3. بناء الرسائل
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "system",
                    "content": (
                        f"اسم الطالب: {student_context.get('name', 'غير معروف')}\n"
                        f"صفه: {student_context.get('grade', 'غير محدد')}\n\n"
                        f"{context_str}"
                    )
                },
            ]
            
            # إضافة تاريخ المحادثة
            history = student_context.get("history", [])[-4:]
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
            
            # 4. إضافة سؤال الطالب
            messages.append({"role": "user", "content": query})
            
            # 5. استدعاء LLM
            response = await self.llm_client.generate(messages)
            
            return response.response, lesson_ids
            
        except Exception as e:
            logger.error(f"RAG response generation failed: {e}", exc_info=True)
            return (
                "عذراً، حصل خطأ تقني. الرجاء المحاولة لاحقاً.",
                []
            )
