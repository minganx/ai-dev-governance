# AI 开发治理

本仓库统一维护跨项目、跨 AI 工具的开发规则、通用 Skill、用户级工具默认配置和 Commit 正文检查器，支持 macOS、Windows、Linux。

## 管理范围

| 路径                            | 用途                           |
| ------------------------------- | ------------------------------ |
| `config/agents/AGENTS.md`       | 全局开发规则唯一源文件         |
| `config/agents/skills/`         | 通用 Skill 唯一源文件          |
| `config/git/gitignore_global`   | Git 全局忽略规则               |
| `config/ruff/ruff.toml`         | Ruff 用户级默认配置            |
| `templates/`                    | Pyright、Prettier 等项目模板   |
| `docs/toolchain.md`             | 开发工具链配置边界和接入规范   |
| `hooks/check_commit_message.py` | Commit 正文最低机械质量检查    |
| `.pre-commit-hooks.yaml`        | 供项目固定版本引用的 Hook 清单 |
| `tools/manage.py`               | 跨平台安装与漂移检查           |
| `tools/install.sh`              | macOS、Linux 安装入口          |
| `tools/install.ps1`             | Windows 安装入口               |

## 首次部署

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

安装器发现同名文件内容不一致时拒绝覆盖。确认治理仓库是权威来源后执行：

```bash
./tools/install.sh --force
```

Windows：

```powershell
.\tools\install.ps1 --force
```

安装器复制文件，不依赖符号链接权限。受管目标包括：

- `~/.config/agents/`
- `~/.codex/AGENTS.md`
- `~/.claude/CLAUDE.md`
- `~/.agents/skills/`
- `~/.claude/skills/`
- `~/.codex/skills/`
- `~/.cursor/skills/`
- `~/.gitignore_global`
- macOS、Linux 的 `~/.config/ruff/ruff.toml`
- Windows 的 `%APPDATA%\ruff\ruff.toml`

## 日常使用

全局规则和通用 Skill 安装后，由 Claude Code、Codex、Cursor 等工具按各自入口自动加载。日常开发不需要从治理仓库启动 AI 工具。

项目仓库继续维护自己的事实和差异：

| 内容                    | 项目位置                  |
| ----------------------- | ------------------------- |
| 项目主规则              | `AGENTS.md`               |
| Claude Code 薄入口      | `CLAUDE.md`               |
| Codex 薄入口            | `.codex/AGENTS.md`        |
| 项目专属 Skill          | `.agents/skills/`         |
| Claude 项目 Skill 适配  | `.claude/skills/`         |
| 工程质量门禁            | `.pre-commit-config.yaml` |
| Ruff、Pyright、Prettier | 项目对应配置文件          |

规则优先级固定为：

1. 用户当前明确指令
2. 项目根目录 `AGENTS.md`
3. 全局 `~/.config/agents/AGENTS.md`
4. AI 工具默认行为

## 新项目接入

1. 在项目根目录创建 `AGENTS.md`，只记录项目事实、命令、架构约束和验证要求。
2. 为需要的工具创建薄入口，不复制项目规则正文。
3. 项目特有 Skill 写入 `.agents/skills/` 并提交到项目仓库。
4. 按技术栈从 `templates/` 选择 Pyright、Prettier 等配置模板。
5. 配置项目自己的 pre-commit、静态检查、测试和 CI。
6. 按下节接入共享 Commit 正文检查器。

项目增量 Skill 不得与全局 Skill 同名，例如：

```text
.agents/skills/tk-rag-docs-workflow/SKILL.md
.agents/skills/tk-rag-git-workflow/SKILL.md
```

需要支持 Claude Code 时，在 `.claude/skills/` 放置引用项目 Skill 的薄适配文件，不复制正文。

## 已有项目接入

1. 核对现有 AI 工具规则，选择项目根目录 `AGENTS.md` 作为项目唯一规则入口。
2. 删除各工具中重复的项目规则正文，仅保留薄入口。
3. 将项目可复用但只适用于当前仓库的 Skill 纳入版本控制。
4. 用项目质量命令替代 Claude Code 等单一工具的私有质量 Hook。
5. 接入共享 Commit Hook，并执行一次全量项目门禁。

## Commit Hook

项目通过不可变 Commit SHA 引用公开仓库：

```yaml
repos:
  - repo: https://github.com/minganx/ai-dev-governance
    rev: <已发布 Commit SHA>
    hooks:
      - id: check-commit-message
```

安装 Git Hook：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

使用 `uv` 管理开发工具的项目可以执行：

```bash
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

`rev` 必须替换为治理仓库已推送的完整 Commit SHA，不使用浮动分支。检查器只验证正文存在、最低有效长度和占位符；问题、原因、修改和结果的语义完整性由全局规则和审查保证。

## 治理仓库升级

在已克隆的治理仓库中执行：

```bash
git pull --ff-only
./tools/install.sh --force
python3 tools/manage.py check
```

Windows：

```powershell
git pull --ff-only
.\tools\install.ps1 --force
py -3 .\tools\manage.py check
```

治理仓库更新不会自动改变项目固定的 Hook 版本。需要升级项目时：

1. 选择治理仓库已推送的完整 Commit SHA。
2. 更新项目 `.pre-commit-config.yaml` 中的 `rev`。
3. 执行合法和非法 Commit message 验证。
4. 执行项目全量质量门禁。
5. 与项目变更一起提交 SHA 更新。

## 换设备

新设备只需重新克隆本仓库并执行“首次部署”。不复制 Token、OAuth、MCP 凭据、IDE 会话、权限记录、缓存或本地日志。

Cursor User Rules 等只能通过产品界面维护的设置不由本仓库自动覆盖。仓库公共规则、项目规则和质量门禁仍是跨工具一致性的权威来源。

## 配置边界

- 用户级默认：全局 AI 规则、通用 Skill、Git 全局忽略和 Ruff 默认配置。
- 项目级强制：项目规则、项目 Skill、依赖锁、Ruff、Pyright、Prettier、pre-commit、测试和 CI。
- IDE 个人设置：只提升编辑体验，不作为完成或提交的判断依据。
- Pyright、Prettier 和项目 Ruff 配置不通过用户目录隐式继承，保证仓库可复现。

详细配置见[开发工具链配置](docs/toolchain.md)。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 tools/manage.py check
```

修改 Hook 或 Python 安装元数据后，还需验证构建和真实 pre-commit 安装。
