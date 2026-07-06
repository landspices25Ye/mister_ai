# Mister AI - Ingest Curriculum Script (LangChain v1.3+)
# scripts/ingest_curriculum.py

"""
سكريبت لفهرسة المنهج في Qdrant باستخدام LangChain الحديث
يدعم:
- Google Gemini (models/text-embedding-004)
- OpenAI (text-embedding-3-small)
- MarkdownTextSplitter
- QdrantVectorStore

الاستخدام:
1. تأكد من وجود ملف .env مع GOOGLE_API_KEY أو OPENAI_API_KEY
2. شغل السكريبت: python -m scripts.ingest_curriculum
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List

# إضافة المجلد الرئيسي إلى PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from bot.core.config import get_settings
from bot.core.llm_client import LLMClient

# إعداد Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CurriculumIngester:
    """
    فئة لفهرسة المنهج في Qdrant باستخدام LangChain
    يدعم Google Gemini و OpenAI
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.llm_client = LLMClient()
        
        # Qdrant client
        self.qdrant_client = QdrantClient(
            host=self.settings.qdrant_host,
            port=self.settings.qdrant_port,
        )
        self.collection_name = self.settings.qdrant_collection
        
        # Text Splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.rag_chunk_size,
            chunk_overlap=self.settings.rag_chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
        )
        
        # طباعة معلومات المزود
        logger.info(f"🚀 Using LLM Provider: {self.settings.llm_provider}")
        logger.info(f"🤖 Active Model: {self.settings.active_model}")
        logger.info(f"📊 Active Embedding Model: {self.settings.active_embedding_model}")
    
    def ensure_collection_exists(self) -> None:
        """التأكد من وجود المجموعة في Qdrant"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(
                    f"Creating collection '{self.collection_name}'..."
                )
                # تحديد بُعد الـ embeddings
                embedding_dim = 768 if self.settings.llm_provider == "gemini" else 1536
                
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=embedding_dim,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info(f"Collection '{self.collection_name}' created")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}", exc_info=True)
            raise
    
    def process_markdown_file(self, file_path: Path) -> List[Document]:
        """
        معالجة ملف Markdown وتحويله إلى Documents
        
        Returns:
            List[Document] مع البيانات الوصفية
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # استخراج البيانات الوصفية
        lesson_id = file_path.stem  # "lesson_1_1"
        chapter_id = file_path.parent.name  # "ch01_derivatives"
        
        # تقسيم النص
        chunks = self.text_splitter.split_text(content)
        
        documents = []
        for idx, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "lesson_id": lesson_id,
                    "chapter_id": chapter_id,
                    "subject": "math",
                    "grade": "third_secondary_science",
                    "chunk_index": idx,
                    "file_path": str(file_path),
                    "source": "curriculum",
                },
            )
            documents.append(doc)
        
        return documents
    
    def find_markdown_files(self, curriculum_path: str = "curriculum") -> List[Path]:
        """البحث عن جميع ملفات Markdown في المنهج"""
        curriculum_dir = Path(curriculum_path)
        if not curriculum_dir.exists():
            logger.warning(f"Curriculum directory not found: {curriculum_path}")
            return []
        
        markdown_files = sorted(curriculum_dir.glob("**/*.md"))
        return markdown_files
    
    async def ingest_curriculum(
        self,
        curriculum_path: str = "curriculum",
    ) -> None:
        """
        فهرسة جميع ملفات المنهج في Qdrant
        
        Args:
            curriculum_path: مسار مجلد المنهج
        """
        # 1. التأكد من وجود المجموعة
        self.ensure_collection_exists()
        
        # 2. البحث عن ملفات Markdown
        markdown_files = self.find_markdown_files(curriculum_path)
        if not markdown_files:
            logger.warning(f"No markdown files found in {curriculum_path}")
            return
        
        logger.info(f"Found {len(markdown_files)} markdown files")
        
        # 3. معالجة كل ملف
        all_documents = []
        for file_path in markdown_files:
            try:
                documents = self.process_markdown_file(file_path)
                all_documents.extend(documents)
                logger.info(
                    f"Processed {file_path.name}: {len(documents)} chunks"
                )
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        if not all_documents:
            logger.warning("No documents to ingest")
            return
        
        logger.info(f"Total chunks: {len(all_documents)}")
        
        # 4. فهرسة في Qdrant باستخدام QdrantVectorStore
        try:
            logger.info("Creating embeddings and ingesting into Qdrant...")
            
            # استخدام from_documents يقوم بالإنشاء والإضافة تلقائياً
            vector_store = await QdrantVectorStore.afrom_documents(
                documents=all_documents,
                embedding=self.llm_client.embeddings,
                collection_name=self.collection_name,
                url=f"http://{self.settings.qdrant_host}:{self.settings.qdrant_port}",
                prefer_grpc=False,
            )
            
            logger.info(
                f"Successfully ingested {len(all_documents)} chunks "
                f"into '{self.collection_name}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to ingest documents: {e}", exc_info=True)
            raise


async def main():
    """الدالة الرئيسية"""
    logger.info("=" * 60)
    logger.info("Mister AI - Curriculum Ingestion")
    logger.info("=" * 60)
    
    try:
        ingester = CurriculumIngester()
        await ingester.ingest_curriculum("curriculum")
        logger.info("=" * 60)
        logger.info("Ingestion completed successfully!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
