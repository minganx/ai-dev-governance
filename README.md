# AI 开发治理

## 项目介绍

本仓库集中维护可在多台设备复用的 AI 开发规则、通用 Skill、开发工具默认配置和 Commit message Hook，兼容 Claude Code、Codex、Cursor、Pi 和 oh-my-pi，支持 macOS、Windows、Linux。

仓库自维护的规则和 Skill 是设备受管文件的来源，安装、更新和卸载采用文件复制，不依赖符号链接权限。第三方 Skill、插件和扩展只保存来源及官方安装命令，由对应工具管理版本；仓库不保存其正文、安装缓存、Token、API Key、OAuth、MCP 凭据、会话或缓存。

## 管理范围

- 全局 AI 开发规则和通用 Skill。
- Claude Code、Codex、Cursor、Pi、oh-my-pi 的规则入口、Skill 和 MCP 配置同步。
- Git 全局忽略文件和 Ruff 用户级默认配置。
- 项目级 Agent、Git、`pyproject.toml`、Pyright、Prettier、pre-commit 等个人配置模板。
- Commit 正文最低质量检查器及 pre-commit Hook 声明。
- 跨平台安装、增量更新、漂移检查和卸载工具。
- 选择 Pi 时，通过 Pi CLI 管理 `npm:@rahularya01/pi-cursor` 和 `npm:pi-mcp-adapter`。

设备管理工具只处理本仓库明确映射的自维护文件。设备上已有的第三方 Skill、插件、工具配置和凭据不属于复制范围，不会因更新或卸载被清理；第三方资源通过各工具的安装和更新命令维护。

## 相关路径与文件清单

### 仓库源文件

| 路径                            | 用途                           |
| ------------------------------- | ------------------------------ |
| `config/agents/AGENTS.md`       | 全局开发规则唯一源文件         |
| `config/agents/skills/`         | 自维护通用 Skill 唯一源文件    |
| `config/agents/README.md`       | 自维护与第三方资源边界         |
| `config/tool-entries/`          | Agent 专属规则薄入口           |
| `config/git/gitignore_global`   | Git 全局忽略规则               |
| `config/ruff/ruff.toml`         | Ruff 用户级默认配置            |
| `config/mcp/servers.json`       | 跨 Agent MCP 非敏感配置源      |
| `config/mcp/context7_mcp.py`    | Context7 本地密钥启动器        |
| `dev-configs/agents/`           | 项目级 Agent 模板 |
| `dev-configs/git/`              | 项目 Git 配置模板              |
| `dev-configs/python/`           | Python 项目配置模板            |
| `dev-configs/prettier/`         | Prettier 配置模板              |
| `dev-configs/pre-commit/`       | pre-commit 配置模板            |
| `docs/toolchain.md`             | 开发工具链配置边界             |
| `hooks/check_commit_message.py` | Commit 正文最低质量检查器      |
| `.pre-commit-hooks.yaml`        | pre-commit Hook 声明           |
| `tools/manage.py`               | 安装、更新、检查和卸载核心逻辑 |
| `tools/install.*`               | macOS、Linux、Windows 安装入口 |
| `tools/update.*`                | macOS、Linux、Windows 更新入口 |
| `tools/uninstall.*`             | macOS、Linux、Windows 卸载入口 |

### 设备受管目标

| 目标路径                                      | 范围                    |
| --------------------------------------------- | ----------------------- |
| `~/.config/agents/`                           | 共享规则和 Skill 副本   |
| `~/.claude/CLAUDE.md`、`~/.claude/skills/`    | Claude Code             |
| `~/.codex/AGENTS.md`、`~/.codex/skills/`      | Codex                   |
| `~/.cursor/skills/`                           | Cursor                  |
| `~/.pi/agent/AGENTS.md`、`~/.agents/skills/`  | Pi                      |
| `~/.omp/agent/AGENTS.md`、`~/.omp/agent/skills/` | oh-my-pi |
| `~/.omp/agent/mcp.json` | oh-my-pi 原生 MCP |
| `~/.claude.json`、`~/.codex/config.toml`      | Claude、Codex MCP       |
| `~/.cursor/mcp.json`                          | Cursor MCP              |
| `~/.config/mcp/mcp.json`                      | Pi 共享 MCP             |
| `~/.config/agents/mcp/`                       | MCP 启动器及本地密钥    |
| `npm:@rahularya01/pi-cursor`                  | Pi 的 Cursor 订阅支持   |
| `npm:pi-mcp-adapter`                          | Pi 的 MCP 支持          |
| `~/.gitignore_global`                         | Git 全局忽略            |
| `~/.config/ruff/ruff.toml`                    | macOS、Linux Ruff 默认值 |
| `%APPDATA%\ruff\ruff.toml`                    | Windows Ruff 默认值      |

Pi 原生发现 `~/.agents/skills/`，因此不向 `~/.pi/agent/skills/` 重复复制通用 Skill。

## 初次使用

### macOS、Linux

```bash
git clone https://github.com/minganx/ai-dev-governance.git
cd ai-dev-governance
./tools/install.sh
git config --global core.excludesFile ~/.gitignore_global
python3 tools/manage.py check
```

### Windows

```powershell
git clone https://github.com/minganx/ai-dev-governance.git
Set-Location ai-dev-governance
.\tools\install.ps1
git config --global core.excludesFile "$HOME/.gitignore_global"
py -3 .\tools\manage.py check
```

默认安装全部 Agent 支持。使用可重复的 `--agent` 仅安装指定 Agent；可选值为 `claude`、`codex`、`cursor`、`pi`、`omp`。首次配置 MCP 时，安装器会提示先将 Context7 API Key 保存到密码管理器，再以不回显方式粘贴。Key 只写入设备文件 `~/.config/agents/mcp/context7-api-key`（macOS、Linux 权限为 `0600`），不会进入仓库或 Agent MCP 配置。

选择 Pi 前必须已安装可执行的 Pi CLI，安装器会继续通过 Pi 官方命令安装 `pi-cursor` 和 `pi-mcp-adapter` Package：

```bash
./tools/install.sh --agent pi
./tools/install.sh --agent codex --agent cursor
```

oh-my-pi CLI 按[官方仓库](https://github.com/can1357/oh-my-pi)安装。本仓库管理默认目录 `~/.omp/agent/` 下的规则、Skill 和原生 MCP，不管理自定义目录、XDG 目录或命名 Profile，也不为 oh-my-pi 安装 Pi Package。

```bash
./tools/install.sh --agent omp
./tools/update.sh --agent omp
python3 tools/manage.py check --agent omp
./tools/uninstall.sh --agent omp
```

Archify 的来源和全局安装命令见 [第三方 Skill](config/agents/README.md#archify)。

指定 Agent 时仍会安装共享规则、共享 Skill、Git 全局忽略和 Ruff 默认配置。目标文件存在不同内容时，安装器不会覆盖；确认以仓库版本为准后使用 `--force`。

```bash
./tools/install.sh --agent pi --force
```

## 更新使用

拉取仓库后执行增量更新：

```bash
git pull --ff-only
./tools/update.sh
python3 tools/manage.py check
```

Windows：

```powershell
git pull --ff-only
.\tools\update.ps1
py -3 .\tools\manage.py check
```

更新会跳过内容一致的文件，安装新增或设备缺失的自维护文件。例如在 `config/agents/skills/` 新增一个自行编写的笔记 Skill 后，执行更新即可将完整 Skill 目录（包括 `scripts/`、`references/`、`assets/`）复制到各 Agent 的受管目录。第三方 Skill、插件和扩展不经过复制更新，使用 `config/agents/README.md` 中对应工具的官方命令安装和更新。

如果设备文件与仓库版本不同，更新器会保留设备文件、继续更新其他安全项，并以状态码 `2` 报告差异。确认全部差异都应以仓库版本覆盖时使用：

```bash
./tools/update.sh --force
```

MCP 同步管理 Context7 和 DeepWiki，并保留各工具中其他 MCP。Context7 通过本地启动器读取设备 Key，不把 Key 写入进程参数。非交互环境可临时提供 `CONTEXT7_API_KEY`；安装器只保存其值，不输出内容。

选择 Pi 时，更新器同时更新 `pi-cursor` 和 `pi-mcp-adapter`，检查器通过 `pi list` 验证 Package。更新和检查同样支持限定 Agent：

```bash
./tools/update.sh --agent pi
python3 tools/manage.py check --agent pi
```

## 卸载

卸载全部受管文件：

```bash
./tools/uninstall.sh
```

Windows：

```powershell
.\tools\uninstall.ps1
```

只卸载指定 Agent 的规则入口和 Skill，不删除共享配置或其他 Agent 文件：

```bash
./tools/uninstall.sh --agent pi
./tools/uninstall.sh --agent claude --agent codex
```

卸载器只删除本仓库映射的文件和 MCP Server 条目并清理空目录，不处理设备上的额外配置。卸载 Pi 支持时同时移除 `pi-cursor` 和 `pi-mcp-adapter`。Context7 API Key 默认保留，便于重新安装；需要彻底清理时手工删除 `~/.config/agents/mcp/context7-api-key`。受管文件或 MCP 条目存在本地差异时默认拒绝删除；确认无需保留后使用 `--force`。不指定 `--agent` 时会同时删除共享配置。
