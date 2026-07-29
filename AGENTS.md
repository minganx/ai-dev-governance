# AI 开发治理仓库规则

本仓库维护跨项目、跨 AI 工具共享的开发规则、通用 Skill、Git Hook 和安装工具。

## 规则优先级

1. 用户当前明确指令
2. 本仓库 `AGENTS.md`
3. `config/agents/AGENTS.md`
4. 工具默认行为

## 维护规则

- `config/agents/` 是全局规则和通用 Skill 的唯一源文件。
- `hooks/` 只实现可机械检查的 Git 规则，不判断业务语义。
- `tools/` 必须兼容 macOS、Windows、Linux，不写死用户目录。
- 不提交 Token、API Key、OAuth、MCP 凭据、权限记录、缓存、会话或本地日志。
- 修改通用 Skill 时保持简洁；项目差异留在项目仓库的增量 Skill。
- 修改安装器或 Hook 后必须执行对应测试。

## Git 规则

- 使用 Conventional Commits。
- Commit 必须包含有效正文，正文说明问题、原因、修改和结果；形式与顺序不限。
- 每个 Commit 只包含一个主题。
- 禁止使用 `--no-verify` 绕过 Hook。
