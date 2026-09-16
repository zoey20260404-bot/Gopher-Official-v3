# feat001：问题与解决记录

## 1. Windows 中 `python` 命令存在但 Python 未安装

### 现象

`Get-Command python` 指向 `Microsoft\WindowsApps\python.exe`，但 `python --version` 不返回有效版本；同时 `py` 和 `pip` 均不存在。

### 原因

该文件是 Microsoft Store 的 App Execution Alias，不是可用的 Python runtime。

### 解决方案

使用机器上已有的 `uv` 安装并固定 Python 3.12，再由 `uv` 在项目内创建 `.venv`。日常命令统一使用 `uv run`，避免依赖系统 PATH、全局 pip 或手动激活虚拟环境。

### 验证

已通过 `uv` 安装 CPython 3.12.13，并成功创建项目内 `.venv`。

## 2. sandbox 无法读取用户级 uv cache

### 现象

首次执行 `uv run` 时，sandbox 对 `C:\Users\14790\AppData\Local\uv\cache` 返回“拒绝访问”。

### 解决方案

依赖安装阶段按授权让 `uv` 使用用户级 cache；项目验证阶段直接调用 `.venv\Scripts` 中的工具。
这不会影响开发者在正常 PowerShell 中使用 README 所列的 `uv run` 命令。

## 3. 自动化执行环境限制用户 cache 与 Git 元数据写入

### 现象

自动化 sandbox 中安装 pre-commit hook 和写入 Git index 时出现 Windows `PermissionError`。

### 解决方案

这些操作只涉及当前仓库 `.git` 和当前用户的 pre-commit cache，因此在明确授权后提升权限执行。
项目源码、依赖配置与测试结果不受影响。

## 4. Windows Store alias 遮蔽真实 Python

### 现象

执行 `uv python install 3.12 --default` 后，`where python` 同时找到 WindowsApps 占位符和
`C:\Users\14790\.local\bin\python.exe`，但占位符位于 PATH 前方，导致 `python --version` 无有效输出。

### 解决方案

保留原有 PATH 内容，仅将 `C:\Users\14790\.local\bin` 移到当前用户 PATH 首位。新终端中
`python` 和 `python3` 均解析到 uv 管理的 CPython 3.12.13，`python -m pip` 可正常使用。

## 5. Python 开发环境不应占用 C 盘

### 需求变化

用户要求 Python runtime、命令入口、包管理缓存和开发工具缓存统一安装到 `E:\python`。

### 解决方案

设置用户级 `UV_PYTHON_INSTALL_DIR`、`UV_PYTHON_BIN_DIR`、`UV_CACHE_DIR`、`UV_TOOL_DIR`、
`UV_TOOL_BIN_DIR`、`PYTHONUSERBASE`、`PIP_CACHE_DIR` 和 `PRE_COMMIT_HOME`，然后在 E 盘重新安装
Python 3.12.13，并按 `uv.lock` 在 `E:\python\venvs\Gopher-Official-v3` 建立外置虚拟环境。

确认 E 盘全局 Python、pip、pre-commit 和项目测试全部正常后，删除 C 盘旧 runtime、uv cache、
pre-commit cache 及三个旧 Python shim。旧 cache 已删除且不可直接恢复，但均可由工具重新生成。

## 6. 项目目录混入本地环境和临时产物

### 现象

项目根目录出现 `.venv`、`.coverage`、`.mypy_cache`、`.ruff_cache`、`pytest-cache-files-*`，源码与
测试目录还生成了多个 `__pycache__`。

### 解决方案

先在 `E:\python\venvs\Gopher-Official-v3` 建立外置环境并完成全部质量验证，再将 Git hook 切换到
外置环境。确认可用后删除项目内虚拟环境、测试/检查缓存、覆盖率文件及字节码目录，只保留源码、
测试、配置、migration、需求文档和 Git 元数据。

同时设置 `RUFF_CACHE_DIR`、`MYPY_CACHE_DIR`、`COVERAGE_FILE` 和 `PYTHONPYCACHEPREFIX` 到
`E:\python\cache`，防止后续质量检查再次污染项目目录。
