"""Markdown 切分：先按标题层级，再按长度递归切分。

两段式：MarkdownHeaderTextSplitter 保留标题路径到 metadata，
RecursiveCharacterTextSplitter 控制每块长度（chunk_size/overlap 取自 config）。
"""

from dataclasses import dataclass

from chromadb.api.types import Metadata
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# 按哪些标题层级切分（markdown 前缀 -> metadata key）
_HEADERS: list[tuple[str, str]] = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]


@dataclass
class Chunk:
    """切分后的一个文本块及其元数据。"""

    content: str
    metadata: Metadata


def split_document(
    text: str,
    source: str,
    kb_id: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """切分 Markdown 文本为 Chunk 列表。

    每个 Chunk 的 metadata 含 source、kb_id、chunk_index，以及所在标题路径
    （Header 1/2/3，仅当存在）；所有值均为 chroma 标量类型。

    Args:
        text: 已清洗的 Markdown 文本。
        source: 原始文件名，写入 source 元数据。
        kb_id: 所属知识库 id，写入 kb_id 元数据。
        chunk_size: 每块最大字符数。
        chunk_overlap: 相邻块重叠字符数。

    Returns:
        Chunk 列表；空文本返回空列表。
    """
    if not text:
        return []

    sections = MarkdownHeaderTextSplitter(_HEADERS).split_text(text)
    for s in sections:
        s.metadata["source"] = source
        s.metadata["kb_id"] = kb_id

    rec_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = rec_splitter.split_documents(sections)

    out: list[Chunk] = []
    for i, c in enumerate(chunks):
        c.metadata["chunk_index"] = i
        # 仅保留 chroma 标量值，过滤潜在的 None/列表等
        meta: dict[str, str | int | float | bool] = {
            k: v for k, v in c.metadata.items() if isinstance(v, str | int | float | bool)
        }
        out.append(Chunk(content=c.page_content, metadata=meta))
    return out
