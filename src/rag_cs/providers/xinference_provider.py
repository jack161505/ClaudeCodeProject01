"""Xinference 平台的 chat 模型与 embedding 构造。

Xinference 暴露 OpenAI 兼容接口，故复用 langchain_openai 的客户端，
仅把 base_url 指向 Xinference 服务（默认 http://localhost:9997/v1）。
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from rag_cs.config import Settings


def _base_url(s: Settings) -> str:
    """Xinference 的 OpenAI 兼容 endpoint。"""
    return f"{s.xinference_base_url}/v1"


def _api_key(s: Settings) -> SecretStr:
    """Xinference 不校验 key，但客户端要求非空；有 OpenAI key 就复用，否则占位。"""
    return SecretStr(s.openai_api_key or "xinference")


def get_chat_model(s: Settings) -> ChatOpenAI:
    """构造 Xinference chat 模型（经 OpenAI 兼容接口）。"""
    return ChatOpenAI(model=s.chat_model, base_url=_base_url(s), api_key=_api_key(s))


def get_embeddings(s: Settings) -> OpenAIEmbeddings:
    """构造 Xinference embedding 模型。"""
    return OpenAIEmbeddings(model=s.embedding_model, base_url=_base_url(s), api_key=_api_key(s))
