"""文档入库流水线：清洗 -> 切分 -> 向量化入库 -> 登记元数据。"""

from rag_cs.config import Settings, get_settings
from rag_cs.ingestion.loader import load_markdown
from rag_cs.ingestion.splitter import split_document
from rag_cs.kb.registry import KBMetaStore, KnowledgeBaseNotFound
from rag_cs.vectorstore.store import VectorStoreService


class IngestionPipeline:
    """编排文档入库：切分后写入向量库并登记到知识库元数据。"""

    def __init__(
        self,
        vstore: VectorStoreService | None = None,
        registry: KBMetaStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._s = settings or get_settings()
        self._vstore = vstore or VectorStoreService(self._s)
        self._registry = registry or KBMetaStore(self._s)

    def ingest(self, kb_id: str, filename: str, markdown_text: str) -> int:
        """入库一份 Markdown 文档，返回实际写入的 chunk 数。

        重新入库同名文档时，先按 source 清除旧 chunk 再写入，避免残留。

        Args:
            kb_id: 目标知识库 id。
            filename: 原始文件名（写入 source 元数据）。
            markdown_text: Markdown 原文。

        Returns:
            实际写入的 chunk 数。

        Raises:
            KnowledgeBaseNotFound: kb_id 不存在。
        """
        kb = self._registry.get(kb_id)
        if kb is None:
            raise KnowledgeBaseNotFound(kb_id)

        chunks = split_document(
            text=load_markdown(markdown_text),
            source=filename,
            kb_id=kb_id,
            chunk_size=self._s.chunk_size,
            chunk_overlap=self._s.chunk_overlap,
        )

        # 重新入库：先清掉该 source 的旧 chunk（首次入库为空操作）
        self._vstore.delete_by_metadata(kb.collection_name, {"source": filename})

        if not chunks:
            self._registry.register_document(kb_id, filename, chunk_count=0)
            return 0

        texts = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]
        ids = [f"{kb_id}:{filename}:{i}" for i in range(len(chunks))]
        self._vstore.add(kb.collection_name, texts, metadatas, ids)
        self._registry.register_document(kb_id, filename, chunk_count=len(chunks))
        return len(chunks)
