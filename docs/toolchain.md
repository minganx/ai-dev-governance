# 开发工具链配置

本仓库区分设备级默认配置、项目级强制配置和 IDE 个人设置。项目仓库中的配置与质量门禁是团队一致性的权威来源。

## 配置边界

| 配置                        | 位置                                  | 作用                                           |
| --------------------------- | ------------------------------------- | ---------------------------------------------- |
| Git 全局忽略                | `config/git/gitignore_global`         | 忽略操作系统、编辑器和通用缓存等本机噪音       |
| Git 项目模板                | `dev-configs/git/`                    | 手工复制并调整项目忽略和跨平台属性             |
| 项目级 Agent 模板           | `dev-configs/agents/`                 | 手工复制项目规则入口          |
| Ruff 用户级默认配置         | `config/ruff/ruff.toml`               | 为没有 Ruff 配置的 Python 项目提供默认检查规则 |
| MCP Server 配置             | `config/mcp/`                         | 同步非敏感定义并在设备本地保存 API Key         |
| Python 项目模板             | `dev-configs/python/`                  | 手工复制并调整 pyproject、Pyright 和项目范围   |
| Prettier 项目模板           | `dev-configs/prettier/`                | 手工复制并固定项目级 Markdown 格式             |
| pre-commit 项目模板         | `dev-configs/pre-commit/`              | 手工复制并按项目质量工具调整                   |
| AI 全局规则与通用 Skill     | `config/agents/`                      | 跨项目、跨 AI 工具共享规则                     |
| 项目规则、项目 Skill 与门禁 | 各项目仓库                            | 项目事实、工程命令、项目差异和 CI/提交前检查   |
| PyCharm、VS Code 个人设置   | IDE 用户配置                          | 提升编辑体验，不作为仓库质量结果的权威来源     |

## Git 全局忽略

安装器将配置复制到 `~/.gitignore_global`。首次安装后执行：

```bash
git config --global core.excludesFile ~/.gitignore_global
git config --global --get core.excludesFile
```

Windows PowerShell：

```powershell
git config --global core.excludesFile "$HOME/.gitignore_global"
git config --global --get core.excludesFile
```

全局忽略只包含跨项目稳定的本机噪音。`dist/`、`logs/`、数据库文件、交付物和项目运行目录由各项目自己的 `.gitignore` 决定，避免全局规则静默隐藏有效文件。

## Ruff

安装器同步用户级默认配置：

- macOS、Linux：`~/.config/ruff/ruff.toml`
- Windows：`%APPDATA%\ruff\ruff.toml`

用户配置不是项目配置的隐式父配置。项目存在 `pyproject.toml`、`ruff.toml` 或 `.ruff.toml` 时，以项目配置为准；需要继承其他配置时必须显式使用 Ruff 的 `extend`。

项目 CI 和 pre-commit 不依赖用户级 Ruff 配置。项目应在仓库内声明完整、可复现的 Ruff 配置。

## MCP

仓库维护 Context7、DeepWiki 的非敏感定义，并将受管条目合并到 Claude、Codex、Cursor、Pi 和 oh-my-pi 配置。Pi 通过官方 `pi-mcp-adapter` Package 读取 `~/.config/mcp/mcp.json`；oh-my-pi 使用默认目录 `~/.omp/agent/mcp.json`；其他 Agent 使用自己的用户级 MCP 配置。同步只修改受管 Server，不覆盖工具中的其他 MCP。

Context7 API Key 由安装器隐藏输入并保存到设备的 `~/.config/agents/mcp/context7-api-key`，macOS、Linux 权限为 `0600`。MCP 配置只引用本地启动器和密钥路径，不包含 Key 明文；启动器通过环境变量调用 Context7 官方 npm Server。OAuth、其他 API Key 和工具生成的 MCP 缓存不纳管。

## Pyright

Pyright 配置属于项目。新项目将模板复制到项目根目录后，至少确认：

- `pythonVersion`
- `include`
- `venvPath` 与 `venv`
- `exclude`
- `typeCheckingMode`

`pyrightconfig.json` 与 `[tool.pyright]` 同时存在时，Pyright 使用 `pyrightconfig.json`。模板不自动安装到用户目录，也不通过本机绝对路径继承，避免换设备后失效。

## Prettier

Prettier 属于项目级工具。新项目执行：

```bash
npm install --save-dev --save-exact prettier
```

然后按需复制 `dev-configs/prettier/` 中的 `.prettierrc.json`、`.prettierignore` 和 `package.json`。模板已提供 Markdown 检查及格式化命令。

提交 `package.json`、锁文件和 Prettier 配置，不提交 `node_modules/`。编辑器应使用项目本地 Prettier，并启用“存在项目配置时才格式化”。

## pre-commit

项目按自身技术栈维护 `.pre-commit-config.yaml`。`dev-configs/pre-commit/` 提供通过项目本地 `uv` 和 npm 工具执行 Prettier、Ruff、Pyright、Bandit、deptry、Commitizen 的个人模板；复制后必须删除不使用的 Hook 并调整路径范围。

共享 Commit 正文检查器按治理仓库不可变 Commit SHA 引用：

```yaml
repos:
  - repo: https://github.com/minganx/ai-dev-governance
    rev: <已发布 Commit SHA>
    hooks:
      - id: check-commit-message
```

`rev` 必须使用已推送的完整 Commit SHA。配置后执行：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

使用 `uv` 管理开发工具时执行 `uv run pre-commit install --hook-type pre-commit --hook-type commit-msg`。

## IDE

- PyCharm 可关闭与 Prettier 冲突的 Markdown 表格格式检查，其他检查保持启用。
- VS Code 可设置 `prettier.requireConfig: true`，Markdown 使用项目本地 Prettier。
- IDE 配置只改善交互；最终结果以项目格式化命令、静态检查、pre-commit 和 CI 为准。
