from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multi Agent Financial Research System"
    database_url: str = "sqlite:///./financial_research.db"
    upload_dir: str = "../data/uploads"
    chroma_dir: str = "../data/chroma"
    max_file_size_mb: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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