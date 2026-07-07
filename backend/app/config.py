from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    nvidia_api_key: str | None = None
    nvidia_model: str = "meta/llama-3.2-90b-vision-instruct"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    
    openrouter_api_key: str | None = None
    openrouter_model: str = "nvidia/nemotron-nano-12b-v2-vl:free"
    
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_url: str = "http://localhost:3000"
    max_file_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
