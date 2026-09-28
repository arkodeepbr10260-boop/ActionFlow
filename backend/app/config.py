import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ActionFlow API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # AWS / Bedrock Settings
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    
    # CORS & Web
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "actionflow.db")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
