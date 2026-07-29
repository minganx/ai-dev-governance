# AI 开发治理

本仓库统一维护跨项目、跨 AI 工具的开发规则、通用 Skill 和 Commit 正文检查器，支持 macOS、Windows、Linux。

## 内容

| 路径                            | 用途                           |
| ------------------------------- | ------------------------------ |
| `config/agents/AGENTS.md`       | 全局开发规则唯一源文件         |
| `config/agents/skills/`         | 通用 Skill 唯一源文件          |
| `hooks/check_commit_message.py` | Commit 正文最低机械质量检查    |
| `.pre-commit-hooks.yaml`        | 供项目固定版本引用的 Hook 清单 |
| `pyproject.toml`                | Python Hook 安装元数据         |
| `tools/manage.py`               | 跨平台安装与漂移检查           |
| `tools/install.sh`              | macOS、Linux 安装入口          |
| `tools/install.ps1`             | Windows 安装入口               |

## 安装

### macOS / Linux

```bash
git clone https://github.com/minganx/ai-dev-governance.git
cd ai-dev-governance
./tools/install.sh
python3 tools/manage.py check
```

已存在不同内容时，安装器拒绝覆盖。确认治理仓库内容为准后执行：

```bash
./tools/install.sh --force
```

### Windows

```powershell
git clone https://github.com/minganx/ai-dev-governance.git
Set-Location ai-dev-governance
.\tools\install.ps1
py -3 .\tools\manage.py check
```

确认覆盖已有受管文件时：

```powershell
.\tools\install.ps1 --force
```

安装器复制全局规则和通用 Skill，不依赖 Windows 符号链接权限。受管目标包括：

- `~/.config/agents/`
- `~/.codex/AGENTS.md`
- `~/.claude/CLAUDE.md`
- `~/.agents/skills/`
- `~/.claude/skills/`
- `~/.codex/skills/`
- `~/.cursor/skills/`

Claude 通过 `~/.claude/CLAUDE.md` 导入共享规则；Codex 的全局 `AGENTS.md` 由同一源文件生成。Cursor 的 User Rules 由产品界面维护，治理仓库只同步其通用 Skill；项目规则继续由仓库根目录 `AGENTS.md` 提供。

## 项目接入

项目根目录 `AGENTS.md` 负责项目规则，并声明项目规则高于全局规则。Claude、Codex、Cursor 的项目入口只做薄转发。

项目 Skill 使用 `.agents/skills/` 作为项目源文件。项目增量 Skill 不得与全局 Skill 同名，例如：

```text
.agents/skills/tk-rag-docs-workflow/SKILL.md
.agents/skills/tk-rag-git-workflow/SKILL.md
```

Claude 项目 Skill 位于 `.claude/skills/`。需要同时支持 Claude 时，在该目录放置薄适配 Skill，引用 `.agents/skills/` 中的项目源文件，不复制正文。

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

`rev` 必须替换为治理仓库已推送的完整 Commit SHA，不使用浮动分支。检查器只验证正文存在、最低有效长度和占位符；问题现象、分析原因、修改内容和修改后结果的语义完整性由全局规则和审查保证。

## 项目与全局边界

- 全局规则：跨项目一致的开发、Git、文档和质量原则。
- 通用 Skill：跨项目可复用的工作流基线。
- 项目规则：项目事实、目录、命令、架构和红线。
- 项目 Skill：只添加项目差异。
- 仓库门禁：项目实际质量工具、业务验证和 CI。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 tools/manage.py check
```
