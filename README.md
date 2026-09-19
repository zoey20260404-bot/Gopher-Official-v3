# Gopher Agent

Gopher Agent 是一个用于学习和交付企业级 Python Agent 的独立工程。项目采用
FastAPI、Pydantic、LangGraph、SQLAlchemy、Redis 和 PostgreSQL/pgvector，首个业务版本将实现
“路由 → 岗位查询工具 → SSE 响应 → checkpoint”的最小垂直链路。

## 本地启动

```powershell
uv venv E:\python\venvs\Gopher-Official-v3 --python 3.12
& E:\python\venvs\Gopher-Official-v3\Scripts\Activate.ps1
uv sync --active --all-groups
Copy-Item .env.example .env
uvicorn gopher_agent.main:app --reload
```

上述命令将本地虚拟环境放在 `E:\python`，项目目录只保留源码和配置。

访问：

- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

## 质量检查

```powershell
ruff format --check .
ruff check .
mypy
pytest
```

## 项目结构

```text
src/gopher_agent/
├── agents/          # LangGraph graph 与 agent node
├── api/             # HTTP router 与 schema
├── core/            # 配置、日志和通用基础能力
├── models/          # ORM model
├── repositories/    # 数据访问抽象与实现
└── tools/           # Agent 可调用工具
tests/
├── integration/     # 跨组件测试
└── unit/            # 隔离依赖的快速测试
```

## 当前能力

- `GET /api/v1/health`：进程存活检查；
- `POST /auth/register`：注册用户；
- `POST /auth/login`：登录并获取 JWT access token；
- `GET /api/v1/profile`：读取 Bearer token 对应的当前用户档案；
- PostgreSQL/pgvector ORM、Alembic migration 与异步 Repository 基础。

本地调用认证接口前，需要在 `.env` 中设置至少 32 字符的 `JWT_SECRET`，并执行：

```powershell
uv run alembic upgrade head
```

各阶段需求及技术设计见 [`docs/feat001`](docs/feat001)、[`docs/feat002`](docs/feat002) 和
[`docs/feat003`](docs/feat003)。
