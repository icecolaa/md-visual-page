---
name: md-visual-page
slug: md-visual-page
displayName: Markdown 一键可视化网页
version: 1.0.1
description: 把一个 Markdown 文件或整个文件夹一键生成单个离线可读的可视化 HTML 网页，完整保留正文并自带目录导航、全文检索、阅读进度、章节折叠与代码复制。当用户说“把 md 文件/文件夹一键生成可视化网页”“把教程或笔记转成网页”“生成带目录和检索的文档页面”“md 转单文件 HTML”时使用。
summary: 把 md 文件或文件夹渲染成单文件可视化 HTML 页面，自带导航、检索、进度与代码复制，离线可用。
tags:
  - markdown
  - html
  - visualization
  - documentation
  - offline
license: MIT
homepage: https://github.com/icecolaa/md-visual-page
argument-hint: <md 文件或文件夹路径>
---

# Markdown 一键可视化网页

## 概述

把一个 Markdown 文件或一整个文件夹（含子目录）渲染成单个自包含 HTML 页面：完整保留正文，附带顶部导航、目录检索、章节折叠、阅读进度条、代码复制与移动端抽屉目录。输出不依赖任何外部资源，双击即可离线阅读，适合教程、笔记、课程资料与项目文档。

## 快速开始

```bash
# 文件夹（递归收集 .md / .markdown，自动按一级子目录分组）
python <skill-dir>/scripts/build_page.py <md文件夹>

# 单个文件
python <skill-dir>/scripts/build_page.py <文件.md>

# 指定输出与标题
python <skill-dir>/scripts/build_page.py <输入路径> --out D:/out/page.html --title "PythonAI 学习资料库" --subtitle "可视化阅读"
```

依赖仅 Python 3.9+ 与两个库：

```bash
python -m pip install Markdown lxml      # pillow 可选，用于写出图片原始尺寸
```

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `input` | 是 | Markdown 文件或文件夹路径 |
| `--out` | 否 | 输出 HTML 路径；传入目录则以默认名写入该目录 |
| `--title` | 否 | Hero 主标题，默认取输入文件/文件夹名 |
| `--subtitle` | 否 | Hero 第二行标题，默认“可视化阅读” |

输出默认位置：与输入同级的 `<名称>-可视化网页.html`。

## 转换规则

- 每篇文档第一个 1–2 级标题作为文档标题并从正文移除；其余标题自动降为章节（H2 → 页面 3 级标题），多 H1 文档会保留为独立章节。
- 图片：`data:` 链接原样保留；相对路径位于输入目录内则按 base64 内联（单张 ≤ 3MB）；文件缺失、超限或网络图片抓取失败时生成蓝色占位图并写明原因。
- 表格自动包一层横向滚动容器；外链自动 `target=_blank` 加 `rel=noopener`；`.zip/.pdf/.docx` 等下载链接使用文件样式。
- 图片全部内联后页面完全离线；页面大小随图片数量增长，必要时先压缩原图再生成。
- 目录按输入的一级子目录分组；单文件输入只有一组，索引区自动变为单栏。

## 执行流程

1. 确认输入路径存在，并检查依赖：`python -c "import markdown, lxml"`。
2. 运行 `scripts/build_page.py`，逐行读取输出的 `sections / chars / image(s) inlined / placeholder(s)`。
3. 若出现 `placeholder(s)`，提示用户对应图片未找到（脚本已列出文件名），页面仍完整可用。
4. 报告输出路径、文档数与文件大小，并提示用浏览器打开；如使用 Qoder 可用浏览器工具打开本地文件核对导航与检索。

## 自检清单

- [ ] 输出为单个 HTML 文件，无外链 CSS / JS / 字体 / 图片。
- [ ] 浏览器打开无控制台报错，移动端无横向溢出（表格、代码块在各自容器内滚动）。
- [ ] 目录检索、章节跳转、折叠展开、阅读进度、代码复制均可用。
- [ ] 占位图数量与源文件缺图数量一致。

## 资源

- `scripts/build_page.py` — 生成器（扫描 Markdown、渲染、内联资源、产出单文件页面）。
- `assets/theme.css` — 蓝色主题样式（响应式、打印样式、无障碍焦点态）。
- `assets/app.js` — 交互脚本（ES5，目录检索、滚动高亮、代码复制、移动端抽屉）。