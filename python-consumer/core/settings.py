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
    url: str = Field(
        alias="OLLAMA_BASE_URL",
        description="url для ollama llm, llm_food"
        )
    qwen_model: str = Field(
        alias = "QWEEN_VL_MODEL",
        description = "qween модель"
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
OLLAMA_BASE_URL = settings.url
QWEEN_VL_MODEL = settings.qwen_model
