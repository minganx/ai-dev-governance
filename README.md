# AI 开发治理

## 项目介绍

本仓库集中维护可在多台设备复用的 AI 开发规则、通用 Skill、开发工具默认配置和 Commit message Hook，兼容 Cursor、Codex 和 Claude Code，支持 macOS、Windows、Linux。

仓库自维护的规则和 Skill 是设备受管文件的来源，安装、更新和卸载采用文件复制，不依赖符号链接权限。第三方 Skill、插件和扩展只保存来源及官方安装命令，由对应工具管理版本；仓库不保存其正文、安装缓存、Token、API Key、OAuth、MCP 凭据、会话或缓存。

## 管理范围

- 全局 AI 开发规则和通用 Skill。
- Cursor、Codex、Claude Code 的规则入口、Skill 和 MCP 配置同步。
- Git 全局忽略文件和 Ruff 用户级默认配置。
- 项目级 Agent、Git、`pyproject.toml`、Pyright、Prettier、pre-commit 等个人配置模板。
- Commit 正文最低质量检查器及 pre-commit Hook 声明。
- 跨平台安装、增量更新、漂移检查和卸载工具。

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
| `~/.config/agents/`                           | 所选共享规则、Skill 副本和安装选择记录 |
| `~/.claude/CLAUDE.md`、`~/.claude/skills/`    | Claude Code             |
| `~/.codex/AGENTS.md`、`~/.codex/skills/`      | Codex                   |
| `~/.cursor/skills/`                           | Cursor                  |
| `~/.claude.json`、`~/.codex/config.toml`      | Claude、Codex MCP       |
| `~/.cursor/mcp.json`                          | Cursor MCP              |
| `~/.gitignore_global`                         | Git 全局忽略            |
| `~/.config/ruff/ruff.toml`                    | macOS、Linux Ruff 默认值 |
| `%APPDATA%\ruff\ruff.toml`                    | Windows Ruff 默认值      |

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

安装无需拼接配置参数，直接运行脚本，在终端依次输入数字选择：

1. Agent：Claude Code、Codex、Cursor，可多选。
2. Skill：按仓库当前的通用 Skill 清单逐项选择。
3. MCP：选择需要同步的 Server，目前为 DeepWiki。
4. 开发工具配置：全局 Agent 规则、Git 全局忽略、Ruff 默认配置，可独立选择。
5. 已有不同内容的处理方式：保留已有内容，或以仓库内容覆盖。

多选编号用空格或逗号分隔，例如 `1 3` 或 `1,3`；菜单还提供全选、`0` 跳过和取消安装的数字选项。空输入、名称和无效数字会要求重新选择。跳过 Agent 时不再显示 Skill、MCP 菜单，仍可选择 Git、Ruff 等配置。所有菜单选择完成后才开始写入；取消、输入结束或中断会直接退出。

安装不接受 `--agent`、`--skill`、`--mcp`、`--force` 等配置参数，也不支持非交互安装。保留已有内容时，文件冲突会阻止文件安装；需要覆盖时重新运行安装脚本，在菜单中选择覆盖。

选择记录保存在设备的 `~/.config/agents/install-selection.json`，供更新、检查和卸载读取。再次安装会用本次选择替换记录，未选中的已有文件不会被自动删除。共享规则、共享 Skill、Git 和 Ruff 配置只安装所选项，Skill 的支持文件随选中的 Skill 一起复制。

Context7 在安装和更新时只输出一次安装文档提示，独立安装方式见 [Context7 安装说明](docs/context7.md)。Archify 等第三方资源继续由原工具管理，见 [第三方 Skill](config/agents/README.md#archify)。

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

更新会沿用设备保存的安装选择，跳过内容一致的文件，补齐所选配置缺失的文件。所选 Skill 的完整目录（包括 `scripts/`、`references/`、`assets/`）一起更新；新增 Skill 不会自动安装，需要重新运行安装菜单选择。第三方 Skill、插件和扩展不经过复制更新，使用 `config/agents/README.md` 中对应工具的官方命令安装和更新。

如果设备文件与仓库版本不同，更新器会保留设备文件、继续更新其他安全项，并以状态码 `2` 报告差异。确认全部差异都应以仓库版本覆盖时使用：

```bash
./tools/update.sh --force
```

MCP 同步仅管理 DeepWiki，并保留各工具中其他 MCP，包括已有 Context7 配置。安装、更新和卸载会删除已退役的 `codegraph` MCP 条目；`check` 会报告其残留。更新和检查默认沿用安装选择，也可通过 `--agent` 缩小到已选择的 Agent。旧设备没有选择记录时，仍按原行为管理全部三个 Agent 和受管配置；可重新运行安装菜单明确范围。跳过 MCP 后，更新、检查和卸载均不操作 MCP 配置。

## 卸载

卸载安装选择中的全部受管文件：

```bash
./tools/uninstall.sh
```

Windows：

```powershell
.\tools\uninstall.ps1
```

只卸载指定 Agent 的已选规则入口、Skill 和 MCP，不删除共享配置或其他 Agent 文件；成功后从安装选择中移除该 Agent：

```bash
./tools/uninstall.sh --agent cursor
./tools/uninstall.sh --agent claude --agent codex
```

卸载器只删除本仓库映射的文件和受管 MCP Server 条目并清理空目录，不处理设备上的额外配置。受管文件或 MCP 条目存在本地差异时默认拒绝删除；确认无需保留后使用 `--force`。不指定 `--agent` 时会同时删除所选共享配置和安装选择记录。历史安装留下的其他 Agent 文件、Context7 启动器和密钥不再纳管，需要清理时自行处理。
