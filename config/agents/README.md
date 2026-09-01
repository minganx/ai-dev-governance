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

Pi 使用 `npm:@rahularya01/pi-cursor` 接入 Cursor 订阅。选择 Pi 时，设备管理工具执行：

- 安装：`pi install npm:@rahularya01/pi-cursor`
- 更新：`pi update npm:@rahularya01/pi-cursor`
- 卸载：`pi remove npm:@rahularya01/pi-cursor`
- 检查：通过 `pi list` 确认 Package 已安装

Claude、Codex、Cursor 的现有第三方插件和 Marketplace 不纳管。CC Switch 中的第三方和工具内置 Skill 不迁入仓库，也不由设备管理工具操作。

## CC Switch 提示词迁移

CC Switch 数据库中的 6 条提示词已去重并归入以下来源：

- Claude 自动导入提示词：`config/tool-entries/claude/CLAUDE.md`。
- Codex 自动导入提示词：通用规则合入 `AGENTS.md`，CodeGraph 约定进入项目 Agent 模板。
- `默认 Agent 通用` 与 Pi `默认 Python 开发`：重复内容合入 `AGENTS.md`。
- `Python 项目默认提示词`：项目无关部分进入 `dev-configs/agents/`；`tk_rag` 项目事实继续由该项目自己的 `AGENTS.md` 管理。
- `Obsidian 笔记库结构、归类与笔记体写作规范`：迁入 `skills/obsidian-notes/`；通用技术笔记规则补充到 `skills/docs-workflow/`。

`oa-timesheet` 及其浏览器扩展由其他仓库管理，不迁入本仓库。
