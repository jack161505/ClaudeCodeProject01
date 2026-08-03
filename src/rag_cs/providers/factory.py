"""按配置构造 chat 模型与 embeddings。

chat 与 embedding 独立路由：例如 chat 走 Ollama、embedding 走 OpenAI。
"""

from typing import assert_never

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from rag_cs.config import ChatProvider, EmbeddingProvider, Settings, get_settings
from rag_cs.providers import ollama_provider, openai_provider, xinference_provider


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """按 chat_provider 配置返回对应的 chat 模型。"""
    s = settings or get_settings()
    p = s.chat_provider
    if p is ChatProvider.OPENAI:
        return openai_provider.get_chat_model(s)
    if p is ChatProvider.OLLAMA:
        return ollama_provider.get_chat_model(s)
    if p is ChatProvider.XINFERENCE:
        return xinference_provider.get_chat_model(s)
    assert_never(p)


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    """按 embedding_provider 配置返回对应的 embedding 模型。"""
    s = settings or get_settings()
    p = s.embedding_provider
    if p is EmbeddingProvider.OPENAI:
        return openai_provider.get_embeddings(s)
    if p is EmbeddingProvider.OLLAMA:
        return ollama_provider.get_embeddings(s)
    if p is EmbeddingProvider.XINFERENCE:
        return xinference_provider.get_embeddings(s)
    assert_never(p)
