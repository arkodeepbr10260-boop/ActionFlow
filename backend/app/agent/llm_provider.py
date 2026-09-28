import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import boto3
from app.config import settings

logger = logging.getLogger("actionflow.llm")

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def is_live(self) -> bool:
        pass

class BedrockProvider(LLMProvider):
    def __init__(self):
        self.model_id = settings.BEDROCK_MODEL_ID
        self.region = settings.AWS_REGION
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            kwargs = {"region_name": self.region}
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            self._client = boto3.client("bedrock-runtime", **kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize AWS Bedrock client: {e}")
            self._client = None

    def is_live(self) -> bool:
        return self._client is not None and bool(settings.AWS_ACCESS_KEY_ID or os.getenv("AWS_PROFILE"))

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self._client:
            raise RuntimeError("Bedrock client is not initialized. Please set AWS credentials.")
        
        system = [{"text": system_prompt}] if system_prompt else []
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        try:
            response = self._client.converse(
                modelId=self.model_id,
                messages=messages,
                system=system,
                inferenceConfig={"temperature": 0.2, "maxTokens": 1000}
            )
            output_text = response["output"]["message"]["content"][0]["text"]
            return output_text
        except Exception as e:
            logger.error(f"Bedrock converse call failed: {e}")
            raise e

class MockBedrockProvider(LLMProvider):
    def is_live(self) -> bool:
        return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        prompt_lower = prompt.lower()
        
        if "plan my evening after college" in prompt_lower or "college" in prompt_lower:
            return json.dumps({
                "understood_goal": "Plan an evening outing after college including weather check, place search, and reminder.",
                "tools_needed": ["get_weather", "search_places", "generate_plan", "create_reminder"],
                "location": "Campus Town",
                "activity_query": "lounge or coffee shop",
                "reminder_title": "Evening College Outing",
                "reminder_time": "6:00 PM"
            })
        elif "tomorrow" in prompt_lower:
            return json.dumps({
                "understood_goal": "Check weather and plan activities for tomorrow based on previous college evening preferences.",
                "tools_needed": ["get_weather", "search_places", "generate_plan"],
                "location": "Campus Town",
                "activity_query": "outdoor park or bistro",
                "reminder_title": "Tomorrow Evening Plan",
                "reminder_time": "5:30 PM"
            })
        else:
            return json.dumps({
                "understood_goal": prompt,
                "tools_needed": ["get_weather", "search_places", "generate_plan"],
                "location": "Downtown",
                "activity_query": "popular spots",
                "reminder_title": "General Task",
                "reminder_time": "6:00 PM"
            })

import os

def get_llm_provider() -> LLMProvider:
    # Check if real AWS credentials or AWS_PROFILE exist
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        try:
            provider = BedrockProvider()
            return provider
        except Exception:
            pass
    # Fallback to clear, structured mock provider for offline/local testing
    return MockBedrockProvider()
