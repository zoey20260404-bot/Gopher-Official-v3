# feat001：Python Agent 工程初始化技术设计

## 1. 技术决策

### Python 与依赖管理

- 固定 Python `3.12`，兼顾生态成熟度与现代类型/异步能力；
- 使用 `uv` 将 CPython 3.12 安装到 `E:\python\versions`，并注册为当前 Windows 用户的默认 Python；
- Python shim 位于 `E:\python\bin`，CMD 和 PowerShell 均可直接调用；
- uv、pip 与 pre-commit cache 分别位于 `E:\python\cache`、`E:\python\pip-cache` 和
  `E:\python\pre-commit`；
- 当前项目虚拟环境位于 `E:\python\venvs\Gopher-Official-v3`，不在项目目录保存 `.venv`；
- Ruff、mypy、coverage 和 Python bytecode 通过用户环境变量统一写入 `E:\python\cache`；
- 使用 `uv` 管理 Python、项目虚拟环境、依赖解析和 lockfile；
- 运行依赖和开发依赖分组，生产镜像不安装开发工具。

### 应用结构

采用 `src layout`，避免从仓库根目录意外导入未安装源码：

```text
src/gopher_agent
├── api             HTTP 边界、router 和 schema
├── core            配置、数据库和横切能力
├── agents          LangGraph graph/node
├── tools           Agent tool 白名单实现
├── models          SQLAlchemy model
└── repositories    数据访问层
```

应用通过 `create_app()` 工厂创建，测试可获得隔离实例。API 统一使用 `/api/v1` 前缀，为未来不兼容升级保留空间。

### 配置与安全

- Pydantic Settings 从环境变量或本地 `.env` 加载强类型配置；
- 仓库只提交 `.env.example`，不提交真实密钥；
- LLM 配置先保留空值，真实接入在后续需求处理；
- Docker Compose 中的数据库口令仅用于本地开发示例。

### 数据访问

- SQLAlchemy 2.x async engine 与 `async_sessionmaker`；
- FastAPI dependency 以 async generator 控制 session 生命周期；
- Alembic 共用应用的 `DATABASE_URL` 与 ORM metadata；
- 本需求不建立业务表，防止在需求尚未明确时固化 schema。

### 质量门禁

| 工具 | 职责 |
| --- | --- |
| Ruff format | 统一代码格式 |
| Ruff lint | import、缺陷模式、async 与安全规则 |
| mypy strict | 静态类型检查 |
| pytest | 单元与集成测试 |
| pytest-cov | statement/branch 覆盖率，门槛 80% |
| pre-commit | 本地提交前快速校验 |
| GitHub Actions | 远端一致性验证 |

## 2. 启动链路

```text
uvicorn
  → gopher_agent.main:app
  → create_app()
  → Settings
  → 注册 /api/v1 router
  → /health
```

健康检查当前只代表应用进程存活。PostgreSQL、Redis 和 LLM readiness 检查应单独设计，避免依赖故障使 liveness 失效。

## 3. 容器设计

- 应用镜像基于 `python:3.12-slim`；
- 依赖严格按 `uv.lock` 安装；
- 应用以非 root UID 运行；
- Compose 使用 pgvector PostgreSQL 镜像和 Redis 7；
- 服务依赖通过 healthcheck 编排，仅用于本地开发。

## 4. 验证命令

```powershell
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## 5. 实施记录

- 2026-09-16：完成方案确认并初始化 `feature/zoey/feat001` 分支；
- 2026-09-16：建立项目结构、配置、健康检查、测试、容器与 CI 基线；
- 2026-09-16：通过 `uv` 安装 CPython 3.12.13，生成 `.venv` 与 `uv.lock`，解析并安装 82 个包；
- 2026-09-16：将 Python runtime、bin、uv/pip/pre-commit cache 迁移到 `E:\python`，并从 C 盘清理旧副本；
- 2026-09-16：基于 E 盘 runtime 建立外置项目虚拟环境，CMD/PowerShell 全局验证 Python 3.12.13 与 pip 26.0.1；
- 2026-09-16：清理项目内 `.venv`、coverage、Ruff/mypy/pytest 临时目录及全部 `__pycache__`；
- 2026-09-16：mypy strict、Ruff lint 与 4 条 pytest 测试通过，综合覆盖率为 96.36%；
- 2026-09-16：实际启动 Uvicorn 并请求 `/api/v1/health`，获得 HTTP 200 与 `{"status":"ok"}`。
