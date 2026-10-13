from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multi Agent Financial Research System"
    database_url: str = "sqlite:///./financial_research.db"
    upload_dir: str = "../data/uploads"
    chroma_dir: str = "../data/chroma"
    max_file_size_mb: int = 30

    # OpenAI is optional.
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0

    # Research provider choices: auto, openai, ollama, fallback
    research_provider: str = "auto"

    # Local Ollama configuration.
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()