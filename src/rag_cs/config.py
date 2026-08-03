"""全局配置。

从环境变量与 .env 文件加载所有可配置项。chat 与 embedding 独立配置，
例如 chat 走本地 Ollama、embedding 仍走 OpenAI（默认）。
"""

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatProvider(StrEnum):
    """Chat 模型提供方。"""

    OPENAI = "openai"
    OLLAMA = "ollama"
    XINFERENCE = "xinference"


class EmbeddingProvider(StrEnum):
    """Embedding 模型提供方。"""

    OPENAI = "openai"
    OLLAMA = "ollama"
    XINFERENCE = "xinference"


class Settings(BaseSettings):
    """应用配置。

    字段名与环境变量名对应（不区分大小写），详见 .env.example。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Chat 模型 ---
    chat_provider: ChatProvider = ChatProvider.OPENAI
    chat_model: str = "gpt-4o-mini"

    # --- Embedding 模型（默认 OpenAI）---
    embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    embedding_model: str = "text-embedding-3-small"

    # --- 平台凭证 / endpoint ---
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    xinference_base_url: str = "http://localhost:9997"

    # --- Chroma / 数据 ---
    chroma_dir: str = "data/chroma"
    kb_meta_path: str = "data/kb_meta.json"

    # --- 切分 ---
    chunk_size: int = 500
    chunk_overlap: int = 50

    # --- 检索 ---
    retrieval_top_k: int = 4


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回单例 Settings，避免重复解析 .env。"""
    return Settings()
