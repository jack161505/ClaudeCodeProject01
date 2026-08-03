"""Ollama 平台的 chat 模型与 embedding 构造（本地推理）。"""

from langchain_ollama import ChatOllama, OllamaEmbeddings

from rag_cs.config import Settings


def get_chat_model(s: Settings) -> ChatOllama:
    """构造 Ollama chat 模型。"""
    return ChatOllama(model=s.chat_model, base_url=s.ollama_base_url)


def get_embeddings(s: Settings) -> OllamaEmbeddings:
    """构造 Ollama embedding 模型。"""
    return OllamaEmbeddings(model=s.embedding_model, base_url=s.ollama_base_url)
