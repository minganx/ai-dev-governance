# Agent 配置维护边界

## 仓库自维护内容

- `AGENTS.md`：跨 Agent 的全局开发规则源文件。
- `skills/*/SKILL.md`：本仓库自行编写并维护的通用 Skill。
- `../tool-entries/`：特定 Agent 的规则薄入口。

这些文件没有外部发布源，由 `tools/install.*` 和 `tools/update.*` 复制到设备受管路径。

## 第三方内容

第三方 Skill、插件、扩展和 Pi Package 不复制到本目录，也不提交其正文或安装缓存。确定需要跨设备复用后，只记录发布源、安装范围和官方安装命令，并继续由原工具负责版本检查、更新和卸载。

当前工具提供的管理入口包括：

- Claude Code：`claude plugin marketplace add`、`claude plugin install`、`claude plugin update`。
- Codex：`codex plugin marketplace add`、`codex plugin add`、`codex plugin marketplace upgrade`。
- Cursor：`cursor-agent plugin marketplace add`、`cursor-agent plugin marketplace update`；插件安装按 Cursor 当前提供的界面或命令执行。
- Pi：`pi install`、`pi update --extensions`、`pi remove`。

不得把工具内置 Skill、运行时插件、插件缓存、凭据或 `node_modules` 复制进治理仓库。

## 已纳管第三方资源

Pi 使用 `npm:@rahularya01/pi-cursor` 接入 Cursor 订阅，使用 `npm:pi-mcp-adapter` 加载标准 MCP 配置。选择 Pi 时，设备管理工具对两个 Package 执行：

- 安装：`pi install <package>`
- 更新：`pi update <package>`
- 卸载：`pi remove <package>`
- 检查：通过 `pi list` 确认 Package 已安装

Claude、Codex、Cursor 的现有第三方插件和 Marketplace 不纳管。CC Switch 中的第三方和工具内置 Skill 不迁入仓库，也不由设备管理工具操作。

### Archify

- 发布源：[tt-a1i/archify](https://github.com/tt-a1i/archify)。
- 用途：生成交互式架构、工作流、时序、数据流和生命周期图。
- 安装范围：设备级第三方 Skill，由上游 Skills CLI 安装到所选 Agent；不进入本仓库自维护 Skill 目录。

按[上游安装说明](https://github.com/tt-a1i/archify#quick-start)执行，在交互选择中确认目标 Agent：

```bash
npx skills add tt-a1i/archify -g
```

Cursor 的明确安装命令：

```bash
npx -y skills add tt-a1i/archify --skill archify --agent cursor --global --copy --yes
```

安装、版本检查、更新和卸载由 Skills CLI 管理，不随本仓库文件同步执行。上游快速入口覆盖 Claude Code、Codex、Cursor 和 OpenCode；本仓库未验证 Archify 在 Pi 和 oh-my-pi 中的运行。

## MCP 配置

`config/mcp/servers.json` 只维护 Context7、DeepWiki 的非敏感定义。安装器将对应条目合并到 Claude、Codex、Cursor、oh-my-pi 配置，并为 Pi 写入 `pi-mcp-adapter` 官方支持的 `~/.config/mcp/mcp.json`；其他 MCP 条目保持不变。

Context7 API Key 不写入仓库或 MCP JSON/TOML。首次安装时提示用户先保存到密码管理器，再隐藏输入并保存到 `~/.config/agents/mcp/context7-api-key`（macOS、Linux 权限为 `0600`）。MCP 启动器在运行时通过 `CONTEXT7_API_KEY` 环境变量传给 Context7 官方 Server，不把 Key 放入命令参数。

Pi 核心不内置 MCP；本仓库只在选择 Pi 时通过其官方 Package 命令维护 `pi-mcp-adapter`，不复制 Package 源码或缓存。

oh-my-pi 使用[原生 MCP](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-config.md)，同步目标为默认目录 `~/.omp/agent/mcp.json`；规则与 Skill 分别写入同目录的 `AGENTS.md` 和 `skills/`。命名 Profile、自定义目录和 XDG 目录不纳管。

## CC Switch 提示词迁移

CC Switch 数据库中的 6 条提示词已去重并归入以下来源：

- Claude 自动导入提示词：`config/tool-entries/claude/CLAUDE.md`。
- Codex 自动导入提示词：通用规则合入 `AGENTS.md`。
- `默认 Agent 通用` 与 Pi `默认 Python 开发`：重复内容合入 `AGENTS.md`。
- `Python 项目默认提示词`：项目无关部分进入 `dev-configs/agents/`；`tk_rag` 项目事实继续由该项目自己的 `AGENTS.md` 管理。
- `Obsidian 笔记库结构、归类与笔记体写作规范`：迁入 `skills/obsidian-notes/`；通用技术笔记规则补充到 `skills/docs-workflow/`。

`oa-timesheet` 及其浏览器扩展由其他仓库管理，不迁入本仓库。
