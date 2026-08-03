# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RAG 智能客服系统：上传 Markdown 构建知识库，对话时 LangGraph Agent 自动检索知识库并流式回答。完整说明见 [README.md](README.md)。

技术栈：Streamlit + LangGraph + Chroma；模型支持 OpenAI / Ollama / Xinference（chat 与 embedding 独立路由）。Python ≥ 3.11，uv 管理依赖。

## 常用命令

```bash
uv sync --extra dev                           # 安装依赖
uv run pytest                                 # 测试（离线，30 个）
uv run ruff check src tests scripts           # lint
uv run ruff format --check src tests scripts  # 格式检查
uv run mypy src/rag_cs                        # 类型检查（strict）
uv run streamlit run src/rag_cs/ui/app.py     # 启动应用
uv run python scripts/check_providers.py      # 验证模型连通
```

## 架构

包 `rag_cs`（src/rag_cs），按层自底向上，每层只依赖下层：

- `config` / `providers`：从 `.env` 加载配置，按 provider 构造 chat/embedding。
- `vectorstore`：Chroma 封装，一个知识库对应一个 collection（`kb_{slug}`），跨库检索合并；embeddings 惰性构造。
- `kb`：知识库元数据（读写 `data/kb_meta.json`），生成 id/slug/collection_name，登记文档与片段数。
- `ingestion`：Markdown 两段式切分（`MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter`）+ 入库流水线。
- `agent`：LangGraph 工具调用 Agent，`stream_mode="messages"` 翻译为 `AgentEvent`。
- `ui`：Streamlit 单入口 + 侧边栏路由，全局启用知识库多选走 `session_state`。

数据流：入库 `load -> split -> vectorstore.add -> registry.register_document`；问答 `Agent -> retrieve_kb -> vectorstore.search -> LLM 流式回答`。

## 约定

- 代码风格见 [.claude/rules/code-style.md](.claude/rules/code-style.md)；ruff/mypy 配置在 `pyproject.toml`（目标 py312，忽略中文全角标点规则 RUF001/002/003）。
- 自定义异常继承 `rag_cs.exceptions.RagCsError`。
- 测试不联网：`conftest.FakeEmbeddings`（确定性向量）+ `test_agent.FakeChatModel`（按对话状态返回预设回复）覆盖全流程；数据落 `tmp_data_dir` 临时目录。
- chromadb 1.5.9 实测约束：空 metadata `{}` 会被拒（须非空 dict）；collection 不存在抛 `chromadb.errors.NotFoundError`（非 `ValueError`）。
- Agent 用 `langgraph.prebuilt.create_react_agent`（langgraph 1.0 起弃用，TODO 迁移 `langchain.agents.create_agent`）。
- 运行时数据 `data/` 与 `.env` 已 gitignore；`.env.example` 入库。
