import os
from typing import ClassVar
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    PERPLEXITY_API_KEY: str
    PERPLEXITY_API_URL: str = "https://api.perplexity.ai/chat/completions"
    PERPLEXITY_DEFAULT_MODEL: str = "sonar-pro"
    PERPLEXITY_TIMEOUT: float = 60.0

    GIGACHAT_AUTH_KEY: str | None = None
    GIGACHAT_OAUTH_URL: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"
    GIGACHAT_API_BASE_URL: str = "https://gigachat.devices.sberbank.ru/api/v1"
    GIGACHAT_DEFAULT_MODEL: str = "GigaChat-2"
    GIGACHAT_TIMEOUT: float = 60.0
    GIGACHAT_VERIFY_SSL: bool = False

    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_EXTENSIONS: list[str] = [
        ".pdf", ".txt", ".pptx"
        ".doc", ".docx",
    ]

    MAX_TEXT_CHARS: int = 200_000

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    FILE_MIME_TYPES: ClassVar[dict[str, str]] = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_upload_dir_exists()

    def _ensure_upload_dir_exists(self) -> None:
        upload_path = Path(self.UPLOAD_DIR)
        upload_path.mkdir(exist_ok=True, parents=True)

    @property
    def async_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def upload_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    def is_file_extension_allowed(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in self.ALLOWED_FILE_EXTENSIONS

    def validate_file_size(self, size_bytes: int) -> bool:
        return size_bytes <= self.max_file_size_bytes

    def get_mime_type(self, filename: str) -> str | None:
        ext = Path(filename).suffix.lower()
        return self.FILE_MIME_TYPES.get(ext)

settings = Settings()