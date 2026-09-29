# Octop 二次开发手册

> 版本：v1.0.2b3 | 最后更新：2026-09-28

---

## 目录

1. [项目概览](#1-项目概览)
2. [技术栈](#2-技术栈)
3. [开发环境搭建](#3-开发环境搭建)
4. [项目结构详解](#4-项目结构详解)
5. [核心架构](#5-核心架构)
6. [模块边界与依赖规则](#6-模块边界与依赖规则)
7. [数据库层](#7-数据库层)
8. [Agent 系统](#8-agent-系统)
9. [消息处理流程](#9-消息处理流程)
10. [API 层开发](#10-api-层开发)
11. [CLI 开发](#11-cli-开发)
12. [前端开发](#12-前端开发)
13. [国际化 (i18n)](#13-国际化-i18n)
14. [连接器与 MCP](#14-连接器与-mcp)
15. [技能系统 (Skills)](#15-技能系统-skills)
16. [定时任务 (Cron)](#16-定时任务-cron)
17. [用户与权限](#17-用户与权限)
18. [插件系统](#18-插件系统)
19. [测试规范](#19-测试规范)
20. [代码质量与提交规范](#20-代码质量与提交规范)
21. [常见二次开发场景](#21-常见二次开发场景)
22. [FAQ](#22-faq)

---

## 1. 项目概览

**Octop** 是一个自托管的多用户、多 Agent AI 助手平台。它以单个 Python wheel 包的形式发布，包含：

- **FastAPI 后端** + **uvicorn** HTTP 服务
- **React 18 + TypeScript** 管理面板 (Dashboard)
- **Click CLI** 命令行工具
- 无外部队列依赖，仅需 LLM 提供商

### 核心能力

| 能力 | 说明 |
|------|------|
| 多 Agent 管理 | 创建、启动、停止、重载 Agent；支持专家 (expert) 和团队 (team) 两种类型 |
| 多渠道接入 | Web UI (WebSocket)、CLI、钉钉、飞书、Discord、Telegram 等 IM 渠道 |
| MCP 连接器 | 13+ 内置适配器 (百度地图、携程、飞书、QQ 音乐等) + 自定义 MCP 服务器 |
| 技能系统 | Markdown 定义的技能包，支持工作空间本地技能和 SkillHub 市场 |
| 知识库 (RAG) | 向量检索增强生成，支持多种 embedding 模型 |
| 定时任务 | 基于 APScheduler 的 cron 系统，支持文本推送和完整 Agent 对话 |
| 用户管理 | Argon2id 密码、SSO (OIDC)、角色权限、邀请码 |
| TLS | 内置 Let's Encrypt ACME 自动证书签发和续期 |
| 浏览器自动化 | Playwright 集成，Agent 可操控浏览器 |
| 桌面应用 | Wails (Go) 跨平台桌面客户端 |

### 设计哲学

- **单进程模型**：所有功能在一个 Python 进程中运行，asyncio 处理并发，无外部消息队列
- **垂直扩展**：适合自托管场景，简化部署和运维
- **双数据库后端**：SQLite (默认，零配置) 或 PostgreSQL (生产推荐)

---

## 2. 技术栈

### 后端

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| Web 框架 | FastAPI + uvicorn |
| 异步运行时 | asyncio (仅 `run_in_executor` 使用线程) |
| 数据库 | SQLite (WAL 模式) / PostgreSQL (psycopg + psycopg_pool) |
| Agent 运行时 | octop-harness (基于 LangGraph) |
| 消息网关 | octop-gateway |
| MCP 协议 | mcp >= 1.9 |
| 认证 | Argon2id (密码) + PyJWT (令牌) + cryptography |
| 定时调度 | APScheduler 3.x |
| 文档构建 | Hatchling |
| 包管理 | uv |

### 前端

| 层级 | 技术 |
|------|------|
| 框架 | React 18 + TypeScript 5.8 |
| 构建工具 | Vite 6.3 |
| UI 组件库 | Ant Design 5.29 |
| 路由 | React Router 7 |
| 状态管理 | ahooks 3.9 + React Context |
| Markdown | react-markdown + remark-gfm + rehype-katex |
| 代码编辑器 | Monaco Editor |
| 终端 | xterm.js 5.5 |
| 图表 | Recharts 3.10 |
| 图表 (流程图) | Mermaid 11 |
| 国际化 | i18next + react-i18next |
| PWA | vite-plugin-pwa |

### 开发工具

| 工具 | 用途 |
|------|------|
| Ruff | Python 代码格式化 + lint |
| mypy | Python 类型检查 (strict 模式) |
| Prettier | 前端代码格式化 |
| ESLint | 前端代码 lint |
| pytest | 后端测试 |
| vitest | 前端测试 |

---

## 3. 开发环境搭建

### 3.1 前置要求

```
Python  >= 3.12
Node.js >= 18 (推荐 20+)
uv      >= 0.7 (推荐 latest)
```

可使用 `mise.toml` 自动管理工具版本。

### 3.2 克隆与安装

```bash
git clone https://github.com/TencentCloud/Octop.git
cd Octop

# 安装后端开发依赖
make install          # 等价于 uv sync

# 安装 pre-commit hook (必须)
make install-hooks

# 验证环境
make all              # format-all + lint + typecheck + test
```

### 3.3 启动开发服务

```bash
# 同时启动前端 (Vite) + 后端 (octop run)
make dev

# 或分别启动
make dev-frontend     # Vite dev server (端口 5173, 代理 /api 到后端 8088)
make dev-backend      # octop run (端口 8088)
```

### 3.4 首次运行

首次启动时会进入设置向导 (Setup Wizard)：

1. 访问 `http://localhost:8088`
2. 设置管理员密码
3. 配置 LLM 提供商 (如 OpenAI API Key)
4. 完成初始化

也可通过 CLI 跳过向导：

```bash
octop init --yes
octop run
```

### 3.5 目录结构概览

```
Octop/
├── src/octop/              # Python 后端源码
│   ├── config.py           # 配置系统
│   ├── launch.py           # 启动入口 (组合根)
│   ├── api/                # HTTP 适配层 (FastAPI)
│   ├── cli/                # CLI 命令
│   ├── i18n/               # 国际化
│   ├── infra/              # 核心领域逻辑
│   │   ├── agents/         # Agent 管理
│   │   ├── backend/        # 存储后端
│   │   ├── connectors/     # MCP 连接器
│   │   ├── cron/           # 定时任务
│   │   ├── db/             # 数据库层
│   │   ├── gateway/        # 消息网关
│   │   ├── history/        # 版本化历史
│   │   ├── knowledge/      # 知识库
│   │   ├── setup/          # 系统设置/TLS
│   │   ├── skills/         # 技能系统
│   │   ├── users/          # 用户管理
│   │   └── utils/          # 工具函数
│   └── dashboard/          # 前端构建产物 (勿直接编辑)
├── dashboard/              # 前端源码 (Vite)
├── docker/                 # Docker 部署文件
├── docs/                   # 文档
├── tests/                  # 测试套件
├── plugins/                # 示例插件
├── scripts/                # 构建/安装脚本
└── desktop/                # 桌面应用 (Wails/Go)
```

---

## 4. 项目结构详解

### 4.1 后端包布局 (`src/octop/`)

#### 入口文件

| 文件 | 职责 |
|------|------|
| `config.py` | `OctopConfig` 数据类，从 `config.json` + 环境变量加载配置 |
| `launch.py` | 组合根：创建 `OctopServer`，构建 FastAPI app，配置 uvicorn，启动服务 |
| `__main__.py` | `python -m octop` 入口，委托给 CLI |

#### `api/` — HTTP 适配层

| 路径 | 职责 |
|------|------|
| `app.py` | FastAPI 工厂函数 `build_app()`，注册所有路由 |
| `deps.py` | 依赖注入：JWT 解析、`current_user`、`get_server` |
| `middleware/` | JWT 认证中间件、设置向导锁定中间件 |
| `errors.py` | `OctopError` → HTTP 状态码映射 |
| `openapi_meta.py` | Scalar API 文档标签和描述 |
| `common/` | 共享工具：附件处理、验证器、工作空间路径等 |
| `routers/` | 47+ 路由模块，每个对应一个资源 |

#### `infra/` — 核心领域层

| 子包 | 职责 | 典型调用者 |
|------|------|-----------|
| `agents/` | Agent 注册表、harness 运行时、提供商、设置、工作空间、安全、 persona、专家、插件、团队、记忆 | `server.py`, `gateway/`, `api/routers/agents.py` |
| `backend/` | 工作空间存储适配器、解析器、远程探测 (COS/S3) | `agents/`, `api/routers/workspace*.py` |
| `connectors/` | 连接器目录、OAuth、MCP 网关、凭证加密 | `api/routers/connectors.py`, `agents/manager.py` |
| `cron/` | 定时任务、触发器、Agent 工具钩子 | `server.py`, `api/routers/cron.py` |
| `db/` | `SqlitePool`、迁移、`RepoBundle` / `SharedServices` | 所有需要持久化的领域代码 |
| `gateway/` | IM 入口、线程管理、斜杠命令、Bot 创建 | `server.py`, `api/routers/chat.py` |
| `history/` | 版本化消息归档、轨迹、回合投影 | `gateway/`, `api/routers/chat`, `cron/` |
| `setup/` | 首次运行向导、系统服务安装、TLS/ACME | `server.py`, `launch.py`, `api/routers/setup.py` |
| `skills/` | 技能包、SkillHub HTTP 客户端 | `api/routers/skills.py`, `agents/experts` |
| `users/` | 用户、角色、密码哈希、`UserManager` | `server.py`, `api/routers/auth.py` |
| `utils/` | 纯工具函数 (路径、ULID、env 文件、Ollama) | 所有模块 |

#### `cli/` — 命令行界面

| 路径 | 职责 |
|------|------|
| `main.py` | Click 入口，命令注册，懒加载 |
| `registry.py` | 20 个命令的注册表 |
| `commands/` | 各子命令实现 |
| `repl/` | 交互式聊天 REPL |
| `support/` | CLI 辅助工具 (认证、数据库、提示、QR 码等) |

### 4.2 前端布局 (`dashboard/src/`)

| 路径 | 职责 |
|------|------|
| `api/` | 类型化 fetch 封装 (`request.ts`, `modules/*`) |
| `pages/` | 路由级页面组件 |
| `components/` | 共享 UI 构建块 |
| `hooks/` | 可复用 React hooks |
| `context/` | 应用级 React Context |
| `layouts/` | 布局壳、侧边栏 |
| `routes/` | 路由表 |
| `locales/` | i18n 翻译文件 |
| `utils/` | 前端工具函数 |
| `plugins/` | 工具渲染器 |

---

## 5. 核心架构

### 5.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│  Surface 层                                         │
│  Dashboard (React) │ CLI (Click) │ HTTP/WebSocket   │
├─────────────────────────────────────────────────────┤
│  API 层 (FastAPI Routers)                           │
│  路由注册 │ JWT 认证 │ 错误映射 │ OpenAPI           │
├─────────────────────────────────────────────────────┤
│  Domain 层 (infra/)                                 │
│  AgentManager │ Gateway │ CronManager │ UserManager │
├─────────────────────────────────────────────────────┤
│  Runtime 层                                         │
│  octop-harness (LangGraph) │ octop-gateway          │
│  octop-memory │ octop-browser                       │
├─────────────────────────────────────────────────────┤
│  Storage 层                                         │
│  SQLite/PostgreSQL │ 文件系统 │ 对象存储 (S3/COS)   │
└─────────────────────────────────────────────────────┘
```

### 5.2 启动流程

```
CLI (octop run)
  └─► launch.run_foreground_blocking()
       └─► launch.run_foreground() (async)
            ├─► OctopServer.__init__()
            │    └─► PathLayout(~/.octop)
            ├─► OctopServer.start()
            │    ├─► paths.ensure_root()           # 创建目录树
            │    ├─► apply_env_file()               # 加载 .env
            │    ├─► _setup_logging()               # 日志轮转
            │    ├─► load_config()                  # config.json + 环境变量
            │    ├─► ExpertCatalog / SubagentCatalog # 加载目录
            │    ├─► PluginManager.seed + load       # 插件
            │    ├─► open_database()                # SQLite/PostgreSQL
            │    ├─► run_migrations()               # 数据库迁移
            │    ├─► build_shared_services()        # DI 容器
            │    └─► _boot_runtime()                # 领域服务
            │         ├─► AgentManager              # Agent 注册表
            │         ├─► Gateway                   # 消息网关
            │         ├─► CronManager               # 定时任务
            │         ├─► UserManager               # 用户管理
            │         └─► ProactiveCareService      # 主动关怀
            ├─► build_app(server)                   # FastAPI 工厂
            ├─► 配置 uvicorn (单/双监听器)
            └─► asyncio.gather(servers)             # 开始服务
```

### 5.3 依赖注入

Octop 使用基于 `SharedServices` 的轻量 DI：

```python
# SharedServices 是冻结数据类，包含所有仓库实例
@dataclass(frozen=True)
class SharedServices:
    paths: PathLayout
    config: OctopConfig
    repos: RepoBundle  # 24 个仓库的集合

# 路由通过 FastAPI Depends 获取
@router.get("/api/agents")
async def list_agents(
    server: OctopServer = Depends(get_server),
    user: User = Depends(current_user),
):
    agents = await server.services.agent_repo.list_for_user(user.id)
    ...
```

### 5.4 数据流

```
用户消息 → Gateway (processor.py)
  ├─ 解析斜杠命令 → SlashDispatcher
  ├─ 解析 HITL 审批 → HitlChannelCoordinator
  ├─ 获取/创建 Thread → ThreadRegistry
  ├─ 构建 HarnessRequest
  │   ├─ 解析模型 (thread > user > agent > fallback)
  │   ├─ 解析 MCP 连接器
  │   └─ 解析知识库
  ├─ Agent.stream() → octop-harness (LangGraph)
  │   ├─ LLM 调用
  │   ├─ 工具执行
  │   └─ 记忆检索
  └─ 输出 → MessageEvent 流
      ├─ WebSocket → Dashboard
      ├─ SSE → IM 渠道
      └─ 持久化 → ThreadMessage + UsageLog + TrajectoryEvent
```

---

## 6. 模块边界与依赖规则

### 6.1 依赖方向

**核心规则：依赖向内流动 — 传输层调用领域层，领域层永远不调用 HTTP/CLI。**

```
dashboard/ ──HTTP──► api/ ──► infra/ ──► infra/utils/, octop.config
cli/ ──► launch.py ──► api/ + infra/
```

### 6.2 硬性禁止

| 禁止 | 原因 |
|------|------|
| `infra/` → `api/`, `cli/`, `launch.py` | 领域层不能依赖传输层 |
| `api/` → `cli/`, `launch.py` | HTTP 层不能依赖 CLI |
| `cli/` → `api/` | CLI 通过 `launch.py` 获取运行时 |
| `infra/db/repos/` → 非 DB 的 `infra` 包 | 仓库只做 SQL |
| `infra/utils/` → 非 utils 的 `infra` 包 | 工具函数必须纯粹 |
| `api/routers/` 中写业务规则 | 路由只做 HTTP 验证 + 委托 `infra/` |

### 6.3 `infra/` 内部依赖规则

| 模块 | 可导入 | 不可导入 |
|------|--------|---------|
| `infra/utils/` | stdlib, 第三方 | 任何 `infra/*` 领域代码 |
| `infra/db/repos/` | `infra/db/_base`, `infra/utils/` | `agents/`, `gateway/`, `api/` |
| `infra/` (领域) | `infra/utils/`, `infra/db/`, `config`, 同级 `infra/*` | `api/`, `cli/`, `launch.py` |

### 6.4 路由层规则

`api/routers/` 中的路由处理函数必须保持薄层：

```python
# ✅ 正确：路由只做验证和委托
@router.post("/api/agents/{agent_id}/chat")
async def chat(
    agent_id: str,
    body: ChatRequest,
    server: OctopServer = Depends(get_server),
    user: User = Depends(current_user),
):
    row = await server.services.agent_repo.get(agent_id)
    _assert_agent_owner(row, user)  # 权限验证
    async for event in server.app_runtime.gateway.stream(agent_id, request):
        yield event

# ❌ 错误：路由中写业务逻辑
@router.post("/api/agents/{agent_id}/chat")
async def chat(...):
    # 不应该在这里做消息处理、数据库操作等
    messages = await db.execute("SELECT ...")
    ...
```

---

## 7. 数据库层

### 7.1 双后端支持

Octop 同时支持 SQLite 和 PostgreSQL，共享一套 schema：

| 特性 | SQLite | PostgreSQL |
|------|--------|-----------|
| 默认启用 | 是 | 否 |
| 并发模型 | WAL + RLock | 连接池 |
| 适用场景 | 开发、小规模部署 | 生产、多用户 |
| 迁移 | 自动 | 自动 |
| 向量搜索 | 不支持 | pgvector |

### 7.2 迁移系统

迁移文件位于 `src/octop/infra/db/migrations/`，每个迁移是一对文件：

```
001_initial.sql          # SQLite DDL
001_initial.pg.sql       # PostgreSQL DDL
```

**添加新迁移的步骤：**

1. 创建 `00N_description.sql` 和 `00N_description.pg.sql`
2. 编写 DDL (CREATE TABLE, ALTER TABLE 等)
3. 更新 `tests/unit/db/test_db_pool.py` 中的版本断言
4. 如需 SQLite 不支持的 ALTER (如 RENAME)，在 `infra/db/migrate.py` 中添加辅助函数

**当前 schema 版本：** v18 (18 个迁移)

### 7.3 仓库模式 (Repository Pattern)

所有数据访问通过仓库类封装，位于 `infra/db/repos/`：

```python
# 仓库基类提供通用辅助
class AgentRepo:
    def __init__(self, pool: DatabasePool):
        self._pool = pool

    async def get(self, agent_id: str) -> AgentRow | None:
        row = await self._pool.fetch_one(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        )
        return AgentRow.from_row(row) if row else None

    async def list_for_user(self, user_id: int) -> list[AgentRow]:
        rows = await self._pool.fetch_all(
            "SELECT * FROM agents WHERE user_id = ?", (user_id,)
        )
        return [AgentRow.from_row(r) for r in rows]
```

### 7.4 资源表约定

API 可见的资源表遵循统一约定：

| 列 | 角色 |
|----|------|
| `id` | 整数代理主键 (AUTOINCREMENT) |
| `{entity}_id` | 公开字符串唯一标识 (ULID/短 ID)，API 使用此列 |
| 子行外键 | 存储字符串 ID (`agent_id`, `thread_id`)，引用父表的 `{entity}_id` |

**例外：** `users` (整数 FK)、名称键配置 (`providers`)、追加日志 (`usage_log`)、KV (`settings`) 不遵循此约定。

### 7.5 使用 SharedServices

```python
# 通过 server.services 访问所有仓库
server: OctopServer = Depends(get_server)

# 读取
agent = await server.services.agent_repo.get(agent_id)
user = await server.services.user_repo.get_by_id(user_id)

# 写入
await server.services.thread_repo.create(
    thread_id=ulid(),
    agent_id=agent_id,
    user_id=user_id,
    ...
)

# 事务 (自动管理)
async with server.services.pool.transaction():
    await server.services.agent_repo.update(agent_id, {"enabled": False})
    await server.services.audit_repo.record(actor, "agent.stop", agent_id)
```

---

## 8. Agent 系统

### 8.1 Agent 类型

| 类型 | 说明 |
|------|------|
| `expert` | 单个 AI 助手，拥有独立工作空间、模型、技能、记忆 |
| `team` | 多 Agent 协作组，由 host agent 协调子 agent |

### 8.2 AgentManager

`AgentManager` 是进程级单例，管理所有 `HarnessAgent` 实例：

```python
# 位于 infra/agents/manager.py

class AgentManager:
    def __init__(
        self,
        services: SharedServices,
        paths: PathLayout,
        config: OctopConfig,
        expert_catalog: ExpertCatalog | None = None,
        plugin_manager: PluginManager | None = None,
    ):
        ...

    # 生命周期
    async def boot(self) -> None: ...        # 启动所有已启用的 agent
    async def shutdown(self) -> None: ...    # 优雅关闭

    # CRUD
    async def create(self, spec: AgentCreateSpec) -> AgentRow: ...
    async def start(self, agent_id: str) -> None: ...
    async def stop(self, agent_id: str) -> None: ...
    async def reload(self, agent_id: str) -> None: ...

    # 运行时
    async def stream(self, agent_id: str, request: HarnessRequest) -> AsyncIterator: ...
    async def resume_hitl(self, ...) -> None: ...
```

### 8.3 Agent 启动流程

```python
# _start_agent() 内部流程

async def _start_agent(self, row: AgentRow) -> None:
    # 1. 构建 HarnessAgentConfig
    config = HarnessAgentConfig(
        agent_id=row.agent_id,
        system_prompt=row.system_prompt,
        model=row.default_model,
        workspace_dir=...,
        memory_backend=...,
        skill_packages=...,
        knowledge_bases=...,
        mcp_servers=...,
        security_policies=...,
        runtime_limits=...,
    )

    # 2. 解析后端存储规格
    backend_spec = resolve_agent_backend_spec(row, self.services)

    # 3. 注册到 HarnessAgentManager
    await self._harness_manager.register(config, backend_spec)

    # 4. 更新数据库状态
    await self.services.agent_repo.update(row.agent_id, {
        "last_state": "running",
    })
```

### 8.4 Agent 工作空间

每个 Agent 拥有独立的工作空间目录：

```
~/.octop/agents/<agent_id>/
├── SOUL.md              # Agent 人格定义
├── skills/              # 工作空间技能
│   └── my-skill/
│       └── SKILL.md
├── inbound/             # 聊天附件上传
├── .octop/              # 系统文件
│   ├── sessions/        # 会话 SQLite
│   └── auth/            # 认证令牌
└── ...                  # 其他工作空间内容
```

**重要规则：**

- 所有工作空间文件读写通过 `HarnessAgent.workspace` (`BackendWorkspace`)
- 不要直接使用 `agent.backend` 或 `Path.write_text()`
- 路径规则在 `BackendWorkspace` 中统一处理

### 8.5 专家系统 (Experts)

专家是预配置的 Agent 模板，位于 `infra/agents/experts/`：

```python
# 内置专家目录
class ExpertCatalog:
    def __init__(self, paths: PathLayout):
        self._bundled = self._load_bundled()  # 从 src/octop/infra/agents/experts/catalog/
        self._user = self._load_user()         # 从 ~/.octop/experts/

    def list_all(self) -> list[ExpertEntry]: ...
    def get(self, slug: str) -> ExpertEntry | None: ...

# 发布专家
async def publish_expert(
    services: SharedServices,
    source_agent_id: str,
    slug: str,
    name: str,
) -> PublishedExpertRow:
    ...
```

### 8.6 团队系统 (Teams)

团队 Agent 协调多个子 Agent：

```python
# infra/agents/teams/

class TeamManager:
    async def dispatch(self, team_agent_id: str, request: HarnessRequest) -> AsyncIterator:
        # 1. 解析团队成员
        members = await self._resolve_members(team_agent_id)
        # 2. 路由到合适的成员
        target = self._route_to_member(members, request)
        # 3. 委托执行
        async for event in target.stream(request):
            yield event
```

---

## 9. 消息处理流程

### 9.1 入口

消息处理由 `GlobalProcessor` (`infra/gateway/processor.py`) 统一处理，支持两种入口：

| 入口 | 来源 | 输出 |
|------|------|------|
| `__call__(msg)` | IM 渠道 (钉钉、飞书等) | `AsyncIterator[MessageEvent]` |
| `iter_turn_chunks(msg)` | Dashboard WebSocket/HTTP | `AsyncIterator[dict]` |

### 9.2 处理流程

```python
# 简化的消息处理流程

async def process_message(self, msg: InboundMessage) -> AsyncIterator[MessageEvent]:
    # 1. 解析 agent_id 和 user_id
    agent_id = msg.tenant_id
    user_id = await self._resolve_user(msg)

    # 2. 检查斜杠命令
    if msg.text.startswith("/"):
        async for event in self._handle_slash(msg):
            yield event
        return

    # 3. 检查 HITL 审批
    if self._is_hitl_resolution(msg):
        async for event in self._handle_hitl(msg):
            yield event
        return

    # 4. 获取或创建 Thread
    thread = await self._get_or_create_thread(agent_id, user_id, msg)

    # 5. 解析模型
    model = self._resolve_model(thread, msg, agent_id)

    # 6. 解析 MCP 连接器
    mcp_servers = await self._resolve_mcp_servers(agent_id, user_id, msg)

    # 7. 构建 HarnessRequest
    request = HarnessRequest(
        text=msg.text,
        model=model,
        thread_id=thread.thread_id,
        mcp_servers=mcp_servers,
        knowledge_bases=...,
        conversation_mode=thread.conversation_mode,
        ...
    )

    # 8. 流式调用 Agent
    async for chunk in self._agent_manager.stream(agent_id, request):
        yield self._project_chunk(chunk)

    # 9. 记录使用量和轨迹
    await self._record_usage(agent_id, user_id, thread, usage)
    await self._record_trajectory(agent_id, thread, events)
```

### 9.3 斜杠命令

斜杠命令由 `SlashDispatcher` (`infra/gateway/slash/dispatcher.py`) 路由：

```python
# 内置斜杠命令
CATALOG = {
    "help": HelpHandler,
    "model": ModelHandler,
    "reset": ResetHandler,
    "approve": ApproveHandler,   # HITL
    "reject": RejectHandler,     # HITL
    "pending": PendingHandler,   # HITL
    ...
}

# 添加自定义斜杠命令
class MyHandler(SlashHandler):
    name = "mycommand"
    description_key = "slash.catalog.mycommand.description"

    async def handle(self, ctx: SlashContext) -> AsyncIterator[str]:
        yield "Hello from my command!"
```

### 9.4 会话模式

支持三种会话模式 (per-thread)：

| 模式 | 说明 |
|------|------|
| `ask` | 默认问答模式 |
| `plan` | 规划模式 (禁用 MCP 和技能) |
| `craft` | 执行模式 (当 plan 生成后用户说"执行"时切换) |

---

## 10. API 层开发

### 10.1 添加新路由

```python
# 1. 在 api/routers/ 创建新文件 (或修改现有文件)
# api/routers/my_resource.py

from fastapi import APIRouter, Depends
from octop.infra.users.identity import User
from octop.api.deps import current_user, get_server
from octop.infra.server import OctopServer

router = APIRouter(prefix="/api/my-resource", tags=["my-resource"])

@router.get("/")
async def list_items(
    server: OctopServer = Depends(get_server),
    user: User = Depends(current_user),
):
    """列出当前用户的所有项目。"""
    items = await server.services.my_repo.list_for_user(user.id)
    return [item.to_dict() for item in items]

@router.post("/")
async def create_item(
    body: CreateItemRequest,
    server: OctopServer = Depends(get_server),
    user: User = Depends(current_user),
):
    """创建新项目。"""
    item = await server.services.my_repo.create(
        user_id=user.id,
        name=body.name,
        ...
    )
    return item.to_dict()
```

```python
# 2. 在 api/app.py 注册路由
from .routers import my_resource

app.include_router(my_resource.router)
```

```python
# 3. 在 api/openapi_meta.py 添加标签描述
TAG_DESCRIPTIONS = {
    ...
    "my-resource": "我的自定义资源管理",
}
```

### 10.2 请求/响应模型

```python
# 使用 Pydantic 定义请求/响应
from pydantic import BaseModel, Field

class CreateItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: str | None = Field(None, max_length=500, description="项目描述")

class ItemResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: str
```

### 10.3 错误处理

```python
from octop.infra.errors import OctopError, ErrorCode

# 抛出业务错误
raise OctopError(ErrorCode.ITEM_NOT_FOUND, "Item not found")

# 错误会自动映射为 HTTP 响应：
# {
#   "error": {
#     "code": "ITEM_NOT_FOUND",
#     "message": "Item not found"
#   }
# }
```

### 10.4 Agent 权限验证

```python
# 大多数 Agent 路由需要验证所有权
@router.get("/api/agents/{agent_id}/settings")
async def get_agent_settings(
    agent_id: str,
    server: OctopServer = Depends(get_server),
    user: User = Depends(current_user),
):
    row = await server.services.agent_repo.get(agent_id)
    if not row:
        raise OctopError(ErrorCode.AGENT_NOT_FOUND)
    _assert_agent_owner(row, user)  # 验证当前用户是 Agent 所有者

    # 继续处理...
```

### 10.5 WebSocket 路由

```python
# Dashboard 聊天使用 WebSocket
@router.websocket("/ws/chat/{agent_id}")
async def chat_ws(
    websocket: WebSocket,
    agent_id: str,
    server: OctopServer = Depends(get_server),
    user: User = Depends(ws_current_user),
):
    await websocket.accept()
    async for chunk in server.app_runtime.gateway.iter_turn_chunks(request):
        await websocket.send_json(chunk)
```

---

## 11. CLI 开发

### 11.1 添加新命令

```python
# 1. 在 cli/commands/ 创建新文件
# cli/commands/my_cmd.py

import click
from octop.cli.support.ctx import pass_ctx

@click.group("mycommand")
@pass_ctx
def my_command(ctx):
    """我的自定义命令组。"""
    pass

@my_command.command("list")
@pass_ctx
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def list_items(ctx, as_json):
    """列出所有项目。"""
    services = ctx.open_cli_services()
    items = services.my_repo.list_all()
    if as_json:
        click.echo(json.dumps([i.to_dict() for i in items]))
    else:
        for item in items:
            click.echo(f"{item.id}: {item.name}")
```

```python
# 2. 在 cli/registry.py 注册
COMMANDS = {
    ...
    "mycommand": "octop.cli.commands.my_cmd",
}
```

### 11.2 CLI 传输层

| 层级 | 何时使用 | 示例 |
|------|---------|------|
| **Offline** | 仅读写本地 SQLite | `user *`, `provider *`, `cron list/create/delete` |
| **Embedded** | 需要 harness/gateway 运行时 | `chats send/repl`, `agent create/start/stop` |
| **External** | 直接调用 OS/守护进程 | `models ollama-*`, channel QR bind |

```python
# Offline 命令 (直接操作数据库)
from octop.cli.support.db import open_cli_services

services = open_cli_services()
items = services.my_repo.list_all()

# Embedded 命令 (需要运行时)
from octop.cli.support.embedded_ops import with_embedded_server

async def my_embedded_command():
    async with with_embedded_server() as server:
        await server.app_runtime.agent_manager.start(agent_id)
```

---

## 12. 前端开发

### 12.1 开发环境

```bash
cd dashboard

# 安装依赖
npm install

# 启动开发服务器 (代理 /api 到后端 8088)
npm run dev     # 或 make dev-frontend

# 构建
npm run build   # tsc -b && vite build
```

### 12.2 添加新页面

```tsx
// 1. 创建页面组件
// dashboard/src/pages/MyResource/MyResourcePage.tsx

import { useEffect, useState } from "react";
import { myResourceApi } from "../../api/modules/myResource";
import { Item } from "../../api/types";

export function MyResourcePage() {
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    myResourceApi.list().then(setItems);
  }, []);

  return (
    <div>
      <h1>My Resources</h1>
      {items.map(item => (
        <div key={item.id}>{item.name}</div>
      ))}
    </div>
  );
}
```

```tsx
// 2. 添加路由
// dashboard/src/routes/routes.tsx

import { MyResourcePage } from "../pages/MyResource/MyResourcePage";

<Route path="my-resource" element={<MyResourcePage />} />
```

```tsx
// 3. 添加 API 模块
// dashboard/src/api/modules/myResource.ts

import { request } from "../request";
import { Item } from "../types";

export const myResourceApi = {
  list: () => request.get<Item[]>("/api/my-resource"),
  create: (data: CreateItemRequest) =>
    request.post<Item>("/api/my-resource", data),
};
```

### 12.3 组件规范

- 共享组件放在 `components/`
- 页面级组件放在 `pages/`
- 不要在页面中直接 `fetch`，使用 `api/` 模块
- 不要在 `components/` 中写页面逻辑

### 12.4 构建与部署

```bash
# 构建前端到 src/octop/dashboard/
make build-frontend

# 或完整构建 (前端 + wheel)
make build
```

**注意：** `src/octop/dashboard/` 是构建产物，不要直接编辑。源码在 `dashboard/`。

---

## 13. 国际化 (i18n)

### 13.1 后端国际化

后端翻译文件位于 `src/octop/i18n/`：

```
i18n/
├── en.json          # 英文 (fallback)
├── zh.json          # 中文
├── loader.py        # 加载器
└── domains/         # 按命名空间划分
    ├── errors.py    # 错误消息
    ├── tools.py     # 工具显示名
    ├── channel.py   # 渠道提示
    └── slash.py     # 斜杠命令
```

**添加翻译的步骤：**

```python
# 1. 在 en.json 和 zh.json 中添加相同的 key
# en.json
{
  "slash": {
    "catalog": {
      "mycommand": {
        "label": "My Command",
        "description": "Does something useful"
      }
    }
  }
}

# zh.json
{
  "slash": {
    "catalog": {
      "mycommand": {
        "label": "我的命令",
        "description": "做一些有用的事"
      }
    }
  }
}

# 2. 在代码中使用
from octop.i18n import tr

label = tr("slash.catalog.mycommand.label", locale)

# 或使用域辅助函数
from octop.i18n.domains.slash import tr

label = tr("mycommand.label", locale)
```

**语言解析顺序：**

1. 用户存储的偏好设置
2. `Accept-Language` 请求头 (Dashboard 发送)
3. 渠道类型提示 (IM 平台默认 `zh`，Telegram → `en`)

### 13.2 前端国际化

前端使用 i18next，翻译文件在 `dashboard/src/locales/`：

```tsx
import { useTranslation } from "react-i18next";

function MyComponent() {
  const { t } = useTranslation();
  return <h1>{t("myResource.title")}</h1>;
}
```

**注意：** 服务器拥有的文本 (工具名、API 错误) 的规范来源在后端 `src/octop/i18n/`，Dashboard 保持副本同步。测试会验证两端 key 一致。

---

## 14. 连接器与 MCP

### 14.1 连接器架构

连接器系统管理 MCP (Model Context Protocol) 与外部服务的集成：

```
infra/connectors/
├── catalog.py          # 静态连接器目录
├── service.py          # ConnectorService (CRUD + 凭证)
├── builder.py          # 构建 harness MCP 连接规格
├── crypto.py           # 凭证加密
├── custom_mcp.py       # 自定义 MCP 服务器
├── gateway/            # MCP 网关
│   ├── protocol.py     # JSON-RPC 协议处理
│   ├── registry.py     # 工具注册表
│   └── adapters/       # 13+ 厂商适配器
└── oauth/              # OAuth 流程
    ├── builtin.py      # 内置 OAuth 提供商
    ├── discovery.py    # Issuer 发现
    ├── mcp.py          # MCP OAuth
    └── pkce.py         # PKCE 实现
```

### 14.2 添加新连接器

```python
# 1. 在 catalog.py 中添加目录条目
CATALOG = [
    ConnectorCatalogEntry(
        slug="my-service",
        display_name="My Service",
        category="productivity",
        auth_kind=AuthKind.OAUTH2,
        mcp_mode=McpMode.REMOTE,
        remote_transport=RemoteTransport.STREAMABLE_HTTP,
        oauth_config=OAuthConfig(
            issuer="https://api.myservice.com",
            scopes=["read", "write"],
        ),
    ),
]

# 2. 如需自定义适配器，在 gateway/adapters/ 中创建
# gateway/adapters/my_service.py

class MyServiceAdapter(McpAdapter):
    name = "my_service"

    async def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="my_tool",
                description="Does something",
                input_schema={...},
            )
        ]

    async def call_tool(self, name: str, args: dict) -> ToolResult:
        if name == "my_tool":
            return await self._call_my_tool(args)
```

### 14.3 自定义 MCP 服务器

用户可通过 Dashboard 添加自定义 MCP 服务器：

```python
# 存储在 connectors 表中
# kind = "custom"
# config_json = {
#   "transport": "stdio" | "sse" | "streamable_http",
#   "command": "npx",
#   "args": ["-y", "@my/mcp-server"],
#   "env": {"API_KEY": "..."}
# }
```

---

## 15. 技能系统 (Skills)

### 15.1 技能定义

技能通过 `SKILL.md` 文件定义，支持 frontmatter：

```markdown
---
name: my-skill
description: Does something useful
version: 1.0.0
tools:
  - name: my_tool
    description: A useful tool
---

# My Skill

This skill provides the following capabilities:

## my_tool

Use this tool to do something useful.

**Input:**
- `query` (string): What to search for

**Output:**
- Results as JSON
```

### 15.2 技能来源

| 来源 | 位置 | 说明 |
|------|------|------|
| 工作空间 | `~/.octop/agents/<id>/skills/` | Agent 本地技能 |
| 全局包 | `~/.octop/skill_packages/` | 全局共享技能包 |
| SkillHub | 远程市场 | 从 SkillHub 下载安装 |

### 15.3 技能包管理

```python
# 创建技能包
from octop.infra.skills import SkillPackageStore

store = SkillPackageStore(root_path)
package = await store.create(
    name="my-package",
    description="My skill package",
    files={
        "my-skill/SKILL.md": skill_content,
        "my-skill/tools/helper.py": helper_code,
    },
)

# 安装到 Agent 工作空间
from octop.infra.skills.install import install_skill_to_workspace

await install_skill_to_workspace(
    workspace=agent.workspace,
    skill_slug="my-skill",
)
```

---

## 16. 定时任务 (Cron)

### 16.1 任务类型

| 类型 | 说明 |
|------|------|
| `text` | 推送固定文本 (提醒) |
| `agent` | 触发完整 Agent 对话回合 |

### 16.2 触发器格式

```python
# cron 表达式 (5 字段)
"cron:0 9 * * 1-5"    # 工作日 9:00

# 间隔
"interval:3600"        # 每小时

# 一次性
"date:2026-01-01T00:00:00"  # 指定时间
```

### 16.3 创建定时任务

```python
# 通过 API
POST /api/cron/jobs
{
  "agent_id": "agent_xxx",
  "schedule_spec": "cron:0 9 * * 1-5",
  "prompt": "Good morning! What's on my schedule today?",
  "task_type": "agent",
  "name": "Morning briefing",
  "enabled": true
}

# 通过 CLI
octop cron create --agent agent_xxx --schedule "cron:0 9 * * 1-5" \
  --prompt "Morning briefing" --type agent

# 通过 Agent 工具 (Agent 可自主管理 cron)
# Agent 可使用 cronjob_create, cronjob_update 等工具
```

### 16.4 CronManager

```python
# infra/cron/manager.py

class CronManager:
    async def boot(self) -> None:
        """启动 APScheduler 并加载所有已启用的任务。"""
        self._scheduler.start()
        jobs = await self._services.cron_job_repo.list_enabled()
        for job_row in jobs:
            self._register_job(job_row)

    async def reload_from_db(self) -> None:
        """从数据库重新加载 (迁移后无需重启)。"""
        ...
```

---

## 17. 用户与权限

### 17.1 用户角色

| 角色 | 权限 |
|------|------|
| `admin` | 全部权限，包括系统设置、用户管理、提供商管理 |
| `user` | 普通用户权限，管理自己的 Agent 和数据 |

### 17.2 权限系统

权限定义在 `infra/users/permissions.py`：

```python
# 权限类别
class PermissionCategory:
    SETTINGS = "settings"   # 个人设置
    CONTROL = "control"     # 功能控制
    ADMIN = "admin"         # 管理功能

# 权限定义
PERMISSIONS = [
    PermissionDef(
        key="channels",
        category=PermissionCategory.CONTROL,
        label_en="IM Channels",
        label_zh="IM 渠道",
    ),
    PermissionDef(
        key="providers",
        category=PermissionCategory.ADMIN,
        label_en="LLM Providers",
        label_zh="LLM 提供商",
    ),
    ...
]
```

### 17.3 用户策略

每个用户可配置命名策略：

| 策略 | 说明 |
|------|------|
| `workspace_root_dir` | 工作空间根目录限制 |
| `token_quota` | Token 配额 |
| `max_agents` | 最大 Agent 数量 |

```python
# 检查策略
from octop.infra.users.resource_policy import check_policy

await check_policy(
    services=services,
    user_id=user.id,
    policy_name="max_agents",
    current_count=current_agent_count,
)
```

### 17.4 SSO (OIDC)

```python
# 配置 SSO 提供商
POST /api/admin/sso/providers
{
  "display_name": "My Corp",
  "issuer": "https://idp.mycompany.com",
  "client_id": "octop",
  "client_secret": "...",
  "scopes": "openid profile email",
  "kind": "oidc"
}
```

---

## 18. 插件系统

### 18.1 插件结构

插件位于 `~/.octop/plugins/` 或项目 `plugins/` 目录：

```
my-plugin/
├── plugin.json          # 插件元数据
├── __init__.py          # 插件入口
└── tools/               # 插件工具
    └── my_tool.py
```

```json
// plugin.json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My custom plugin",
  "entry": "__init__.py"
}
```

### 18.2 PluginManager

```python
# infra/agents/plugins/

class PluginManager:
    async def seed_bundled(self) -> None:
        """将内置插件复制到 ~/.octop/plugins/"""
        ...

    async def load_installed(self, install_deps: bool = True) -> None:
        """加载所有已安装的插件"""
        ...

    def get_tools(self) -> list[BaseTool]:
        """获取所有插件提供的工具"""
        ...
```

### 18.3 示例插件

参见 `plugins/` 目录中的示例：

- `greeting/` — 问候技能
- `toolkit/` — 工具集
- `ui-card/` — UI 卡片渲染
- `turn-logger/` — 回合日志

---

## 19. 测试规范

### 19.1 测试布局

```
tests/
├── support/              # 测试辅助工具
│   ├── app.py           # FastAPI 测试客户端
│   ├── auth.py          # 认证辅助
│   ├── fakes.py         # 假对象
│   ├── harness.py       # Harness 测试辅助
│   ├── http.py          # HTTP 测试工具
│   └── scenarios.py     # 测试场景
├── unit/                 # 单元测试 (24 个子目录)
│   ├── agents/          # 50+ 测试文件
│   ├── api/             # 30+ 测试文件
│   ├── auth/            # 14 测试文件
│   └── ...
├── integration/          # 集成测试 (70+ 文件)
└── live/                 # 实时测试 (需要真实 LLM)
```

### 19.2 运行测试

```bash
# 完整测试套件 (排除 live)
uv run pytest -m "not live"

# 仅单元测试
uv run pytest tests/unit -x -q

# 仅集成测试
uv run pytest tests/integration -x -q

# 快速测试 (排除 live 和 slow)
make test-fast

# 实时测试 (需要 LLM API Key)
make test-live

# 受影响测试 (testmon)
make test-affected
```

### 19.3 编写测试

```python
# 单元测试示例
# tests/unit/agents/test_manager.py

import pytest
from octop.infra.agents.manager import AgentManager

@pytest.mark.asyncio
async def test_create_agent(services, tmp_path):
    manager = AgentManager(services, paths, config)
    spec = AgentCreateSpec(
        name="Test Agent",
        user_id=1,
        default_model="gpt-4",
    )
    agent = await manager.create(spec)
    assert agent.name == "Test Agent"
    assert agent.last_state == "running"

# 集成测试示例
# tests/integration/test_agents_api.py

@pytest.mark.asyncio
async def test_list_agents(client, auth_headers):
    resp = await client.get("/api/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
```

### 19.4 测试标记

| 标记 | 说明 |
|------|------|
| `live` | 需要真实 LLM/外部服务 |
| `slow` | 耗时测试 |
| `postgresql` | 需要 PostgreSQL |
| `posix_only` | 仅 POSIX 系统 |

```python
# 跨平台测试
import os

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX only")

@posix_only
def test_chmod(tmp_path):
    ...

# 使用 tmp_path 而非硬编码路径
def test_workspace(tmp_path):
    workspace = tmp_path / "agent" / "workspace"
    workspace.mkdir(parents=True)
    assert workspace.exists()
```

---

## 20. 代码质量与提交规范

### 20.1 代码质量检查

```bash
# 完整检查 (发布标准)
make all                # format-all + lint + typecheck + test

# 格式化
make format             # 后端 Ruff
make format-frontend    # 前端 Prettier

# Lint
make lint               # ruff check + format check
make lint-frontend      # ESLint + Prettier check

# 类型检查
make typecheck          # mypy --strict src/octop
make typecheck-frontend # tsc -b
```

### 20.2 Pre-commit Hook

```bash
# 安装 hook (必须)
make install-hooks

# Hook 执行流程：
# 1. make precommit (format-all + lint + typecheck + testmon)
# 2. 重新暂存格式化修改的文件
# 3. npm run build (dashboard)

# 紧急绕过 (不推荐)
SKIP_PRECOMMIT=1 git commit ...
```

### 20.3 分支策略

```
feature/* ──PR──► develop ──► release/x.y.z ──PR──► main ──tag v*──► publish
hotfix/* ──PR──► main (+ tag) and ──PR──► develop
```

| 分支 | 角色 |
|------|------|
| `main` | 生产源码真相来源；仅 release/hotfix 合并 |
| `develop` | 日常集成；feature PR 目标 |
| `release/x.y.z` | 临时发布快照 |
| `hotfix/*` | 紧急修复 |

**规则：**

- 永远不要直接将 `develop` 推送到 `main`
- `release/*` → `main` 使用 merge commit (非 squash)
- 生产 `v*` 标签在 `main` 合并后创建
- 日常功能开发：从 `develop` 分支，PR 到 `develop`

### 20.4 提交信息

遵循 Conventional Commits：

```
feat: add new connector for MyService
fix: resolve agent startup race condition
docs: update API reference
test: add integration tests for cron manager
refactor: simplify message processing pipeline
chore: bump dependencies
```

---

## 21. 常见二次开发场景

### 21.1 添加新的 LLM 提供商

```python
# 1. 在 infra/agents/providers/ 中添加提供商逻辑
# providers/my_llm.py

class MyLLMProvider:
    def __init__(self, config: ProviderConfig):
        self.api_key = config.api_key
        self.base_url = config.base_url

    async def chat(self, messages: list[Message], model: str) -> AsyncIterator[Chunk]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat",
                json={"model": model, "messages": messages},
                headers={"Authorization": f"Bearer {self.api_key}"},
            ) as resp:
                async for line in resp.aiter_lines():
                    yield parse_chunk(line)

# 2. 通过 API 或 Dashboard 添加提供商配置
POST /api/providers
{
  "name": "my-llm",
  "kind": "my_llm",
  "base_url": "https://api.myllm.com/v1",
  "api_key": "...",
  "models_json": [{"id": "my-model", "name": "My Model"}]
}
```

### 21.2 添加新的 IM 渠道

```python
# 1. 在 octop-gateway 中实现渠道适配器 (外部包)
# 2. 在 infra/gateway/channels/ 中添加注册逻辑
# 3. 在 api/routers/channels.py 中添加路由

@router.post("/api/channels/{channel_id}/webhook")
async def channel_webhook(
    channel_id: str,
    request: Request,
    server: OctopServer = Depends(get_server),
):
    channel = await server.services.channel_repo.get(channel_id)
    payload = await request.json()

    # 解析消息并发送到 Gateway
    inbound = parse_my_channel_message(payload)
    async for event in server.app_runtime.gateway(inbound):
        # 处理响应...
        pass
```

### 21.3 添加新的 API 端点

参见 [§10 API 层开发](#10-api-层开发)。

### 21.4 自定义前端页面

参见 [§12 前端开发](#12-前端开发)。

### 21.5 添加数据库迁移

参见 [§7.2 迁移系统](#72-迁移系统)。

### 21.6 添加新的斜杠命令

```python
# infra/gateway/slash/handlers/my_command.py

from octop.i18n.domains.slash import tr

class MyCommandHandler(SlashHandler):
    name = "mycommand"

    @property
    def label(self) -> str:
        return tr("mycommand.label", self.locale)

    @property
    def description(self) -> str:
        return tr("mycommand.description", self.locale)

    async def handle(self, ctx: SlashContext) -> AsyncIterator[str]:
        yield "Processing..."
        result = await self._do_something(ctx)
        yield f"Done: {result}"

# 在 catalog.py 中注册
CATALOG["mycommand"] = MyCommandHandler
```

### 21.7 添加新的 Agent 工具

```python
# 方式 1: 通过技能 (推荐)
# 在 Agent 工作空间创建 SKILL.md

# 方式 2: 通过插件
# plugins/my_tools/__init__.py

from langchain.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Does something useful with the query."""
    return f"Result for: {query}"

def get_tools() -> list:
    return [my_custom_tool]
```

---

## 22. FAQ

### Q: 如何在不修改上游代码的情况下扩展 Octop？

**A:** 推荐的扩展点：

1. **插件系统** — 添加自定义工具
2. **技能系统** — 通过 SKILL.md 定义新能力
3. **连接器** — 添加新的 MCP 集成
4. **API 路由** — fork 后添加自定义端点
5. **前端页面** — fork 后添加自定义 UI

### Q: 如何选择 SQLite vs PostgreSQL？

**A:**

- **SQLite**：开发、测试、小规模部署 (< 50 用户)、快速原型
- **PostgreSQL**：生产环境、多用户、需要向量搜索 (pgvector)、高并发

### Q: 如何调试 Agent 问题？

**A:**

```bash
# 查看 Agent 日志
tail -f ~/.octop/logs/octop.log

# 检查 Agent 状态
octop agent list --json

# 重启 Agent
octop agent restart <agent_id>

# 启用调试日志
OCTOP_LOG_LEVEL=debug octop run
```

### Q: 如何备份和恢复？

**A:**

```bash
# 手动备份
octop backup create

# 自动备份 (在 config.json 中配置)
{
  "backup": {
    "auto_enabled": true,
    "schedule": "cron:0 4 * * *",
    "retention_count": 7
  }
}

# 恢复
octop backup restore <backup_file>
```

### Q: 如何贡献代码到上游？

**A:** 参见 [CONTRIBUTING.md](../CONTRIBUTING.md)。关键点：

1. 从 `develop` 分支创建 feature 分支
2. 确保 `make all` 通过
3. PR 到 `develop`
4. 更新 CHANGELOG.md

---

> **更多信息：**
>
> - API 文档：启动后访问 `/api/docs` (需 `enable_api_docs: true`)
> - 架构文档：`docs/architecture.md`
> - 配置参考：`docs/configuration.md`
> - CLI 参考：`docs/cli.md`
