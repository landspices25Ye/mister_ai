# Mister AI - Configuration
# bot/core/config.py

"""
إعدادات التطبيق باستخدام Pydantic Settings v2
يدعم مزودي LLM متعددين (OpenAI, Google Gemini)
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# النماذج المدعومة لكل مزود
SUPPORTED_MODELS = {
    "gemini": [
        "gemini-3.1-flash-lite",        # الافتراضي - خفيف وسريع
        "gemini-3.5-flash",
        "gemini-3-pro",
        "gemini-2.5-flash",
    ],
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
}

# النماذج المتاحة للـ Embeddings (مقاطع نصية)
SUPPORTED_EMBEDDING_MODELS = {
    "gemini": [
        "models/text-embedding-004",
        "models/embedding-001",
    ],
    "openai": [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    ],
}


class Settings(BaseSettings):
    """إعدادات التطبيق الرئيسية"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===== LLM Provider =====
    llm_provider: Literal["gemini", "openai"] = Field(
        default="gemini",
        description="مزود LLM المستخدم (gemini أو openai)"
    )
    
    # ===== Telegram Bot =====
    telegram_bot_token: str = Field(..., description="Telegram Bot Token")
    
    # ===== Google Gemini =====
    google_api_key: str = Field(
        default="",
        description="Google AI Studio API Key"
    )
    gemini_model: str = Field(
        default="gemini-3.1-flash-lite",
        description="نموذج Gemini المستخدم"
    )
    gemini_embedding_model: str = Field(
        default="models/text-embedding-004",
        description="نموذج Gemini Embeddings"
    )
    
    # ===== OpenAI =====
    openai_api_key: str = Field(
        default="",
        description="OpenAI API Key"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="نموذج OpenAI"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="نموذج OpenAI Embeddings"
    )
    
    # ===== النموذج النشط (يحسب تلقائياً) =====
    active_model: str = Field(default="", description="النموذج النشط (محسوب)")
    active_embedding_model: str = Field(default="", description="نموذج Embeddings النشط (محسوب)")
    
    # ===== PostgreSQL =====
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="mister_ai_user")
    postgres_password: str = Field(...)
    postgres_db: str = Field(default="mister_ai")
    
    # ===== Redis =====
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    
    # ===== Qdrant =====
    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="mister_ai_curriculum")
    
    # ===== RAG =====
    rag_top_k: int = Field(default=4, ge=1, le=20)
    rag_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    rag_chunk_size: int = Field(default=1000, ge=100, le=4000)
    rag_chunk_overlap: int = Field(default=200, ge=0, le=1000)
    
    # ===== System Prompt =====
    system_prompt_path: str = Field(
        default="/app/prompts/system_prompt.md",
        description="مسار ملف System Prompt"
    )
    
    # ===== LLM Settings =====
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1000, ge=100, le=8000)
    llm_timeout: int = Field(default=30)
    
    # ===== App Settings =====
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    environment: Literal["development", "staging", "production"] = Field(default="production")
    
    @model_validator(mode="after")
    def compute_active_models_and_validate(self):
        """حساب النموذج النشط والتحقق من الإعدادات"""
        # حساب النموذج النشط
        if self.llm_provider == "gemini":
            self.active_model = self.gemini_model
            self.active_embedding_model = self.gemini_embedding_model
            
            if not self.google_api_key:
                raise ValueError(
                    "GOOGLE_API_KEY مطلوب عند استخدام llm_provider=gemini. "
                    "احصل عليه من https://aistudio.google.com/apikey"
                )
        else:  # openai
            self.active_model = self.openai_model
            self.active_embedding_model = self.openai_embedding_model
            
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY مطلوب عند استخدام llm_provider=openai"
                )
        
        return self
    
    @field_validator("telegram_bot_token", "postgres_password")
    @classmethod
    def validate_required_secrets(cls, v: str, info) -> str:
        if not v or v.startswith("your_") or v == "***":
            raise ValueError(
                f"{info.field_name} مطلوب. أضفه في ملف .env"
            )
        return v
    
    @property
    def postgres_dsn(self) -> str:
        """DSN لـ PostgreSQL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def postgres_dsn_async(self) -> str:
        """DSN غير متزامن لـ PostgreSQL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """URL لـ Redis"""
        return f"redis://{self.redis_host}:{self.redis_port}/0"
    
    def get_provider_info(self) -> dict:
        """معلومات المزود النشط"""
        return {
            "provider": self.llm_provider,
            "model": self.active_model,
            "embedding_model": self.active_embedding_model,
        }


@lru_cache
def get_settings() -> Settings:
    """إرجاع الإعدادات (مع caching)"""
    return Settings()
