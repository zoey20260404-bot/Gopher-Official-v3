# feat001：Python Agent 项目前期工程搭建需求

## 1. 背景

当前目录只有 Python 入门教程、Python Agent 技术方向讨论和项目规则，没有可运行的 Python
环境、工程骨架或 Git 仓库。开发者需要在 Windows 环境从零开始 Python Agent 开发，并希望项目从第一天就具备企业级可维护性。

## 2. 目标

- 建立稳定、可复现的 Python 3.12 本地开发环境；
- 将 Python runtime、命令入口与开发工具缓存统一放置在 `E:\python`，避免占用系统盘；
- 建立职责清晰、便于扩展的 `src` 工程目录；
- 引入 FastAPI、Pydantic、LangGraph、SQLAlchemy、Alembic、Redis 等主线技术；
- 建立格式化、静态检查、类型检查、自动测试和覆盖率门禁；
- 提供容器化与 CI 基线；
- 将原始讨论文档和全部初始化产物纳入 Git 管理。

## 3. 本需求范围

### 包含

- Python、虚拟环境和依赖锁定；
- Git 仓库及 `feature/zoey/feat001` 需求分支；
- 应用分层目录、配置模块、数据库会话基础设施；
- FastAPI 应用工厂和健康检查接口；
- 单元测试、集成测试及基础覆盖率；
- Dockerfile、Docker Compose、GitHub Actions；
- README、配置示例、需求文档、技术文档和问题记录。

### 不包含

- LLM provider 的真实接入与密钥配置；
- `/chat`、SSE、Router、Advisor 和岗位查询业务实现；
- 数据表设计及首个业务 migration；
- 生产部署和生产数据访问。

## 4. 验收标准

1. `uv sync --all-groups` 可创建环境并按 lockfile 安装依赖；
2. `uv run uvicorn gopher_agent.main:app` 可启动应用；
3. `GET /api/v1/health` 返回 HTTP 200 和 `{"status":"ok"}`；
4. Ruff format、Ruff lint、mypy 和 pytest 全部通过；
5. 测试覆盖率不低于 80%；
6. `.env`、虚拟环境、缓存和构建产物不会进入 Git；
7. Docker Compose 包含 app、PostgreSQL/pgvector 与 Redis；
8. CI 在 push 和 pull request 时执行完整质量门禁。
9. 新开的 CMD/PowerShell 中 `python`、`python3` 和 `python -m pip` 均使用 E 盘安装。

## 5. 后续需求

下一个需求建议实现最小业务链路：`POST /chat → LangGraph Router → Advisor →
query_positions tool → SSE → checkpoint`，并为 LLM 和数据库边界提供 deterministic test。
