"""OpenAI 平台的 chat 模型与 embedding 构造。"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from rag_cs.config import Settings


def _api_key(s: Settings) -> SecretStr | None:
    """把配置中的明文 key 包成 SecretStr；为 None 时返回 None 以走环境变量回退。"""
    return SecretStr(s.openai_api_key) if s.openai_api_key else None


def get_chat_model(s: Settings) -> ChatOpenAI:
    """构造 OpenAI chat 模型。"""
    return ChatOpenAI(model=s.chat_model, api_key=_api_key(s))


def get_embeddings(s: Settings) -> OpenAIEmbeddings:
    """构造 OpenAI embedding 模型。"""
    return OpenAIEmbeddings(model=s.embedding_model, api_key=_api_key(s))
