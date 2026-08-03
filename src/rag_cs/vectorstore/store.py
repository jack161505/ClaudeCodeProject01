"""Chroma 向量库封装。

一个知识库对应一个 collection（命名 kb_{slug}），按集合隔离增删查。
跨库检索时对各 collection 分别查询，再按距离（L2，越小越相关）合并排序。

embedding 由本服务经 providers 统一计算后显式传入，不让 Chroma 用其默认模型，
保证入库与检索的 embedding 路由与配置一致。
"""

import contextlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import chromadb
from chromadb.api.types import Embeddings, Metadata, QueryResult, Where
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

from rag_cs.config import Settings, get_settings
from rag_cs.providers.factory import get_embeddings

# 批量 embedding 上限，避免单次请求 token 数过大
_EMBED_BATCH_SIZE = 64


@dataclass
class SearchHit:
    """单条检索命中。

    Attributes:
        content: 命中的文本片段。
        metadata: 入库时写入的元数据（来源、header 路径、chunk 序号等）。
        score: Chroma L2 距离，越小越相关。
        collection: 命中所在 collection 名。
    """

    content: str
    metadata: Metadata
    score: float
    collection: str


class VectorStoreService:
    """Chroma 向量库服务：按集合隔离的增删查。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._s = settings or get_settings()
        self._client = chromadb.PersistentClient(
            path=self._s.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embeddings = get_embeddings(self._s)

    def ensure_collection(self, name: str) -> None:
        """确保集合存在（不存在则创建）。"""
        self._client.get_or_create_collection(name=name)

    def collection_exists(self, name: str) -> bool:
        """集合是否存在。"""
        try:
            self._client.get_collection(name=name)
        except (ValueError, NotFoundError):
            return False
        return True

    def drop_collection(self, name: str) -> None:
        """删除集合；不存在则忽略。"""
        with contextlib.suppress(ValueError, NotFoundError):
            self._client.delete_collection(name=name)

    def add(
        self,
        collection: str,
        texts: list[str],
        metadatas: list[Metadata],
        ids: list[str],
    ) -> None:
        """批量入库；embedding 由本服务计算后显式传入。

        Args:
            collection: 目标集合名。
            texts: 文本片段。
            metadatas: 与 texts 逐项对应的元数据。
            ids: 与 texts 逐项对应的唯一 id。

        Raises:
            ValueError: texts / metadatas / ids 长度不一致。
        """
        if not (len(texts) == len(metadatas) == len(ids)):
            raise ValueError("texts / metadatas / ids 长度须一致")
        if not texts:
            return
        coll = self._client.get_or_create_collection(name=collection)
        # chromadb 的 Embeddings 类型是含 ndarray 的联合，list[list[float]] 因 List 不变
        # 无法直接匹配，此处显式断言为我们算出的向量。
        coll.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
            embeddings=cast(Embeddings, self._embed(texts)),
        )

    def delete(self, collection: str, ids: list[str]) -> None:
        """按 id 删除文档；集合不存在则忽略。"""
        if not ids or not self.collection_exists(collection):
            return
        coll = self._client.get_collection(name=collection)
        coll.delete(ids=ids)

    def delete_by_metadata(
        self,
        collection: str,
        where: Mapping[str, str | int | float | bool],
    ) -> None:
        """按 metadata 过滤删除文档（用于重新入库或删除单文件）；集合不存在则忽略。"""
        if not self.collection_exists(collection):
            return
        coll = self._client.get_collection(name=collection)
        coll.delete(where=cast(Where, dict(where)))

    def search(
        self,
        collections: list[str],
        query: str,
        top_k: int,
    ) -> list[SearchHit]:
        """跨多个 collection 检索，合并后按距离升序取前 top_k。

        不存在的 collection 会被跳过（不报错），便于上层按启用列表直接传入。
        """
        if not collections or top_k <= 0:
            return []
        query_embedding = self._embeddings.embed_query(query)
        hits: list[SearchHit] = []
        for name in collections:
            if not self.collection_exists(name):
                continue
            coll = self._client.get_collection(name=name)
            result = coll.query(
                query_embeddings=cast(Embeddings, [query_embedding]),
                n_results=top_k,
            )
            hits.extend(_parse_query_result(result, name))
        hits.sort(key=lambda h: h.score)
        return hits[:top_k]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """分批计算 embedding，避免单次请求过大。"""
        out: list[list[float]] = []
        for i in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[i : i + _EMBED_BATCH_SIZE]
            out.extend(self._embeddings.embed_documents(batch))
        return out


def _parse_query_result(result: QueryResult, collection: str) -> list[SearchHit]:
    """解析单条 query 的结果（外层 query 维度恒为 1）。"""
    documents = result.get("documents")
    if not documents or not documents[0]:
        return []
    docs = documents[0]
    metadatas = result.get("metadatas")
    distances = result.get("distances")
    metas = metadatas[0] if metadatas else [None] * len(docs)
    dists = distances[0] if distances else [0.0] * len(docs)
    hits: list[SearchHit] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else None
        dist = dists[i] if i < len(dists) else 0.0
        hits.append(
            SearchHit(
                content=doc,
                metadata=meta or {},
                score=dist,
                collection=collection,
            )
        )
    return hits
