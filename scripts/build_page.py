#!/usr/bin/env python3
"""Turn a Markdown file or a folder of Markdown files into one visual HTML page.

Usage:
    python scripts/build_page.py <file-or-folder> [--out <path>] [--title <text>]

The output is a single self-contained HTML file: CSS, JS and images are inlined,
so it can be opened or shared offline.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import mimetypes
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency. Install it with: python -m pip install Markdown")

try:
    from lxml import etree, html as lxml_html
except ImportError:
    sys.exit("Missing dependency. Install it with: python -m pip install lxml")

try:
    from PIL import Image
except ImportError:
    Image = None


ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICON_SEARCH = (
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" aria-hidden="true"><circle cx="7" cy="7" r="4.5"></circle>'
    '<path d="M10.5 10.5 14 14"></path></svg>'
)
ICON_MENU = (
    '<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" aria-hidden="true"><path d="M3 5h12M3 9h12M3 13h12"></path></svg>'
)
ICON_CHEVRON_RIGHT = (
    '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 2.5 8 6l-3.5 3.5"></path></svg>'
)
ICON_CHEVRON_DOWN = (
    '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 4.5 6 8l3.5-3.5"></path></svg>'
)
ICON_UP = (
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 13V3M3.5 7.5 8 3l4.5 4.5"></path></svg>'
)

FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
MARKDOWN_SUFFIXES = {".md", ".markdown"}
IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", ".next", ".cache",
}
IMAGE_LIMIT = 3_000_000
IMAGE_CACHE: dict[str, tuple[bytes, str] | None] = {}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<meta name="description" content="@@DESC@@">
<meta name="theme-color" content="#f5f9ff">
<link rel="icon" href="@@FAVICON@@">
<style>
@@CSS@@
</style>
</head>
<body id="top">
<a class="skip-link" href="#main">跳到正文</a>
<header class="topbar" id="topbar">
  <div class="topbar-inner">
    <button class="menu-btn" id="menuBtn" type="button" aria-label="打开目录" aria-expanded="false" aria-controls="sidebar">@@ICON_MENU@@</button>
    <a class="brand" href="#top" aria-label="@@BRAND_TITLE@@ 首页">
      <span class="brand-mark" aria-hidden="true">@@BRAND_MARK@@</span>
      <span class="brand-text"><strong>@@BRAND_TITLE@@</strong><small>VISUAL DOCS</small></span>
    </a>
    <div class="topbar-actions">
      <button class="search-trigger" id="searchTrigger" type="button" aria-label="搜索文档或章节">
        @@ICON_SEARCH@@<span>搜索</span><kbd>Ctrl K</kbd>
      </button>
      <span class="topbar-meta">@@TOPBAR_META@@</span>
    </div>
  </div>
  <div class="progress-track" aria-hidden="true"><span id="progressBar"></span></div>
</header>

<div class="shell">
  <aside class="sidebar" id="sidebar" aria-label="文档目录">
    <div class="sidebar-head">
      <p class="kicker">LIBRARY INDEX</p>
      <h2>资料目录</h2>
      <p class="sidebar-note">@@SIDEBAR_META@@</p>
    </div>
    <label class="search-box" for="navSearch">
      @@ICON_SEARCH@@
      <input id="navSearch" type="search" placeholder="搜索文档或章节…" autocomplete="off" aria-label="搜索文档或章节">
      <kbd>Ctrl K</kbd>
    </label>
    <nav class="toc" aria-label="文档导航">
      <a class="nav-overview" href="#index"><span>文档索引</span><em>INDEX</em></a>
      @@NAV@@
    </nav>
    <p class="nav-empty" id="navEmpty" hidden>没有匹配的文档或章节</p>
    <div class="sidebar-foot">
      <strong>MARKDOWN / VISUAL EDITION</strong>
      全部正文已收录<br>离线可读 · 目录可检索
    </div>
  </aside>

  <main class="main" id="main">
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow"><span class="eyebrow-dot" aria-hidden="true"></span>@@EYEBROW@@</p>
        <h1 id="hero-title">@@HERO_TITLE@@<span>@@HERO_SUBTITLE@@</span></h1>
        <p class="hero-sub">@@HERO_SUB@@</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="#@@FIRST_DOC@@">开始阅读</a>
          <a class="btn btn-ghost" href="#index">浏览文档索引</a>
        </div>
        <dl class="hero-stats">
          <div><dt>文档</dt><dd>@@DOC_COUNT@@<small>篇</small></dd></div>
          <div><dt>字符</dt><dd>@@CHAR_COUNT@@<small>万</small></dd></div>
          <div><dt>阅读</dt><dd>@@READ_HOURS@@<small>小时</small></dd></div>
        </dl>
      </div>
      <aside class="roadmap" aria-label="内容概览">
        <div class="roadmap-head"><span>内容概览</span><em>@@OVERVIEW_TAG@@</em></div>
        <p class="roadmap-note">@@OVERVIEW_NOTE@@</p>
        <ol class="stage-list">
          @@OVERVIEW_LIST@@
        </ol>
        <div class="roadmap-foot"><span class="pulse" aria-hidden="true"></span>单文件离线阅读 · 全文已收录</div>
      </aside>
    </section>

    <section class="index-section" id="index" aria-labelledby="index-title">
      <div class="section-head">
        <p class="kicker">DOCUMENT INDEX</p>
        <h2 id="index-title">文档索引</h2>
        <p>共 @@DOC_COUNT@@ 篇，按目录顺序排列。点击任意条目，直接跳到对应正文。</p>
      </div>
      <div class="index-grid@@INDEX_GRID_CLASS@@">
        @@INDEX@@
      </div>
    </section>

    @@GROUPS@@

    <footer class="site-foot">
      <strong>@@BRAND_TITLE@@ · 可视化文档</strong>
      <p>共 @@DOC_COUNT@@ 篇文档 · @@TOPIC_COUNT@@ 个章节 · 全部正文已收录</p>
      <p>由本地 Markdown 一键生成 · @@BUILD_DATE@@</p>
    </footer>
  </main>
</div>

<div class="overlay" id="overlay" hidden></div>
<button class="back-top" id="backTop" type="button" aria-label="回到顶部">@@ICON_UP@@</button>
<script>
@@JS@@
</script>
</body>
</html>
"""


def strip_front_matter(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    if text.startswith("---\n"):
        match = re.match(r"^---\n.*?\n---\n", text, re.S)
        if match:
            text = text[match.end():]
    return text


def normalize_markdown(text: str) -> tuple[str, str | None]:
    """Drop the document title and make every file use H2 for its top sections."""
    text = strip_front_matter(text)
    lines = text.split("\n")
    fence = False
    first_idx = None
    first_title = None

    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) <= 2:
            first_idx = i
            first_title = match.group(2).strip()
            break

    if first_idx is None:
        return text.strip() + "\n", None

    level = len(HEADING_RE.match(lines[first_idx]).group(1))
    before = lines[:first_idx]
    after = lines[first_idx + 1:]

    # H1 title: keep every H1/H2 as a top section (max(2, ...) below). H2 title: demote the rest.
    shift = 0 if level == 1 else -1

    out: list[str] = []
    fence = False
    for line in before + [""] + after:
        if FENCE_RE.match(line):
            fence = not fence
            out.append(line)
            continue
        if not fence:
            match = HEADING_RE.match(line)
            if match:
                new_level = max(2, min(6, len(match.group(1)) + shift))
                line = "#" * new_level + " " + match.group(2)
        out.append(line)

    return "\n".join(out).strip() + "\n", first_title


def render_markdown(body: str) -> str:
    converter = markdown.Markdown(
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    return converter.convert(body)


def element_text(element: etree._Element) -> str:
    return "".join(element.itertext()).strip()


def has_meaningful_content(element: etree._Element) -> bool:
    if element.text and element.text.strip():
        return True
    for child in element:
        if child.tag == "hr":
            continue
        if element_text(child):
            return True
        if child.tag in ("img", "figure", "table", "pre", "blockquote"):
            return True
    return False


def clean_title(title: str) -> str:
    title = re.sub(r"^第\s*\d+\s*[章节篇课]\s*[：:、.\-]?\s*", "", title)
    title = re.sub(r"^\d+[.、)\-]\s*", "", title)
    return title.strip() or title


def extract_desc(text: str) -> str:
    text = strip_front_matter(text)
    fence = False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        candidate = line.strip()
        if not candidate or len(candidate) < 8:
            continue
        if candidate.startswith(("#", ">", "-", "*", "+", "|", "![")):
            continue
        if re.match(r"^\d+[.、)]\s", candidate):
            continue
        candidate = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", candidate)
        candidate = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", candidate)
        candidate = re.sub(r"[`*_~]", "", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if len(candidate) < 8:
            continue
        return candidate[:88] + ("…" if len(candidate) > 88 else "")
    return "本页收录完整正文，可直接离线阅读。"


def natural_key(path: Path) -> list[tuple[int, object]]:
    parts = re.split(r"(\d+)", str(path))
    return [(0, int(part)) if part.isdigit() else (1, part.lower()) for part in parts if part]


def discover_markdown(input_path: Path) -> tuple[Path, list[Path]]:
    if input_path.is_file():
        if input_path.suffix.lower() not in MARKDOWN_SUFFIXES:
            sys.exit(f"Not a Markdown file: {input_path}")
        return input_path.parent, [input_path]

    files = []
    for candidate in sorted(input_path.rglob("*"), key=natural_key):
        if not candidate.is_file() or candidate.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        relative_parts = candidate.relative_to(input_path).parts[:-1]
        if any(part.startswith(".") or part in IGNORED_DIRS for part in relative_parts):
            continue
        files.append(candidate)
    return input_path, files


def wrap_tables(root: etree._Element) -> None:
    for table in list(root.iter("table")):
        parent = table.getparent()
        if parent is None:
            continue
        if parent.tag == "div" and "table-wrap" in (parent.get("class") or ""):
            continue
        wrapper = etree.Element("div")
        wrapper.set("class", "table-wrap")
        parent.replace(table, wrapper)
        wrapper.append(table)


def process_links(root: etree._Element) -> None:
    for link in root.iter("a"):
        href = link.get("href") or ""
        if href.startswith(("http://", "https://")):
            link.set("target", "_blank")
            link.set("rel", "noopener noreferrer")
        if href.lower().endswith((".zip", ".7z", ".rar", ".pdf", ".docx", ".xlsx")):
            classes = (link.get("class") or "").split()
            if "file-link" not in classes:
                classes.append("file-link")
            link.set("class", " ".join(classes))


def make_placeholder(img: etree._Element, label: str, note: str) -> None:
    safe_label = label if len(label) <= 64 else label[:61] + "…"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="440" viewBox="0 0 1200 440">
<rect width="1200" height="440" fill="#eef5ff"/>
<rect x="2" y="2" width="1196" height="436" rx="20" fill="none" stroke="#b9d4f8" stroke-width="2" stroke-dasharray="12 10"/>
<text x="600" y="206" text-anchor="middle" font-family="Georgia, serif" font-size="32" fill="#1e3a6e">{html.escape(note)}</text>
<text x="600" y="250" text-anchor="middle" font-family="Consolas, monospace" font-size="17" fill="#5b7699">{html.escape(safe_label)}</text>
<text x="600" y="292" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#7d93b0">可在源 Markdown 中补充图片后重新生成</text>
</svg>"""
    img.set("src", "data:image/svg+xml;charset=utf-8," + quote(svg, safe=""))
    img.set("width", "1200")
    img.set("height", "440")
    img.set("class", "img-placeholder")
    img.set("alt", f"{note}：{label}")
    figure = img.getparent()
    if figure is not None and figure.tag == "figure":
        caption = figure.find("figcaption")
        if caption is not None:
            caption.text = f"{note} · {safe_label}"


def fetch_image(url: str) -> tuple[bytes, str] | None:
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*,*/*;q=0.8",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(IMAGE_LIMIT + 1)
                if len(data) > IMAGE_LIMIT:
                    break
                content_type = response.headers.get_content_type() or "image/png"
            IMAGE_CACHE[url] = (data, content_type)
            return IMAGE_CACHE[url]
        except Exception:
            if attempt < 2:
                time.sleep(1.2)
    IMAGE_CACHE[url] = None
    return None


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    if Image is None:
        return None
    try:
        with Image.open(io.BytesIO(data)) as image:
            return image.size
    except Exception:
        return None


def process_images(root: etree._Element, doc_path: Path, input_root: Path) -> tuple[int, int]:
    for img in list(root.iter("img")):
        parent = img.getparent()
        if parent is not None and parent.tag == "p" and len(parent) == 1:
            figure = etree.Element("figure")
            figure.set("class", "figure")
            grandparent = parent.getparent()
            if grandparent is not None:
                grandparent.replace(parent, figure)
                figure.append(img)
                caption = etree.SubElement(figure, "figcaption")
                caption.text = img.get("alt") or "插图"

    inlined = 0
    missing = 0
    for img in root.iter("img"):
        src = (img.get("src") or "").strip()
        data = None
        mime = "image/png"
        if src.startswith("data:"):
            inlined += 1
            continue
        if src.startswith(("http://", "https://")):
            fetched = fetch_image(src)
            if fetched is not None:
                data, mime = fetched
            else:
                make_placeholder(img, "网络图片", "插图未能内联")
                missing += 1
        else:
            relative = unquote(src.split("?")[0].split("#")[0])
            candidate = (doc_path.parent / relative).resolve()
            try:
                candidate.relative_to(input_root)
                inside_root = True
            except ValueError:
                inside_root = False
            if inside_root and candidate.is_file() and candidate.stat().st_size <= IMAGE_LIMIT:
                data = candidate.read_bytes()
                mime = mimetypes.guess_type(candidate.name)[0] or "image/png"
            else:
                make_placeholder(img, relative, "插图暂缺")
                missing += 1

        if data is not None:
            size = image_dimensions(data)
            if size:
                img.set("width", str(size[0]))
                img.set("height", str(size[1]))
            encoded = base64.b64encode(data).decode("ascii")
            img.set("src", f"data:{mime};base64,{encoded}")
            inlined += 1

        img.set("loading", "lazy")
        img.set("decoding", "async")

    return inlined, missing


def build_document(path: Path, input_root: Path, index: int) -> dict:
    raw = path.read_text(encoding="utf-8-sig")
    body_md, source_title = normalize_markdown(raw)
    fragment = render_markdown(body_md)
    parser = lxml_html.HTMLParser(encoding="utf-8")
    root = lxml_html.fromstring('<div class="md-root">' + fragment + "</div>", parser=parser)

    doc_id = f"doc-{index:02d}"
    title = clean_title(source_title) if source_title else path.stem

    lead = etree.Element("div")
    lead.set("class", "doc-lead")
    sections: list[etree._Element] = []
    current = lead
    for child in list(root):
        if child.tag == "h2":
            section = etree.Element("section")
            section.set("class", "topic")
            section.append(child)
            sections.append(section)
            current = section
        else:
            current.append(child)

    topics = []
    for topic_index, section in enumerate(sections, 1):
        heading = section.find("h2")
        if heading is None:
            continue
        topic_id = f"{doc_id}-s{topic_index}"
        heading.set("id", topic_id)
        topics.append({"id": topic_id, "title": element_text(heading)})
        sub_index = 0
        for sub_heading in section.iter():
            if sub_heading.tag not in ("h3", "h4", "h5", "h6"):
                continue
            sub_index += 1
            sub_heading.set("id", f"{topic_id}-{sub_index}")

    lead_index = 0
    for heading in lead.iter():
        if heading.tag in ("h2", "h3", "h4", "h5", "h6"):
            lead_index += 1
            heading.set("id", f"{doc_id}-lead-{lead_index}")

    nodes = [lead, *sections]
    for node in nodes:
        for heading in list(node.iter("h2", "h3", "h4", "h5", "h6")):
            heading.tag = f"h{min(6, int(heading.tag[1]) + 1)}"

    for node in nodes:
        for heading in node.iter("h3", "h4", "h5", "h6"):
            heading_id = heading.get("id")
            if not heading_id:
                continue
            anchor = etree.SubElement(heading, "a")
            anchor.set("class", "heading-anchor")
            anchor.set("href", "#" + heading_id)
            anchor.set("aria-hidden", "true")
            anchor.text = "#"

    inlined = 0
    missing = 0
    for node in nodes:
        process_links(node)
        wrap_tables(node)
        node_inlined, node_missing = process_images(node, path, input_root)
        inlined += node_inlined
        missing += node_missing

    lead_html = ""
    if has_meaningful_content(lead):
        lead_html = lxml_html.tostring(lead, encoding="unicode", method="html")
    sections_html = "".join(
        lxml_html.tostring(section, encoding="unicode", method="html")
        for section in sections
    )

    plain_length = len(re.sub(r"\s+", "", raw))
    return {
        "id": doc_id,
        "path": path,
        "relative": path.relative_to(input_root) if path != input_root else path.name,
        "title": title,
        "desc": extract_desc(raw),
        "topics": topics,
        "lead_html": lead_html,
        "sections_html": sections_html,
        "chars": len(raw),
        "minutes": max(3, int(round(plain_length / 400))),
        "inlined": inlined,
        "missing": missing,
    }


def ascii_label(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").upper()
    return slug or "GROUP"


def build_groups(docs: list[dict], input_root: Path, is_dir: bool) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    order: list[str] = []
    for doc in docs:
        relative = doc["path"].relative_to(input_root)
        key = relative.parts[0] if is_dir and len(relative.parts) > 1 else ""
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(doc)

    groups = []
    for position, key in enumerate(order, 1):
        group_docs = buckets[key]
        group_id = f"group-{position:02d}"
        title = key if key else (input_root.name if is_dir else "单篇文档")
        groups.append({
            "id": group_id,
            "key": key,
            "title": title,
            "kicker": f"PART {position:02d}",
            "label": ascii_label(key) if key else "DOCS",
            "desc": f"本组共 {len(group_docs)} 篇文档，约 {sum(doc['minutes'] for doc in group_docs)} 分钟。",
            "docs": group_docs,
        })
    return groups


def build_nav(groups: list[dict]) -> str:
    blocks = []
    for group in groups:
        parts = [
            '<div class="nav-group">',
            f'<div class="nav-group-head"><span>{html.escape(group["title"])}</span><em>{len(group["docs"]):02d}</em></div>',
        ]
        for doc in group["docs"]:
            search_bits = [doc["title"], doc["desc"]] + [topic["title"] for topic in doc["topics"]]
            search_value = html.escape(" ".join(search_bits), quote=True)
            parts.append(f'<div class="nav-item" data-doc="{doc["id"]}" data-search="{search_value}">')
            parts.append('<div class="nav-row">')
            parts.append(
                f'<a class="nav-link" href="#{doc["id"]}"><span class="nav-no">{doc["nav_no"]}</span>'
                f'<span class="nav-title">{html.escape(doc["short"])}</span></a>'
            )
            if doc["topics"]:
                parts.append(
                    f'<button class="nav-expand" type="button" aria-expanded="false" '
                    f'aria-controls="subs-{doc["id"]}" aria-label="展开 {html.escape(doc["short"], quote=True)} 的章节">'
                    f'{ICON_CHEVRON_RIGHT}</button>'
                )
            parts.append("</div>")
            if doc["topics"]:
                parts.append(f'<div class="nav-subs" id="subs-{doc["id"]}" hidden>')
                for topic in doc["topics"]:
                    parts.append(
                        f'<a class="nav-sub" href="#{topic["id"]}">{html.escape(topic["title"])}</a>'
                    )
                parts.append("</div>")
            parts.append("</div>")
        parts.append("</div>")
        blocks.append("".join(parts))
    return "\n".join(blocks)


def build_index(groups: list[dict], docs: list[dict]) -> str:
    panels = []
    if len(groups) > 1:
        group_items = []
        for position, group in enumerate(groups, 1):
            group_items.append(
                f'<li><a href="#{group["id"]}"><span class="index-no">{position:02d}</span>'
                f'<span class="index-title">{html.escape(group["title"])}</span>'
                f'<span class="index-meta">{len(group["docs"])} 篇</span></a></li>'
            )
        panels.append(
            '<article class="index-panel">'
            '<p class="kicker">GROUPS</p>'
            '<h3>分组导航</h3>'
            f'<p>{len(groups)} 个分组，按目录结构整理。</p>'
            f'<ol class="index-list">{"".join(group_items)}</ol>'
            '</article>'
        )

    doc_items = []
    for doc in docs:
        doc_items.append(
            f'<li><a href="#{doc["id"]}"><span class="index-no">{doc["nav_no"]}</span>'
            f'<span class="index-title">{html.escape(doc["short"])}</span>'
            f'<span class="index-meta">{doc["minutes"]} 分钟</span></a></li>'
        )
    panels.append(
        '<article class="index-panel index-panel--wide">'
        '<p class="kicker">DOCUMENTS · ALL</p>'
        '<h3>全部文档</h3>'
        f'<p>共 {len(docs)} 篇，按目录顺序排列。</p>'
        f'<ol class="index-list">{"".join(doc_items)}</ol>'
        '</article>'
    )
    return "\n".join(panels)


def build_document_html(doc: dict) -> str:
    if doc["topics"]:
        toc_items = "".join(
            f'<li><a href="#{topic["id"]}">{html.escape(topic["title"])}</a></li>'
            for topic in doc["topics"]
        )
        toc = (
            '<details class="doc-toc">'
            f'<summary><span>本文章节</span><em>{len(doc["topics"])}</em>{ICON_CHEVRON_DOWN}</summary>'
            f'<ol>{toc_items}</ol></details>'
        )
    else:
        toc = ""

    return (
        f'<article class="doc reveal" id="{doc["id"]}" data-doc="{doc["id"]}">'
        f'<header class="doc-head">'
        f'<div class="doc-meta"><span class="doc-badge">{html.escape(doc["badge"])}</span>'
        f'<span class="meta-dot" aria-hidden="true"></span><span>约 {doc["minutes"]} 分钟</span>'
        f'<span class="meta-dot" aria-hidden="true"></span><span>{doc["chars"]:,} 字符</span>'
        f'<span class="meta-dot" aria-hidden="true"></span><span>{len(doc["topics"])} 节</span></div>'
        f'<h2 class="doc-title">{html.escape(doc["title"])}</h2>'
        f'<p class="doc-desc">{html.escape(doc["desc"])}</p>'
        f'</header>{toc}<div class="paper">{doc["lead_html"]}{doc["sections_html"]}</div>'
        f'<div class="doc-end"><a href="#index">↑ 返回文档索引</a></div>'
        f'</article>'
    )


def build_group_sections(groups: list[dict]) -> str:
    blocks = []
    for group in groups:
        docs_html = "\n".join(build_document_html(doc) for doc in group["docs"])
        blocks.append(
            f'<section class="doc-group" aria-labelledby="{group["id"]}-title">'
            f'<div class="group-head reveal" id="{group["id"]}">'
            f'<div><p class="kicker">{group["kicker"]} · {group["label"]}</p>'
            f'<h2 id="{group["id"]}-title">{html.escape(group["title"])}</h2>'
            f'<p>{html.escape(group["desc"])}</p></div>'
            f'<span class="group-stamp" aria-hidden="true">{len(group["docs"]):02d}<small>篇</small></span>'
            f'</div>{docs_html}</section>'
        )
    return "\n".join(blocks)


def build_overview(groups: list[dict], docs: list[dict]) -> str:
    rows: list[tuple[str, str]] = []
    if len(groups) > 1:
        rows = [(group["title"], f'{len(group["docs"])} 篇') for group in groups]
    else:
        for doc in docs[:8]:
            rows.append((doc["short"], f'{len(doc["topics"])} 节'))
    items = []
    for position, (name, meta) in enumerate(rows, 1):
        items.append(
            f'<li class="is-included"><span class="stage-no">{position:02d}</span>'
            f'<span class="stage-name">{html.escape(name)}</span>'
            f'<span class="stage-state">{html.escape(meta)}</span></li>'
        )
    remaining = len(docs) - 8
    if len(groups) <= 1 and remaining > 0:
        items.append(
            f'<li><span class="stage-no">+</span>'
            f'<span class="stage-name">其余 {remaining} 篇文档</span>'
            f'<span class="stage-state">已收录</span></li>'
        )
    return "".join(items)


def make_favicon() -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="16" fill="#2f6bff"/>'
        '<text x="32" y="42" text-anchor="middle" font-family="Consolas,monospace" '
        'font-size="25" font-weight="700" fill="#f8fbff">MD</text></svg>'
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")


def build_page(docs: list[dict], groups: list[dict], title: str, subtitle: str, source_label: str) -> str:
    css = (ASSETS / "theme.css").read_text(encoding="utf-8")
    js = (ASSETS / "app.js").read_text(encoding="utf-8")

    total_chars = sum(doc["chars"] for doc in docs)
    total_topics = sum(len(doc["topics"]) for doc in docs)
    total_minutes = sum(doc["minutes"] for doc in docs)
    brand_title = title if len(title) <= 14 else title[:13] + "…"

    values = {
        "@@TITLE@@": html.escape(f"{title} · 可视化文档"),
        "@@DESC@@": html.escape(
            f"{title}：{len(docs)} 篇 Markdown 的可视化阅读版，含章节导航、目录检索与阅读进度。",
            quote=True,
        ),
        "@@FAVICON@@": make_favicon(),
        "@@CSS@@": css,
        "@@JS@@": js,
        "@@ICON_MENU@@": ICON_MENU,
        "@@ICON_SEARCH@@": ICON_SEARCH,
        "@@ICON_UP@@": ICON_UP,
        "@@BRAND_TITLE@@": html.escape(brand_title),
        "@@BRAND_MARK@@": "MD",
        "@@EYEBROW@@": html.escape(f"MARKDOWN · VISUAL LIBRARY"),
        "@@HERO_TITLE@@": html.escape(title),
        "@@HERO_SUBTITLE@@": html.escape(subtitle),
        "@@HERO_SUB@@": html.escape(
            f"将 {source_label} 中的 {len(docs)} 篇 Markdown 汇成一册：完整保留正文，"
            "加入章节导航、目录检索与阅读进度，双击即可离线阅读。"
        ),
        "@@FIRST_DOC@@": docs[0]["id"],
        "@@DOC_COUNT@@": str(len(docs)),
        "@@TOPIC_COUNT@@": str(total_topics),
        "@@CHAR_COUNT@@": f"{total_chars / 10000:.1f}",
        "@@READ_HOURS@@": f"{total_minutes / 60:.1f}",
        "@@TOPBAR_META@@": f"{len(docs)} 篇 · {total_topics} 节",
        "@@SIDEBAR_META@@": f"{len(docs)} 篇文档 · {total_topics} 个章节",
        "@@OVERVIEW_TAG@@": f"{len(docs):02d} DOCS",
        "@@OVERVIEW_NOTE@@": html.escape(
            f"共收录 {len(docs)} 篇 · {total_topics} 个章节 · {total_chars / 10000:.1f} 万字。"
        ),
        "@@OVERVIEW_LIST@@": build_overview(groups, docs),
        "@@NAV@@": build_nav(groups),
        "@@INDEX@@": build_index(groups, docs),
        "@@INDEX_GRID_CLASS@@": "" if len(groups) > 1 else " index-grid--single",
        "@@GROUPS@@": build_group_sections(groups),
        "@@BUILD_DATE@@": date.today().isoformat(),
    }

    page = PAGE_TEMPLATE
    for key, value in values.items():
        page = page.replace(key, value)
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Markdown file or folder to convert")
    parser.add_argument("--out", default="", help="output HTML path or folder")
    parser.add_argument("--title", default="", help="hero title (default: input name)")
    parser.add_argument("--subtitle", default="可视化阅读", help="hero second line")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        sys.exit(f"Input not found: {input_path}")

    input_root, files = discover_markdown(input_path)
    if not files:
        sys.exit(f"No Markdown files found in: {input_path}")

    docs: list[dict] = []
    for index, path in enumerate(files, 1):
        built = build_document(path, input_root, index)
        docs.append(built)
        print(
            f"Read {built['relative']}: {len(built['topics'])} sections, "
            f"{built['chars']:,} chars, {built['inlined']} image(s) inlined, "
            f"{built['missing']} placeholder(s)"
        )

    groups = build_groups(docs, input_root, input_path.is_dir())
    for group in groups:
        for doc in group["docs"]:
            doc["nav_no"] = f"{group['docs'].index(doc) + 1:02d}"
            doc["badge"] = f"第 {doc['nav_no']} 篇"
            title = doc["title"]
            doc["short"] = title if len(title) <= 18 else title[:17] + "…"
            doc["group"] = group["id"]

    title = args.title or input_path.stem if input_path.is_file() else (args.title or input_path.name)
    source_label = input_path.name

    default_name = f"{input_path.stem}-可视化网页.html" if input_path.is_file() \
        else f"{input_path.name}-可视化网页.html"
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        if out_path.suffix.lower() != ".html":
            out_path = out_path / default_name
    else:
        out_path = input_path.parent / default_name

    page = build_page(docs, groups, title, args.subtitle, source_label)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")

    total_topics = sum(len(doc["topics"]) for doc in docs)
    print(f"Created: {out_path}")
    print(f"Documents: {len(docs)} | Topics: {total_topics} | Size: {out_path.stat().st_size / 1024:.1f} KB")
    print(f"Open: {out_path.as_uri()}")


if __name__ == "__main__":
    main()