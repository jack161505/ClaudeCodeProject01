"""AgentService 测试：用 FakeChatModel + 假 embedding 验证检索->生成与流式事件。

FakeChatModel / make_retrieve_call 见 conftest.py。
"""

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from conftest import FakeChatModel, make_retrieve_call
from rag_cs.agent.graph import AgentEventType, AgentService, _translate_stream
from rag_cs.agent.tools import make_retrieve_tool
from rag_cs.ingestion.pipeline import IngestionPipeline
from rag_cs.kb.registry import KBMetaStore
from rag_cs.vectorstore.store import VectorStoreService


def test_retrieve_tool_returns_formatted_hits(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")
    IngestionPipeline(vstore=vstore, registry=registry).ingest(
        kb.id, "faq.md", "# 密码\n重置密码的步骤。"
    )
    tool = make_retrieve_tool([kb.collection_name], top_k=3, vstore=vstore)

    result = tool.invoke({"query": "密码"})

    assert "来源：faq.md" in result
    assert "重置密码" in result


def test_retrieve_tool_empty(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("空")
    tool = make_retrieve_tool([kb.collection_name], top_k=3, vstore=vstore)

    assert tool.invoke({"query": "无关内容"}) == "未检索到相关内容。"


def test_retrieve_tool_multiple_hits(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")
    vstore.ensure_collection(kb.collection_name)
    vstore.add(
        kb.collection_name,
        ["密码A", "密码B", "密码C"],
        [{"source": "a.md"}, {"source": "a.md"}, {"source": "a.md"}],
        ["1", "2", "3"],
    )
    tool = make_retrieve_tool([kb.collection_name], top_k=3, vstore=vstore)

    result = tool.invoke({"query": "密码"})

    assert "[1]" in result and "[2]" in result and "[3]" in result
    assert result.count("来源：a.md") == 3


def test_retrieve_tool_empty_collections(vstore: VectorStoreService) -> None:
    tool = make_retrieve_tool([], top_k=3, vstore=vstore)

    assert tool.invoke({"query": "x"}) == "未检索到相关内容。"


def test_agent_streams_retrieve_and_answer(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")
    IngestionPipeline(vstore=vstore, registry=registry).ingest(
        kb.id, "faq.md", "# 密码\n重置密码请进入设置。"
    )
    model = FakeChatModel(
        responses=[make_retrieve_call("密码"), AIMessage(content="重置密码请进入设置。")]
    )
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([kb.collection_name], "如何重置密码？"))
    types = [e.type for e in events]

    assert types[0] == AgentEventType.TOOL_CALL
    assert AgentEventType.TOOL_RESULT in types
    assert AgentEventType.TOKEN in types
    assert types[-1] == AgentEventType.DONE
    result_event = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)
    assert "重置密码" in result_event.content
    call_event = next(e for e in events if e.type is AgentEventType.TOOL_CALL)
    assert call_event.query == "密码"


def test_agent_answers_directly_without_retrieval(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")
    model = FakeChatModel(responses=[AIMessage(content="你好，我是客服。")])
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([kb.collection_name], "你是谁？"))
    types = [e.type for e in events]

    assert AgentEventType.TOOL_CALL not in types
    assert AgentEventType.TOKEN in types
    assert types[-1] == AgentEventType.DONE


def test_build_returns_runnable(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")
    model = FakeChatModel(responses=[AIMessage(content="ok")])
    svc = AgentService(vstore=vstore, model=model)

    graph = svc.build([kb.collection_name])

    assert hasattr(graph, "stream")
    assert hasattr(graph, "invoke")


def test_translate_stream_token() -> None:
    chunk = AIMessageChunk(content="你好", tool_calls=[])

    events = list(_translate_stream([(chunk, {})]))

    assert len(events) == 1
    assert events[0].type is AgentEventType.TOKEN
    assert events[0].content == "你好"


def test_translate_stream_tool_call() -> None:
    chunk = AIMessageChunk(
        content="",
        tool_calls=[
            {"name": "retrieve_kb", "args": {"query": "密码"}, "id": "c1", "type": "tool_call"}
        ],
    )

    events = list(_translate_stream([(chunk, {})]))

    assert len(events) == 1
    assert events[0].type is AgentEventType.TOOL_CALL
    assert events[0].query == "密码"


def test_translate_stream_tool_result() -> None:
    msg = ToolMessage(content="检索结果片段", tool_call_id="c1", name="retrieve_kb")

    events = list(_translate_stream([(msg, {})]))

    assert len(events) == 1
    assert events[0].type is AgentEventType.TOOL_RESULT
    assert events[0].content == "检索结果片段"
