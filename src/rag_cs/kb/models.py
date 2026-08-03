"""知识库元数据模型。

用 pydantic BaseModel 建模，便于与 kb_meta.json 互序列化。
document_count / chunk_count 由 documents 列表派生，不单独持久化。
"""

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    """知识库内一份已入库文档的记录。"""

    source: str  # 原始文件名
    chunk_count: int
    ingested_at: str  # ISO8601 时间戳


class KnowledgeBase(BaseModel):
    """一个知识库的元数据。

    collection_name 由 slug 派生，是 Chroma 中的集合名；与向量库解耦：
    本模型只描述"是什么"，向量 CRUD 由 vectorstore 负责。
    """

    id: str
    name: str
    slug: str
    description: str
    collection_name: str
    created_at: str  # ISO8601 时间戳
    documents: list[DocumentRecord] = Field(default_factory=list)

    @property
    def document_count(self) -> int:
        return len(self.documents)

    @property
    def chunk_count(self) -> int:
        return sum(d.chunk_count for d in self.documents)


class KbMetaFile(BaseModel):
    """kb_meta.json 的整体结构。"""

    knowledge_bases: list[KnowledgeBase] = Field(default_factory=list)
