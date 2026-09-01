---
name: obsidian-notes
description: 整理、迁移和更新 Obsidian 笔记，维护 GTD 目录、附件、Excalidraw 画板和 Markdown 格式。用于用户明确要求整理笔记、迁移旧文或维护 Obsidian 知识库时。
---

# Obsidian 笔记规范

仅在用户明确要求整理、迁移或更新 Obsidian 笔记时使用。

## 目录与归类

- `inbox/`：尚未消化的材料。
- `work/`：按公司、项目组织的工作资料。
- `knowledge/`：按系统运维、数据库、网络等领域组织的知识。
- `notes/`：私人资料；不得把 Token、密钥或隐私内容迁入公开仓库。
- 一业务领域一份文件，领域内工具和知识点使用二级标题分章；内容过长或明显难读时再拆分。
- 新材料先进入对应目录；`inbox/` 内容消化后迁出。

## 内容与文体

- 只记录当前有效的事实、配置、命令、参数和行为边界。
- 推测、临时排查过程、验证计划和方案对比不写成稳定笔记事实。
- 迁移旧文时先结构化保留有效内容，再删除重复、过时、错误或已被替代的说明。
- 使用笔记体和工程事实表达，避免教学、宣传和过程汇报语气。
- 标题最多三级，减少碎片列表；参数密集和结构化信息优先使用表格。
- 不主动增加手写目录、批量脚本、教程附录或与当前主题无关的扩展内容。

## 附件

默认结构：

```text
章节目录/
  笔记A.md
  笔记B.md
  assets/
    笔记A-slug/
    笔记B-slug/
```

- `foo.md` 的附件放在同目录 `assets/{笔记文件名-slug}/`。
- Markdown 图片使用相对路径：`![alt](assets/{slug}/file.png)`。
- 从外部平台迁移时下载远程图片和附件并替换链接。
- 单篇附件很多或包含画板源文件时，可使用 `笔记名/笔记名.md + assets/` 结构。
- 语雀画板或导图保留 `.lake`、`.lakecard` 源文件，并增加同目录 Markdown 说明，不强制转为纯 Markdown。

## Excalidraw

- 架构图、流程图、拓扑图、关系图和示意图默认使用 Excalidraw；用户明确指定时除外。
- 使用现代 Markdown 格式 `.excalidraw.md`，放入笔记对应的 `assets/{slug}/`。
- 正文使用 `![[assets/{slug}/{画板名}.excalidraw|宽度]]`，链接不得写成 `.excalidraw.md`。
- 保留插件生成的文件结构，不手工改写 `## Text Elements` 或压缩数据。
- 程序生成画板时使用 `excalidraw-plugin: raw`，文字写入 Drawing JSON。
- 交付前同时检查 Excalidraw 视图和笔记嵌入效果；仅验证 JSON 和文件存在不算完成。

## Markdown 与代码块

- 标题后、段落间、代码块和表格前后保留一个空行。
- 所有代码块标注语言；命令使用 `bash` 或 `shell`，输出使用 `text`。
- 围栏及块内命令从第一列开始，不保留迁移内容中的四空格缩进。
- 命令必须完整可执行，参数说明放在代码块外；参数较多时使用表格。
- Linter 负责 Markdown 结构，Prettier 负责整篇排版，Simple Code Formatter 只处理支持的单个代码块。
- `bash`、`shell`、`python`、`plsql` 等未配置自动格式化时，保持顶格并人工整理。
