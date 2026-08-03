"""检索工具：按启用的知识库 collection 联合检索。

工具以闭包形式构造：捕获本次启用的 collection 列表、top_k 与 vstore，
供 LangGraph Agent 自主决定是否调用。
"""

from langchain_core.tools import BaseTool, tool

from rag_cs.vectorstore.store import VectorStoreService


def make_retrieve_tool(
    collections: list[str],
    top_k: int,
    vstore: VectorStoreService,
) -> BaseTool:
    """构造检索工具闭包；collections 为本次启用的 collection 名列表。"""

    @tool
    def retrieve_kb(query: str) -> str:
        """检索知识库，返回与查询最相关的文档片段。

        当用户提问涉及产品使用、退款、密码重置等已有文档覆盖的内容时调用。
        """
        hits = vstore.search(collections, query, top_k)
        if not hits:
            return "未检索到相关内容。"
        parts: list[str] = []
        for i, hit in enumerate(hits, 1):
            source_val = hit.metadata.get("source")
            source = source_val if isinstance(source_val, str) else "未知"
            parts.append(f"[{i}]（来源：{source}）\n{hit.content}")
        return "\n\n".join(parts)

    return retrieve_kb
