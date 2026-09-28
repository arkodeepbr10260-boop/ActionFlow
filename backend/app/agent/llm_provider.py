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
            # If explicit keys are provided in settings, use them; otherwise let boto3 resolve via standard AWS chain
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            self._client = boto3.client("bedrock-runtime", **kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize AWS Bedrock client: {e}")
            self._client = None

    def is_live(self) -> bool:
        if not self._client or not self.model_id:
            return False
        # If client was initialized with explicit keys or credentials exist in boto3 session
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except Exception:
            return bool(settings.AWS_ACCESS_KEY_ID or os.getenv("AWS_PROFILE"))

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
        
        # Check follow-up queries first so context carrying "college" does not shadow "tomorrow"
        if "tomorrow" in prompt_lower:
            return json.dumps({
                "goal": "Check weather and plan activities for tomorrow based on previous college evening preferences.",
                "tasks": [
                    {"tool": "get_weather", "arguments": {"location": "Campus Town", "date": "Tomorrow"}},
                    {"tool": "search_places", "arguments": {"query": "nearby lounge or coffee shop", "location": "Campus Town"}},
                    {"tool": "generate_plan", "arguments": {"user_goal": "What about tomorrow?"}}
                ],
                "requires_confirmation": False
            })
        elif "plan my evening after college" in prompt_lower or "college" in prompt_lower:
            return json.dumps({
                "goal": "Plan an evening outing after college including weather check, place search, and reminder.",
                "tasks": [
                    {"tool": "get_weather", "arguments": {"location": "Campus Town", "date": "Today"}},
                    {"tool": "search_places", "arguments": {"query": "nearby lounge or coffee shop", "location": "Campus Town"}},
                    {"tool": "generate_plan", "arguments": {"user_goal": prompt}},
                    {"tool": "create_reminder", "arguments": {"title": "Evening Activity: Campus Lounge", "datetime_str": "6:00 PM"}}
                ],
                "requires_confirmation": True
            })
        else:
            return json.dumps({
                "goal": prompt,
                "tasks": [
                    {"tool": "get_weather", "arguments": {"location": "Campus Town", "date": "Today"}},
                    {"tool": "search_places", "arguments": {"query": "popular spots", "location": "Campus Town"}},
                    {"tool": "generate_plan", "arguments": {"user_goal": prompt}}
                ],
                "requires_confirmation": False
            })

import os

def get_llm_provider() -> LLMProvider:
    # Attempt live BedrockProvider if model ID is configured
    if settings.BEDROCK_MODEL_ID:
        try:
            provider = BedrockProvider()
            if provider.is_live():
                logger.info(f"Using live AWS BedrockProvider with model: {settings.BEDROCK_MODEL_ID}")
                return provider
        except Exception as e:
            logger.warning(f"Error checking BedrockProvider: {e}")
            pass
    logger.info("Using offline MockBedrockProvider (development mode)")
    return MockBedrockProvider()
