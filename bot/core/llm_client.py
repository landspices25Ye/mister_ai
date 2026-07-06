# Mister AI - LLM Client (LangChain v1.3+)
# bot/core/llm_client.py

"""
عميل LLM متعدد المزودين
يدعم:
- Google Gemini (gemini-3.1-flash-lite)
- OpenAI (gpt-4o-mini)
- توليد النصوص
- توليد Embeddings
- استخدام LCEL (LangChain Expression Language)
"""

import logging
import time
from typing import Dict, List, Optional, Union

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
)
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel, Field

# Google Gemini
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)

# OpenAI
from langchain_openai import (
    ChatOpenAI,
    OpenAIEmbeddings,
)

from bot.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """استجابة LLM موحدة"""
    response: str
    model: str
    provider: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    finish_reason: str = "stop"


class LLMClient:
    """
    عميل LLM متعدد المزودين
    يدعم Google Gemini و OpenAI
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._llm: Optional[Union[ChatGoogleGenerativeAI, ChatOpenAI]] = None
        self._embeddings: Optional[Union[GoogleGenerativeAIEmbeddings, OpenAIEmbeddings]] = None
    
    @property
    def llm(self) -> Union[ChatGoogleGenerativeAI, ChatOpenAI]:
        """Lazy initialization لـ LLM"""
        if self._llm is None:
            if self.settings.llm_provider == "gemini":
                self._llm = ChatGoogleGenerativeAI(
                    model=self.settings.gemini_model,
                    temperature=self.settings.llm_temperature,
                    max_output_tokens=self.settings.llm_max_tokens,
                    timeout=self.settings.llm_timeout,
                    api_key=self.settings.google_api_key,
                )
                logger.info(
                    f"Initialized ChatGoogleGenerativeAI: "
                    f"model={self.settings.gemini_model}"
                )
            else:  # openai
                self._llm = ChatOpenAI(
                    model=self.settings.openai_model,
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                    timeout=self.settings.llm_timeout,
                    api_key=self.settings.openai_api_key,
                )
                logger.info(
                    f"Initialized ChatOpenAI: model={self.settings.openai_model}"
                )
        return self._llm
    
    @property
    def embeddings(self) -> Union[GoogleGenerativeAIEmbeddings, OpenAIEmbeddings]:
        """Lazy initialization لـ Embeddings"""
        if self._embeddings is None:
            if self.settings.llm_provider == "gemini":
                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model=self.settings.gemini_embedding_model,
                    api_key=self.settings.google_api_key,
                )
                logger.info(
                    f"Initialized GoogleGenerativeAIEmbeddings: "
                    f"model={self.settings.gemini_embedding_model}"
                )
            else:  # openai
                self._embeddings = OpenAIEmbeddings(
                    model=self.settings.openai_embedding_model,
                    api_key=self.settings.openai_api_key,
                )
                logger.info(
                    f"Initialized OpenAIEmbeddings: "
                    f"model={self.settings.openai_embedding_model}"
                )
        return self._embeddings
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[BaseMessage]:
        """تحويل الرسائل من Dict إلى BaseMessage"""
        result = []
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                result.append(HumanMessage(content=content))
            elif role == "assistant":
                result.append(AIMessage(content=content))
            else:
                logger.warning(f"Unknown role: {role}, treating as user")
                result.append(HumanMessage(content=content))
        
        return result
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        توليد رد من LLM
        
        Args:
            messages: قائمة الرسائل [{role, content}, ...]
            temperature: درجة الحرارة (اختياري)
            max_tokens: الحد الأقصى للتوكنات (اختياري)
        
        Returns:
            LLMResponse يحتوي على الرد والمعلومات
        """
        try:
            start_time = time.time()
            
            # إنشاء LLM مع إعدادات مخصصة إذا تم تمريرها
            llm = self.llm
            if temperature is not None or max_tokens is not None:
                if self.settings.llm_provider == "gemini":
                    llm = ChatGoogleGenerativeAI(
                        model=self.settings.gemini_model,
                        temperature=temperature or self.settings.llm_temperature,
                        max_output_tokens=max_tokens or self.settings.llm_max_tokens,
                        api_key=self.settings.google_api_key,
                    )
                else:  # openai
                    llm = ChatOpenAI(
                        model=self.settings.openai_model,
                        temperature=temperature or self.settings.llm_temperature,
                        max_tokens=max_tokens or self.settings.llm_max_tokens,
                        api_key=self.settings.openai_api_key,
                    )
            
            # تحويل الرسائل
            lc_messages = self._convert_messages(messages)
            
            # استدعاء LLM
            response = await llm.ainvoke(lc_messages)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # استخراج معلومات الاستخدام
            tokens_input = 0
            tokens_output = 0
            finish_reason = "stop"
            
            if hasattr(response, "response_metadata") and response.response_metadata:
                usage = response.response_metadata.get("token_usage", {})
                tokens_input = usage.get("prompt_tokens", 0)
                tokens_output = usage.get("completion_tokens", 0)
                finish_reason = response.response_metadata.get("finish_reason", "stop")
            
            return LLMResponse(
                response=response.content if isinstance(response.content, str) else str(response.content),
                model=self.settings.active_model,
                provider=self.settings.llm_provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                finish_reason=finish_reason,
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            return LLMResponse(
                response="عذراً، حصل خطأ تقني. الرجاء المحاولة لاحقاً.",
                model=self.settings.active_model,
                provider=self.settings.llm_provider,
                tokens_input=0,
                tokens_output=0,
                latency_ms=0,
                finish_reason="error",
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        توليد embedding لنص واحد
        
        Args:
            text: النص المراد تحويله لـ embedding
        
        Returns:
            List[float] من الأبعاد
        """
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            # Gemini: 768 dim, OpenAI: 1536 dim
            return [0.0] * (768 if self.settings.llm_provider == "gemini" else 1536)
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        توليد embeddings لمجموعة نصوص
        
        Args:
            texts: قائمة النصوص
        
        Returns:
            List[List[float]] من الـ embeddings
        """
        try:
            embeddings = await self.embeddings.aembed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}", exc_info=True)
            dim = 768 if self.settings.llm_provider == "gemini" else 1536
            return [[0.0] * dim for _ in texts]
    
    def get_llm_chain(self, prompt: str) -> Runnable:
        """
        إنشاء سلسلة LLM بسيطة باستخدام LCEL
        
        Args:
            prompt: قالب الـ prompt
        
        Returns:
            Runnable سلسلة جاهزة للاستخدام
        """
        from langchain_core.prompts import ChatPromptTemplate
        
        prompt_template = ChatPromptTemplate.from_template(prompt)
        return prompt_template | self.llm | StrOutputParser()
