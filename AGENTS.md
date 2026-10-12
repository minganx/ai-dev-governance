# AI 开发治理仓库规则

本仓库维护跨项目共享的开发规则、通用 Skill、Git Hook 和跨平台安装工具，仅支持 Cursor、Codex 和 Claude Code。

## 规则优先级

1. 用户当前明确指令
2. 本仓库 `AGENTS.md`
3. `config/agents/AGENTS.md`
4. 工具默认行为

## 仓库结构

- `config/agents/`：全局开发规则和自维护通用 Skill。
- `config/tool-entries/`：工具专属规则薄入口。
- `config/mcp/servers.json`：受管 MCP 定义，目前仅包含 DeepWiki。
- `config/git/`、`config/ruff/`：设备级默认配置源文件。
- `dev-configs/`：手工复制到项目的配置模板，不自动安装到用户目录。
- `tools/manage.py`：安装、更新、检查和卸载的共享实现；Shell、PowerShell 脚本只做入口适配。
- `hooks/`：Commit message 检查器；`tests/`：安装器和 Hook 的单元测试。
- `docs/`、`README.md`：工具边界、安装文档和使用说明。

## 维护规则

- `config/agents/` 是全局规则和通用 Skill 的唯一源文件。
- 根目录 `AGENTS.md` 是本项目规则来源；`CLAUDE.md`、`.codex/AGENTS.md` 只做加载适配，不复制规则正文。
- `hooks/` 只实现可机械检查的 Git 规则，不判断业务语义。
- `tools/` 必须兼容 macOS、Windows、Linux，不写死用户目录。
- Python 代码兼容 Python 3.9 及以上版本；优先使用标准库，新增依赖必须有明确必要性。
- 不提交 Token、API Key、OAuth、MCP 凭据、权限记录、缓存、会话或本地日志。
- 修改通用 Skill 时保持简洁；项目差异留在项目仓库的增量 Skill。
- 第三方 Skill、插件和扩展由原工具管理，仓库只记录来源及安装文档，不复制其正文或缓存。
- 修改管理范围、路径或交互流程时，同步更新 README、相关文档和测试。

## 安装与管理约定

- 安装通过终端数字菜单选择 Agent、Skill、MCP、其他工具配置及覆盖策略，不使用配置参数拼接安装范围。
- 多选菜单支持全选和跳过；无效输入重新选择。取消、EOF 或菜单输入中断必须在写入配置前退出。
- 跳过 Agent 时不安装 Agent Skill 或 MCP；跳过某种配置后，后续管理不得自动补装该配置。
- 安装选择保存到设备的 `~/.config/agents/install-selection.json`，更新、检查和卸载沿用该范围；选择记录不进入仓库。
- 再次安装替换选择记录，不自动删除未选中的已有文件；指定 Agent 卸载成功后，从选择记录中移除该 Agent。
- 受管文件采用复制，不依赖符号链接权限；默认保护本地差异，只有明确选择覆盖或使用受支持的强制选项时才能覆盖或删除。
- Context7 仅在安装、更新时输出一次官方安装文档提示，各 Agent 独立安装和管理；仓库不保存密钥，也不修改、检查或卸载其配置。
- MCP 管理保留其他 Server 配置，包括已有 Context7；跳过 MCP 时不读写 Agent MCP 配置或调用 Agent CLI。
- 已停用 Agent 的历史文件、Context7 启动器和密钥不再纳管，不自动清理。

## 验证

- 修改安装器或 Hook 后必须执行对应测试；测试使用临时目录或模拟调用，不修改真实用户配置。
- 完整测试：`python3 -m unittest discover -s tests`；Windows 使用 `py -3 -m unittest discover -s tests`。
- 安装器测试：`python3 -m unittest discover -s tests -p 'test_manage.py'`。
- Hook 测试：`python3 -m unittest discover -s tests -p 'test_check_commit_message.py'`。
- 交互安装实测在临时目录中使用隐藏的 `--home` 指定目标，不运行面向真实用户目录的安装、更新或卸载来验证变更。
- 交付前执行 `git diff --check`；文档变更核对当前实现，不声称未执行的平台测试已通过。

## Git 规则

- 使用 Conventional Commits，标题格式为 `type: 描述`，不使用 scope（如 `feat(xxx):`）。
- Commit 必须包含有效正文，正文说明问题、原因、修改和结果；形式与顺序不限。
- 每个 Commit 只包含一个主题。
- 禁止使用 `--no-verify` 绕过 Hook。
