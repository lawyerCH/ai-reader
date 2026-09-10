"""EPUB 解析：提取元信息、按 spine 顺序还原章节。"""
from __future__ import annotations

import io
import os
import re
import tempfile

from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT

from . import ParsedBook, ParsedChapter, clean_text, _lines_to_chapters


def _html_to_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # 标题标签转换为 markdown 形式，供章节切分识别
    for h in soup.find_all(re.compile(r"^h[1-3]$")):
        h.replace_with(f"\n\n## {h.get_text(strip=True)}\n\n")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.append("\n\n")
    text = soup.get_text()
    return clean_text(text).split("\n")


def parse_epub(data: bytes, filename: str = "") -> ParsedBook:
    # ebooklib 只接受文件路径（内部会 os.path.isdir），写临时文件
    tmp = tempfile.NamedTemporaryFile(suffix=".epub", delete=False)
    try:
        tmp.write(data); tmp.flush(); tmp.close()
        book = epub.read_epub(tmp.name, options={"ignore_ncx": True})
    finally:
        try: os.unlink(tmp.name)
        except OSError: pass

    title = ""
    author = ""
    try:
        tm = book.get_metadata("DC", "title")
        cm = book.get_metadata("DC", "creator")
        title = tm[0][0] if tm else ""
        author = cm[0][0] if cm else ""
    except Exception:
        pass

    chapters: list[ParsedChapter] = []
    front: list[str] = []
    chapter_index = 0
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        name = item.get_name()
        if name.endswith(("nav.xhtml", "ncx.ncx", "title.xhtml")):
            continue
        lines = _html_to_lines(item.get_content().decode("utf-8", errors="ignore"))
        chs, fr = _lines_to_chapters(lines)
        if chapter_index == 0 and fr:
            front.extend(fr)
        doc_title = getattr(item, "title", "") or name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        for c in chs:
            if not c.paragraphs or c.paragraphs == ["（空文档）"]:
                continue
            if c.title == "正文":  # 单文档无显式标题时用 EPUB 文档名
                c.title = doc_title
            chapters.append(c)
        chapter_index += 1

    # 合并被 spine 切碎的同章（标题相同的连续章节）
    merged: list[ParsedChapter] = []
    for c in chapters:
        if merged and c.title == merged[-1].title:
            merged[-1].paragraphs.extend(c.paragraphs)
        else:
            merged.append(c)

    if not merged:
        merged = [ParsedChapter(title="正文", paragraphs=["（空文档）"])]

    return ParsedBook(
        title=title or filename.rsplit(".", 1)[0],
        author=author,
        intro="\n".join(front)[:400],
        fmt="epub",
        chapters=merged,
        raw_front=front,
    )
