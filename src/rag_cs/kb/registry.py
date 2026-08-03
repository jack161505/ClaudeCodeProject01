"""知识库元数据读写（kb_meta.json）。

单用户场景：读-改-写，不加锁。身份（id/slug/collection_name）在此生成；
向量 CRUD 由 vectorstore 负责，本模块不依赖 chroma。
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from rag_cs.config import Settings, get_settings
from rag_cs.exceptions import RagCsError
from rag_cs.kb.models import DocumentRecord, KbMetaFile, KnowledgeBase


class KnowledgeBaseNotFound(RagCsError):
    """按 id 未找到知识库。"""

    def __init__(self, kb_id: str) -> None:
        super().__init__(f"知识库不存在: {kb_id}")
        self.kb_id = kb_id


def _slugify(name: str, kb_id: str) -> str:
    """把名称转成 ASCII 安全的 slug，并追加短 id 保证唯一。

    Chroma collection 名仅允许字母数字/下划线/连字符，且须 3-63 字符；
    中文等非 ASCII 会被替换，纯非 ASCII 名称回退为短 id。
    """
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()[:40]
    short_id = kb_id[:8]
    return f"{ascii_part}_{short_id}" if ascii_part else short_id


class KBMetaStore:
    """知识库元数据存储：CRUD + 文档登记。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._s = settings or get_settings()

    def list_kbs(self) -> list[KnowledgeBase]:
        """列出全部知识库。"""
        return self._load().knowledge_bases

    def get(self, kb_id: str) -> KnowledgeBase | None:
        """按 id 取知识库；不存在返回 None。"""
        return self._find(self._load(), kb_id)

    def create(self, name: str, description: str = "") -> KnowledgeBase:
        """新建知识库，生成 id/slug/collection_name 并持久化。"""
        data = self._load()
        kb_id = uuid4().hex
        slug = _slugify(name, kb_id)
        kb = KnowledgeBase(
            id=kb_id,
            name=name,
            slug=slug,
            description=description,
            collection_name=f"kb_{slug}",
            created_at=datetime.now(UTC).isoformat(),
        )
        data.knowledge_bases.append(kb)
        self._save(data)
        return kb

    def delete(self, kb_id: str) -> KnowledgeBase | None:
        """删除知识库；返回被删除的 KB（供调用方 drop 对应 collection），不存在返回 None。"""
        data = self._load()
        for i, kb in enumerate(data.knowledge_bases):
            if kb.id == kb_id:
                removed = data.knowledge_bases.pop(i)
                self._save(data)
                return removed
        return None

    def register_document(self, kb_id: str, source: str, chunk_count: int) -> None:
        """登记一份已入库文档；同名文档重新入库则更新 chunk_count。"""
        data = self._load()
        kb = self._find(data, kb_id)
        if kb is None:
            raise KnowledgeBaseNotFound(kb_id)
        now = datetime.now(UTC).isoformat()
        for doc in kb.documents:
            if doc.source == source:
                doc.chunk_count = chunk_count
                doc.ingested_at = now
                self._save(data)
                return
        kb.documents.append(DocumentRecord(source=source, chunk_count=chunk_count, ingested_at=now))
        self._save(data)

    def unregister_document(self, kb_id: str, source: str) -> None:
        """移除一份文档登记（不删向量；向量删除由 vectorstore 按 metadata 处理）。"""
        data = self._load()
        kb = self._find(data, kb_id)
        if kb is None:
            raise KnowledgeBaseNotFound(kb_id)
        kb.documents = [d for d in kb.documents if d.source != source]
        self._save(data)

    def _load(self) -> KbMetaFile:
        path = Path(self._s.kb_meta_path)
        if not path.exists():
            return KbMetaFile()
        return KbMetaFile.model_validate_json(path.read_text(encoding="utf-8"))

    def _save(self, data: KbMetaFile) -> None:
        path = Path(self._s.kb_meta_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def _find(data: KbMetaFile, kb_id: str) -> KnowledgeBase | None:
        for kb in data.knowledge_bases:
            if kb.id == kb_id:
                return kb
        return None
