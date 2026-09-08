# 项目级 Agent 配置模板

按需复制到项目根目录：

- `AGENTS.md`：Cursor、Pi 和 oh-my-pi 原生读取的项目主规则，也是其他 Agent 的项目事实来源。
- `CLAUDE.md`：Claude Code 薄入口，只导入根目录 `AGENTS.md`。
- `.codex/AGENTS.md`：Codex 薄入口，要求优先读取根目录 `AGENTS.md`。

项目专属 Skill 不提供固定正文模板。创建后放入项目 `.agents/skills/`，并使用项目前缀命名。Claude Code 需要额外适配时，在项目 `.claude/skills/` 放置薄入口，不复制 Skill 正文。
