from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    host: str = Field(
        alias="RABBITMQ_HOST",
        description="хост rabbitmq"
    )
    port: int = Field(
        alias="RABBITMQ_PORT",
        description="порт rabbitmq"
        )
    user: str = Field(
        alias="RABBITMQ_USER",
        description="user для rabbitmq"
        )
    password: str = Field(
        alias="RABBITMQ_PASS",
        description="pass для rabbitmq"
        )
    qwen_text_model: str = Field(
        alias = "QWEN_TEXT_MODEL",
        description = "qwen модель для текста"
    )
    qwen_pict_model: str = Field(
        alias = "QWEN_PICT_MODEL",
        description = "qwen модель для картинок"
    )
    qwen_text_url: str = Field(
        alias = "QWEN_TEXT_URL",
        description = "qwen url для анализа текста"
    )
    qwen_pict_url: str = Field(
        alias = "QWEN_PICT_URL",
        description = "qwen url для анализа картинки"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True

settings = Settings()

RABBITMQ_HOST = settings.host
RABBITMQ_PORT = settings.port
RABBITMQ_USER = settings.user
RABBITMQ_PASS = settings.password

QWEN_PICT_MODEL=settings.qwen_pict_model
QWEN_PICT_URL=settings.qwen_pict_url

QWEN_TEXT_URL=settings.qwen_text_url
QWEN_TEXT_MODEL=settings.qwen_text_model
