# 常用开发配置模板

本目录保存按个人习惯整理、供项目手工复制的开发配置，不由 `tools/manage.py` 安装或更新。模板以 `tk_rag` 的有效配置为基线，去除了业务依赖、业务目录和针对具体源码文件的豁免。

## 文件清单

- `agents/`：项目 `AGENTS.md`、Claude、Codex 薄入口。
- `git/`：项目 `.gitignore` 和 `.gitattributes` 通用模板。
- `python/pyproject.toml`：`uv`、setuptools、Ruff、deptry、Bandit、Commitizen 的组合模板。
- `python/pyrightconfig.json`：Python 3.11、`.venv`、`src` 布局的 Pyright 模板。
- `prettier/.prettierrc.json`：Markdown 保留人工换行并统一 LF。
- `prettier/.prettierignore`：常见依赖、运行数据和交付目录忽略清单。
- `prettier/package.json`：固定 Prettier 版本及 Markdown 检查、格式化命令。
- `pre-commit/.pre-commit-config.yaml`：通过项目本地 `uv` 和 npm 工具执行质量门禁的模板。

## 使用边界

1. 按项目技术栈复制需要的文件，不整目录盲目覆盖。
2. 搜索模板中的 `replace-me`、`replace_me`、版本号、`src`、Python 版本和目录范围并逐项确认。
3. 删除项目不使用的检查器和豁免；不得仅为通过检查而扩大忽略范围。
4. 执行 `uv lock`、`npm install` 等项目依赖命令生成或更新锁文件。
5. 执行模板中配置的全部检查，确认命令、范围和项目行为一致后再提交。

`pyrightconfig.json` 使用 Pyright 支持的 JSON with Comments 格式，文件内注释用于标明必须按项目修改的字段。Prettier 的 JSON 配置说明集中在本文件，避免加入工具不识别的自定义字段。
