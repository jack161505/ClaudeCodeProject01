"""集成冒烟测试：打通 kb + ingestion + vectorstore + agent 全链路（离线）。

用假 embedding + FakeChatModel，验证从「建库 -> 入库 -> Agent 检索 -> 回答」
以及多库、重新入库、空库等端到端场景。
"""

from langchain_core.messages import AIMessage

from conftest import FakeChatModel, make_retrieve_call
from rag_cs.agent.graph import AgentEventType, AgentService
from rag_cs.ingestion.pipeline import IngestionPipeline
from rag_cs.kb.registry import KBMetaStore
from rag_cs.vectorstore.store import VectorStoreService


def test_full_stack_create_ingest_chat(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    """端到端：建库 -> 入库 Markdown -> Agent 检索 -> 基于结果回答。"""
    kb = registry.create("客服手册", "常见问题")
    IngestionPipeline(vstore=vstore, registry=registry).ingest(
        kb.id, "faq.md", "# 退款\n退款请在 7 天内联系客服。"
    )
    model = FakeChatModel(
        responses=[make_retrieve_call("退款"), AIMessage(content="退款请在 7 天内联系客服。")]
    )
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([kb.collection_name], "怎么退款？"))
    types = [e.type for e in events]

    assert AgentEventType.TOOL_CALL in types
    result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)
    assert "退款" in result.content
    assert "7 天" in result.content
    assert AgentEventType.TOKEN in types
    assert types[-1] is AgentEventType.DONE

    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count >= 1


def test_multi_kb_agent_searches_across_enabled(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    """两个知识库都启用时，Agent 跨库检索到命中库的内容。"""
    kb1 = registry.create("售后")
    kb2 = registry.create("物流")
    IngestionPipeline(vstore=vstore, registry=registry).ingest(kb1.id, "a.md", "退货政策说明。")
    IngestionPipeline(vstore=vstore, registry=registry).ingest(
        kb2.id, "b.md", "发货时效为 48 小时。"
    )

    model = FakeChatModel(
        responses=[make_retrieve_call("发货"), AIMessage(content="发货时效 48 小时。")]
    )
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([kb1.collection_name, kb2.collection_name], "发货多久？"))
    result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)

    assert "48 小时" in result.content  # 命中物流库


def test_reingest_then_agent_sees_update(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    """重新入库后，Agent 检索到的是新内容而非旧内容。"""
    kb = registry.create("手册")
    pipe = IngestionPipeline(vstore=vstore, registry=registry)
    pipe.ingest(kb.id, "doc.md", "旧内容：电话 10086。")
    pipe.ingest(kb.id, "doc.md", "新内容：电话 10010。")  # 重新入库

    model = FakeChatModel(
        responses=[make_retrieve_call("电话"), AIMessage(content="电话是 10010。")]
    )
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([kb.collection_name], "电话多少？"))
    result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)

    assert "10010" in result.content
    assert "10086" not in result.content  # 旧 chunk 已清除


def test_agent_empty_collections_retrieves_nothing(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    """未启用任何知识库时，检索工具返回未命中，Agent 仍可流式回答。"""
    registry.create("手册")
    model = FakeChatModel(
        responses=[make_retrieve_call("任意"), AIMessage(content="暂无相关资料。")]
    )
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([], "随便问"))
    types = [e.type for e in events]

    result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)
    assert result.content == "未检索到相关内容。"
    assert AgentEventType.TOKEN in types
    assert types[-1] is AgentEventType.DONE
