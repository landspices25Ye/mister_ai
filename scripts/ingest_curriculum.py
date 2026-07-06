# Mister AI - Ingest Curriculum Script
# scripts/ingest_curriculum.py

"""
سكريبت لفهرسة المنهج في Qdrant لاستخدامه في RAG

الاستخدام:
1. ثبت المتطلبات: pip install qdrant-client openai pypdf
2. شغل السكريبت: python scripts/ingest_curriculum.py
"""

import os
import logging
from typing import List
from pathlib import Path

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from openai import OpenAI
from dotenv import load_dotenv

# الإعدادات
load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)
COLLECTION_NAME = "mister_ai_curriculum"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 500  # أحرف

# إعداد Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعداد العملاء
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """تقسيم النص إلى chunks"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks

def generate_embedding(text: str) -> List[float]:
    """توليد embedding للنص باستخدام OpenAI"""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

def process_markdown_file(file_path: Path) -> List[PointStruct]:
    """معالجة ملف Markdown وإنتاج نقاط لـ Qdrant"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # استخراج البيانات الوصفية
    lesson_id = file_path.stem  # "lesson_1_1"
    chapter_id = file_path.parent.name  # "ch01_derivatives"
    subject = "math"
    grade = "third_secondary_science"
    
    # تقسيم المحتوى
    chunks = chunk_text(content)
    
    points = []
    for idx, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk)
        
        point = PointStruct(
            id=f"{lesson_id}_{idx}",
            vector=embedding,
            payload={
                "lesson_id": lesson_id,
                "chapter_id": chapter_id,
                "subject": subject,
                "grade": grade,
                "chunk_index": idx,
                "chunk_text": chunk,
                "file_path": str(file_path)
            }
        )
        points.append(point)
    
    return points

def create_collection():
    """إنشاء مجموعة جديدة في Qdrant"""
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=1536,  # بُعد OpenAI embeddings
            distance=models.Distance.COSINE
        )
    )
    logger.info(f"Collection '{COLLECTION_NAME}' created successfully")

def ingest_curriculum(curriculum_path: str = "curriculum"):
    """فهرسة جميع ملفات المنهج"""
    curriculum_dir = Path(curriculum_path)
    markdown_files = list(curriculum_dir.glob("**/*.md"))
    
    if not markdown_files:
        logger.warning("No markdown files found in curriculum directory")
        return
    
    logger.info(f"Found {len(markdown_files)} markdown files to ingest")
    
    # إنشاء المجموعة
    create_collection()
    
    # معالجة كل ملف
    all_points = []
    for file_path in markdown_files:
        try:
            points = process_markdown_file(file_path)
            all_points.extend(points)
            logger.info(f"Processed {file_path} - {len(points)} chunks")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
    
    # رفع النقاط إلى Qdrant
    if all_points:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=all_points,
            wait=True
        )
        logger.info(f"Successfully ingested {len(all_points)} chunks into Qdrant")
    else:
        logger.warning("No points to ingest")

if __name__ == "__main__":
    ingest_curriculum()
