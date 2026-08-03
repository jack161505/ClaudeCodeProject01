"""LangGraph 工具调用 Agent：检索->生成，支持流式事件。

用 langgraph.prebuilt.create_react_agent 构造 ReAct 图：LLM 自主决定是否调用
检索工具，工具执行后回到 LLM，直到给出最终回答。流式用 stream_mode="messages"，
翻译为语义事件（token / 工具调用 / 工具结果 / 完成）供 UI 消费。

TODO(langgraph-2.0): create_react_agent 已弃用，迁移到 langchain.agents.create_agent
（需在 pyproject 增加 langchain 依赖）。
"""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from rag_cs.agent.tools import make_retrieve_tool
from rag_cs.config import Settings, get_settings
from rag_cs.providers.factory import get_chat_model
from rag_cs.vectorstore.store import VectorStoreService

_DEFAULT_SYSTEM_PROMPT = (
    "你是一名客服助手。请优先调用 retrieve_kb 工具查询知识库，"
    "基于检索结果回答用户问题；若知识库无相关内容，如实告知。回答简洁。"
)


class AgentEventType(StrEnum):
    """Agent 流式事件类型。"""

    TOKEN = "token"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"


@dataclass
class AgentEvent:
    """Agent 流式事件。

    Attributes:
        type: 事件类型。
        content: TOKEN 的文本片段 / TOOL_RESULT 的检索结果。
        query: TOOL_CALL 时的检索查询。
    """

    type: AgentEventType
    content: str = ""
    query: str | None = None


class AgentService:
    """构造并运行工具调用型 Agent。"""

    def __init__(
        self,
        settings: Settings | None = None,
        vstore: VectorStoreService | None = None,
        model: BaseChatModel | None = None,
    ) -> None:
        self._s = settings or get_settings()
        self._vstore = vstore or VectorStoreService(self._s)
        self._model = model or get_chat_model(self._s)

    def build(
        self,
        collections: list[str],
        system_prompt: str | None = None,
    ) -> CompiledStateGraph[Any]:
        """构造针对给定启用 collection 的 Agent 图。"""
        tool = make_retrieve_tool(collections, self._s.retrieval_top_k, self._vstore)
        prompt = system_prompt if system_prompt is not None else _DEFAULT_SYSTEM_PROMPT
        return create_react_agent(self._model, [tool], prompt=prompt)

    def stream(
        self,
        collections: list[str],
        message: str,
        system_prompt: str | None = None,
    ) -> Iterator[AgentEvent]:
        """流式运行 Agent，产出语义事件（token / 工具调用 / 工具结果 / 完成）。"""
        graph = self.build(collections, system_prompt)
        raw = graph.stream({"messages": [HumanMessage(message)]}, stream_mode="messages")
        # stream_mode="messages" 运行时产出 (message, metadata) 二元组，
        # 但 langgraph 的静态签名是泛型联合，此处显式断言。
        yield from _translate_stream(
            cast("Iterable[tuple[BaseMessage, Mapping[str, object]]]", raw)
        )
        yield AgentEvent(type=AgentEventType.DONE)


def _translate_stream(
    stream: Iterable[tuple[BaseMessage, Mapping[str, object]]],
) -> Iterator[AgentEvent]:
    """把 LangGraph messages 流翻译为语义事件。"""
    for chunk, _meta in stream:
        if isinstance(chunk, AIMessageChunk):
            if chunk.tool_calls:
                args = chunk.tool_calls[0].get("args") or {}
                query_val = args.get("query") if isinstance(args, dict) else None
                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL,
                    query=query_val if isinstance(query_val, str) else None,
                )
            else:
                content = chunk.content
                if isinstance(content, str) and content:
                    yield AgentEvent(type=AgentEventType.TOKEN, content=content)
        elif isinstance(chunk, ToolMessage):
            raw_content = chunk.content
            text = raw_content if isinstance(raw_content, str) else str(raw_content)
            yield AgentEvent(type=AgentEventType.TOOL_RESULT, content=text)


__all__ = ["AgentEvent", "AgentEventType", "AgentService"]
