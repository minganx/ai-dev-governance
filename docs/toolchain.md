# 开发工具链配置

本仓库区分设备级默认配置、项目级强制配置和 IDE 个人设置。项目仓库中的配置与质量门禁是团队一致性的权威来源。

## 配置边界

| 配置                        | 位置                                  | 作用                                           |
| --------------------------- | ------------------------------------- | ---------------------------------------------- |
| Git 全局忽略                | `config/git/gitignore_global`         | 忽略操作系统、编辑器和通用缓存等本机噪音       |
| Ruff 用户级默认配置         | `config/ruff/ruff.toml`               | 为没有 Ruff 配置的 Python 项目提供默认检查规则 |
| Pyright 项目模板            | `templates/python/pyrightconfig.json` | 新项目复制后按源码目录、Python 版本和范围调整  |
| Prettier 项目模板           | `templates/prettier/`                 | 新项目复制并固定项目级 Markdown 格式           |
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

然后复制 `templates/prettier/` 中的配置，并在 `package.json` 中提供：

```json
{
  "scripts": {
    "format:markdown": "prettier --write \"**/*.md\"",
    "check:markdown": "prettier --check \"**/*.md\""
  }
}
```

提交 `package.json`、锁文件和 Prettier 配置，不提交 `node_modules/`。编辑器应使用项目本地 Prettier，并启用“存在项目配置时才格式化”。

## pre-commit

项目按自身技术栈维护 `.pre-commit-config.yaml`。Markdown 项目可使用：

```yaml
repos:
  - repo: local
    hooks:
      - id: prettier-markdown
        name: Prettier Markdown
        entry: npx --no-install prettier --write
        language: system
        types: [markdown]
        files: \.md$
```

共享 Commit 正文检查器按治理仓库不可变 Commit SHA 引用，配置见根目录 [README](../README.md)。

## IDE

- PyCharm 可关闭与 Prettier 冲突的 Markdown 表格格式检查，其他检查保持启用。
- VS Code 可设置 `prettier.requireConfig: true`，Markdown 使用项目本地 Prettier。
- IDE 配置只改善交互；最终结果以项目格式化命令、静态检查、pre-commit 和 CI 为准。
