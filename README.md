# RAG 智能客服系统

基于 RAG（检索增强生成）的智能客服系统：上传 Markdown 文档构建知识库，对话时 Agent 自动检索知识库并基于检索结果流式回答。

## 功能

- **知识库管理**：新建知识库、上传 Markdown 文档、自动切分并向量化入库、删除。
- **智能客服对话**：用户提问后，Agent 自主调用知识库检索工具，基于检索结果生成回答；支持流式输出，并展示工具调用过程（检索查询与命中片段）。
- **多知识库**：对话时可在侧边栏勾选启用哪些知识库，跨库联合检索。
- **多模型平台**：支持 OpenAI / Ollama / Xinference 三个平台；chat 与 embedding 独立配置（例如 chat 走本地 Ollama、embedding 仍走 OpenAI）。

## 技术栈

| 层 | 选型 |
|---|---|
| Web 界面 | Streamlit |
| Agent 编排 | LangGraph（工具调用型 ReAct） |
| 向量库 | Chroma（持久化） |
| 模型接入 | langchain-openai / langchain-ollama（Xinference 走 OpenAI 兼容接口） |
| 配置 | pydantic-settings |
| 工具链 | uv · ruff · mypy(strict) · pytest |

## 项目结构

```
src/rag_cs/
├── config.py              # Settings：环境变量/.env 加载，chat/embedding 路由
├── exceptions.py          # RagCsError 基类
├── providers/             # 模型构造工厂
│   ├── factory.py         #   按 provider 分发 chat/embedding
│   ├── openai_provider.py
│   ├── ollama_provider.py
│   └── xinference_provider.py
├── vectorstore/           # Chroma 封装
│   └── store.py           #   VectorStoreService：按 collection 增删查，跨库合并
├── kb/                    # 知识库元数据
│   ├── models.py          #   KnowledgeBase / DocumentRecord
│   └── registry.py        #   KBMetaStore：CRUD + 文档登记（读写 kb_meta.json）
├── ingestion/             # 文档入库
│   ├── loader.py          #   Markdown 清洗
│   ├── splitter.py        #   两段式切分（标题 + 长度）
│   └── pipeline.py        #   IngestionPipeline：清洗->切分->入库->登记
├── agent/                 # LangGraph Agent
│   ├── tools.py           #   检索工具闭包 make_retrieve_tool
│   └── graph.py           #   AgentService + 流式事件翻译
└── ui/                    # Streamlit 前端
    ├── app.py             #   入口：侧边栏路由 + 启用知识库多选
    ├── state.py           #   session_state 封装
    └── pages/
        ├── kb_management.py
        └── chat.py
tests/                     # 30 个测试（离线，假 embedding + FakeChatModel）
scripts/check_providers.py # 手动验证 providers 连通性
```

## 快速开始

要求 Python ≥ 3.11。用 [uv](https://docs.astral.sh/uv/) 管理依赖。

```bash
# 1. 安装依赖（uv 会自动准备 Python）
uv sync --extra dev

# 2. 配置环境变量
cp .env.example .env
#   编辑 .env，至少填 OPENAI_API_KEY；或改用本地 Ollama/Xinference（见下表）

# 3.（可选）验证 chat / embedding 连通
uv run python scripts/check_providers.py

# 4. 启动
uv run streamlit run src/rag_cs/ui/app.py
```

## 使用

### 知识库管理页

1. 新建知识库（名称 + 描述）。
2. 选择目标知识库，上传一个或多个 `.md` / `.markdown` 文件，点「入库」--自动切分并向量化，显示入库片段数。
3. 知识库列表可展开查看文档与片段数，支持删除（同时清掉对应向量集合）。

### 智能客服对话页

1. 在侧边栏勾选要启用的知识库（可多选）。
2. 输入问题，Agent 会自主决定是否检索：
   - 触发检索时显示「🔍 检索知识库：\<查询\>」与检索结果折叠框；
   - 随后逐字流式输出回答。

## 配置项（`.env`）

| 变量 | 默认 | 说明 |
|---|---|---|
| `CHAT_PROVIDER` | `openai` | `openai` / `ollama` / `xinference` |
| `CHAT_MODEL` | `gpt-4o-mini` | chat 模型名 |
| `EMBEDDING_PROVIDER` | `openai` | `openai` / `ollama` / `xinference` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | embedding 模型名 |
| `OPENAI_API_KEY` | - | OpenAI 凭证（走 Ollama/Xinference 时可留空） |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `XINFERENCE_BASE_URL` | `http://localhost:9997` | Xinference 服务地址 |
| `CHROMA_DIR` | `data/chroma` | Chroma 持久化目录 |
| `KB_META_PATH` | `data/kb_meta.json` | 知识库元数据文件 |
| `CHUNK_SIZE` | `500` | 切分每块最大字符数 |
| `CHUNK_OVERLAP` | `50` | 相邻块重叠字符数 |
| `RETRIEVAL_TOP_K` | `4` | 检索返回的片段数 |

> 走 Ollama：设 `CHAT_PROVIDER=ollama`、`CHAT_MODEL=<本地模型名>`，并确保 `OLLAMA_BASE_URL` 指向运行中的 Ollama。chat 与 embedding 可分别选不同 provider。

## 架构

按层自底向上，每层只依赖下层：

- **config / providers**：统一从 `.env` 加载配置，按 provider 构造 chat 模型与 embeddings。
- **vectorstore**：一个知识库对应一个 Chroma collection（`kb_{slug}`）；跨库检索 = 各 collection 各查 top_k，按距离合并排序。embeddings 惰性构造。
- **kb**：纯元数据层（不依赖 chroma），生成 id/slug/collection_name，登记文档与片段数。
- **ingestion**：Markdown 经 `MarkdownHeaderTextSplitter`（保留标题路径）+ `RecursiveCharacterTextSplitter`（控长度）两段切分后入库；重新入库同名文件先清旧 chunk 再写新。
- **agent**：LangGraph ReAct，LLM 自主调用 `retrieve_kb` 工具；`stream_mode="messages"` 流式翻译为语义事件（token / 工具调用 / 工具结果 / 完成）。
- **ui**：Streamlit 单入口 + 侧边栏路由，全局启用知识库多选走 `session_state`。

数据流：
- 入库：`load -> split -> vectorstore.add -> registry.register_document`
- 问答：`用户提问 -> Agent -> retrieve_kb -> vectorstore.search -> LLM 基于结果流式回答`

## 开发

```bash
uv run pytest                      # 跑全部测试（离线，30 个）
uv run ruff check src tests scripts # lint
uv run ruff format --check src tests scripts  # 格式检查
uv run mypy src/rag_cs             # 类型检查（strict）
```

测试不联网：用假 embedding（确定性向量）和 `FakeChatModel`（按对话状态返回预设回复）覆盖 vectorstore/kb/ingestion/agent 全流程。UI 用 `streamlit.testing.v1.AppTest` 做了渲染烟雾测试；对话端到端流式需配真实模型 key 手动验证。

## 注意事项

- `data/` 目录（Chroma 持久化与 `kb_meta.json`）已加入 `.gitignore`，不入库。
- Agent 当前用 `langgraph.prebuilt.create_react_agent`（langgraph 1.0 起标记弃用，2.0 移除），运行时会打印一条弃用警告，不影响功能。
