from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.python"),   # ← .env для локали, .env.python для контейнера
        env_file_encoding="utf-8",
        extra="ignore",                     # ← ОБЯЗАТЕЛЬНО: в env-файле больше ключей, чем полей
        validate_by_name=True,
        case_sensitive=False,
        env_ignore_empty=True,
    )

    # --- RabbitMQ ---
    host: str = Field("rabbitmq", alias="RABBITMQ_HOST")
    port: int = Field(5672, ge=1, le=65535, alias="RABBITMQ_PORT")
    user: str = Field("guest", alias="RABBITMQ_USER")
    password: SecretStr = Field(SecretStr("guest"), alias="RABBITMQ_PASS")
    request_queue: str = Field("request_queue", alias="RABBITMQ_REQUEST_QUEUE")
    response_queue: str = Field("response_queue", alias="RABBITMQ_RESPONSE_QUEUE")
    prefetch: int = Field(7, ge=1, le=64, alias="RABBITMQ_PREFETCH")

    # --- Qwen / vLLM ---
    qwen_text_model: str = Field(..., alias="QWEN_TEXT_MODEL")
    qwen_text_url: str = Field(..., alias="QWEN_TEXT_URL")
    qwen_pict_model: str = Field(..., alias="QWEN_PICT_MODEL")
    qwen_pict_url: str = Field(..., alias="QWEN_PICT_URL")
    llm_timeout: float = Field(120.0, gt=0, alias="LLM_TIMEOUT")
    llm_max_tokens: int = Field(500, ge=1, alias="LLM_MAX_TOKENS")
    llm_retries: int = Field(1, ge=0, le=5, alias="LLM_RETRIES")

    # --- Redis (память последнего фото) ---
    redis_url: str = Field("redis://redis:6379/2", alias="REDIS_URL")
    redis_socket_timeout: float = Field(2.0, gt=0, alias="REDIS_SOCKET_TIMEOUT")
    image_ttl: int = Field(3600, ge=60, alias="IMAGE_TTL")            # сек, 1 час
    image_max_bytes: int = Field(10 * 1024 * 1024, ge=1024, alias="IMAGE_MAX_BYTES")
    image_max_side: int = Field(600, ge=64, le=2048, alias="IMAGE_MAX_SIDE")
    image_jpeg_quality: int = Field(75, ge=40, le=95, alias="IMAGE_JPEG_QUALITY")
    image_fetch_timeout: float = Field(20.0, gt=0, alias="IMAGE_FETCH_TIMEOUT")

    @field_validator("redis_url")
    @classmethod
    def _check_redis(cls, v: str) -> str:
        if not v.startswith(("redis://", "rediss://", "unix://")):
            raise ValueError("REDIS_URL должен начинаться с redis:// или rediss://")
        return v

    @field_validator("qwen_text_url", "qwen_pict_url")
    @classmethod
    def _check_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL модели должен начинаться с http(s)://")
        return v.rstrip("/")


settings = Settings()

# --- RabbitMQ ---
RABBITMQ_HOST = settings.host
RABBITMQ_PORT = settings.port
RABBITMQ_USER = settings.user
RABBITMQ_PASS = settings.password.get_secret_value()   # ← SecretStr, наружу отдаём строку
RABBITMQ_REQUEST_QUEUE = settings.request_queue
RABBITMQ_RESPONSE_QUEUE = settings.response_queue
RABBITMQ_PREFETCH = settings.prefetch

# --- Qwen / vLLM ---
QWEN_TEXT_MODEL = settings.qwen_text_model
QWEN_TEXT_URL = settings.qwen_text_url
QWEN_PICT_MODEL = settings.qwen_pict_model
QWEN_PICT_URL = settings.qwen_pict_url
LLM_TIMEOUT = settings.llm_timeout
LLM_MAX_TOKENS = settings.llm_max_tokens
LLM_RETRIES = settings.llm_retries

# --- Redis / изображения ---
REDIS_URL = settings.redis_url
REDIS_SOCKET_TIMEOUT = settings.redis_socket_timeout
IMAGE_TTL = settings.image_ttl
IMAGE_MAX_BYTES = settings.image_max_bytes
IMAGE_MAX_SIDE = settings.image_max_side
IMAGE_JPEG_QUALITY = settings.image_jpeg_quality
IMAGE_FETCH_TIMEOUT = settings.image_fetch_timeout
