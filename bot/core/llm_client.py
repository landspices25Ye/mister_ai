# Mister AI - LLM Client
# bot/core/llm_client.py

"""
عميل LLM مع دعم متعدد النماذج
"""

import os
import logging
from typing import Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class LLMResponse(BaseModel):
    response: str
    model: str
    tokens_input: int
    tokens_output: int
    latency_ms: int

class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> LLMResponse:
        """توليد رد من LLM"""
        model = model or self.default_model
        
        try:
            import time
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            latency = int((time.time() - start_time) * 1000)
            
            return LLMResponse(
                response=response.choices[0].message.content.strip(),
                model=model,
                tokens_input=response.usage.prompt_tokens,
                tokens_output=response.usage.completion_tokens,
                latency_ms=latency
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return LLMResponse(
                response="عذراً، حصل خطأ تقني. الرجاء المحاولة لاحقاً.",
                model=model,
                tokens_input=0,
                tokens_output=0,
                latency_ms=0
            )