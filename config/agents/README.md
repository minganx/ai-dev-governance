# Agent 配置维护边界

## 仓库自维护内容

- `AGENTS.md`：跨 Agent 的全局开发规则源文件。
- `skills/*/SKILL.md`：本仓库自行编写并维护的通用 Skill。
- `../tool-entries/`：特定 Agent 的规则薄入口。

这些文件没有外部发布源。安装时通过数字菜单选择 Agent、Skill 和全局规则，由 `tools/install.*` 复制所选项；`tools/update.*` 沿用设备保存的安装选择。

## 第三方内容

第三方 Skill、插件和扩展不复制到本目录，也不提交其正文或安装缓存。确定需要跨设备复用后，只记录发布源、安装范围和官方安装命令，并继续由原工具负责版本检查、更新和卸载。

当前工具提供的管理入口包括：

- Claude Code：`claude plugin marketplace add`、`claude plugin install`、`claude plugin update`。
- Codex：`codex plugin marketplace add`、`codex plugin add`、`codex plugin marketplace upgrade`。
- Cursor：`cursor-agent plugin marketplace add`、`cursor-agent plugin marketplace update`；插件安装按 Cursor 当前提供的界面或命令执行。

不得把工具内置 Skill、运行时插件、插件缓存、凭据或 `node_modules` 复制进治理仓库。

## 已纳管第三方资源

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

安装、版本检查、更新和卸载由 Skills CLI 管理，不随本仓库文件同步执行。本仓库仅支持 Cursor、Codex 和 Claude Code。

## MCP 配置

`config/mcp/servers.json` 只维护 DeepWiki 的非敏感定义，安装时通过数字菜单选择，按所选 Agent 同步到 Cursor、Codex 和 Claude Code。其他 MCP 条目保持不变，已退役的 `codegraph` 条目在安装、更新和卸载时清理，检查时报告残留。

Context7 由各 Agent 独立安装和管理。本仓库仅在安装和更新时输出一次[安装文档](../../docs/context7.md)提示，不保存密钥或维护 Context7 配置。

## CC Switch 提示词迁移

CC Switch 数据库中的 6 条提示词已去重并归入以下来源：

- Claude 自动导入提示词：`config/tool-entries/claude/CLAUDE.md`。
- Codex 自动导入提示词：通用规则合入 `AGENTS.md`。
- `默认 Agent 通用` 与 `默认 Python 开发`：重复内容合入 `AGENTS.md`。
- `Python 项目默认提示词`：项目无关部分进入 `dev-configs/agents/`；`tk_rag` 项目事实继续由该项目自己的 `AGENTS.md` 管理。
- `Obsidian 笔记库结构、归类与笔记体写作规范`：迁入 `skills/obsidian-notes/`；通用技术笔记规则补充到 `skills/docs-workflow/`。

`oa-timesheet` 及其浏览器扩展由其他仓库管理，不迁入本仓库。
