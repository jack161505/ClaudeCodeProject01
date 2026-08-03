"""AgentService 测试：用 FakeChatModel + 假 embedding 验证检索->生成与流式事件。

FakeChatModel 按 conversation 中已有 AIMessage 数量依次返回预设回复，
bind_tools 返回自身；retrieve_kb 工具真正走假 vstore 检索。
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from rag_cs.agent.graph import AgentEventType, AgentService
from rag_cs.agent.tools import make_retrieve_tool
from rag_cs.ingestion.pipeline import IngestionPipeline
from rag_cs.kb.registry import KBMetaStore
from rag_cs.vectorstore.store import VectorStoreService


class FakeChatModel(BaseChatModel):
    """按对话中已有 AIMessage 数量依次返回预设回复；bind_tools 返回自身。"""

    responses: list[BaseMessage]

    def _pick(self, messages):
        n_ai = sum(1 for m in messages if isinstance(m, AIMessage))
        return self.responses[n_ai] if n_ai < len(self.responses) else AIMessage(content="(end)")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self._pick(messages))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self._pick(messages)
        text = msg.content if isinstance(msg.content, str) else str(msg.content)
        first = True
        for i in range(0, len(text) or 1, 3):
            chunk_msg = AIMessageChunk(
                content=text[i : i + 3],
                tool_calls=msg.tool_calls if first else [],
            )
            yield ChatGenerationChunk(message=chunk_msg)
            first = False

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self):
        return "fake"


def _retrieve_call(query: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "retrieve_kb", "args": {"query": query}, "id": "c1", "type": "tool_call"}
        ],
    )


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


def test_agent_streams_retrieve_and_answer(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")
    IngestionPipeline(vstore=vstore, registry=registry).ingest(
        kb.id, "faq.md", "# 密码\n重置密码请进入设置。"
    )
    model = FakeChatModel(
        responses=[_retrieve_call("密码"), AIMessage(content="重置密码请进入设置。")]
    )
    svc = AgentService(vstore=vstore, model=model)

    events = list(svc.stream([kb.collection_name], "如何重置密码？"))
    types = [e.type for e in events]

    assert types[0] == AgentEventType.TOOL_CALL
    assert AgentEventType.TOOL_RESULT in types
    assert AgentEventType.TOKEN in types
    assert types[-1] == AgentEventType.DONE
    result_event = next(e for e in events if e.type == AgentEventType.TOOL_RESULT)
    assert "重置密码" in result_event.content
    call_event = next(e for e in events if e.type == AgentEventType.TOOL_CALL)
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
