"""Application settings and environment configuration."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database
    DATABASE_URL: Optional[str] = Field(default=None)
    CHECKPOINT_DATABASE_URL: Optional[str] = Field(default=None)
    CHECKPOINTER: str = Field(default="postgres")  # 'postgres' or 'memory'

    # Groq LLM
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="openai/gpt-oss-20b")

    # Browser & Automation
    BROWSER_MODE: str = Field(default="local")  # 'local' or 'browserbase'
    BROWSERBASE_API_KEY: Optional[str] = Field(default=None)
    BROWSERBASE_PROJECT_ID: Optional[str] = Field(default=None)
    BROWSERBASE_REGION: str = Field(default="ap-southeast-1")
    PORTAL_BASE_URL: str = Field(default="http://localhost:3000")

    # Execution limits & timeouts
    FETCH_MODE: str = Field(default="agent")  # 'agent' or 'deterministic'
    MAX_AGENT_STEPS: int = Field(default=15)
    CAPTCHA_TIMEOUT_SECONDS: int = Field(default=120)

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:3000")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def direct_checkpoint_url(self) -> Optional[str]:
        """Derives direct Postgres URL for LangGraph checkpointer by stripping '-pooler'."""
        url = self.CHECKPOINT_DATABASE_URL or self.DATABASE_URL
        if url:
            # Neon requires direct connection (no PgBouncer pooler) for checkpoints
            return url.replace("-pooler", "")
        return None

settings = Settings()
