"""多格式书籍解析：TXT / Markdown / EPUB / PDF，统一输出 ParsedBook。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

CN_NUM = "零一二三四五六七八九十百千万两〇"
CHAPTER_RE = re.compile(rf"^\s*第[0-9{CN_NUM}]+[章节回卷部集篇]\s*.{{0,40}}$")
PLAIN_CH_RE = re.compile(r"^\s*(?:Chapter\s*)?(\d{1,4})\s*[、.．:：\s][^\n]{1,40}$", re.I)
MD_HEADING_RE = re.compile(r"^\s{0,3}(#{1,3})\s+(.+?)\s*#*\s*$")
SENT_END = "。！？…」）)】"


@dataclass
class ParsedChapter:
    title: str
    paragraphs: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(len(p) for p in self.paragraphs)


@dataclass
class ParsedBook:
    title: str
    author: str = ""
    intro: str = ""
    fmt: str = "txt"
    chapters: list[ParsedChapter] = field(default_factory=list)
    raw_front: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(c.word_count for c in self.chapters)


def clean_text(text: str) -> str:
    """统一清洗：去 markdown 代码围栏、注释标记、零宽字符、回车。"""
    text = text.replace("　", "  ")
    text = re.sub(r"```[a-zA-Z]*", "", text)
    text = "".join(c for c in text if not (0x2460 <= ord(c) <= 0x2487))  # 脚注圈号
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[​‌‍﻿]", "", text)
    return text


def _heading_of(stripped: str) -> str | None:
    """识别章节标题行，返回标题（去缩进），否则 None。"""
    if len(stripped) <= 42 and CHAPTER_RE.match(stripped):
        return stripped
    if len(stripped) <= 42 and PLAIN_CH_RE.match(stripped):
        return stripped
    return None


def _flush(buf: list[str], sink: list[str]) -> None:
    if not buf:
        return
    p = "".join(buf).strip()
    p = p.replace(" ", "")
    if p:
        sink.append(p)
    buf.clear()


def _lines_to_chapters(lines: list[str]) -> tuple[list[ParsedChapter], list[str]]:
    """把文本行切成章节；返回 (章节列表, 前言段落)。"""
    chapters: list[ParsedChapter] = []
    front: list[str] = []
    cur: ParsedChapter | None = None
    para_buf: list[str] = []
    sink: list[str] = front
    found = False
    first_heading_consumed = False

    for raw in lines:
        stripped = raw.strip()

        m_md = MD_HEADING_RE.match(raw)
        heading = None
        if m_md:
            heading = m_md.group(2).strip()
            # 形如 "第X章" 的 markdown 标题当然算；普通短标题也视作章节
            if len(heading) > 42:
                heading = None
        else:
            heading = _heading_of(stripped)
        if heading:
            heading = re.sub(r"\s+", " ", heading).strip()

        if heading:
            # 文档中第一个"非章节式"的 Markdown 标题通常是书名，归入前言
            if (not found and not first_heading_consumed and m_md
                    and not _heading_of(heading)):
                first_heading_consumed = True
                _flush(para_buf, sink)
                front.append(heading)
                sink = front
                continue
            first_heading_consumed = True
            _flush(para_buf, sink)
            if not found:
                if sum(len(x) for x in front) > 20:
                    chapters.append(ParsedChapter(title="引子", paragraphs=list(front)))
                found = True
            cur = ParsedChapter(title=heading)
            chapters.append(cur)
            sink = cur.paragraphs
            continue

        if not stripped:
            _flush(para_buf, sink)
            continue
        # 行首缩进表示新段落开始（原文用全角空格缩进而 clean_text 转成两个空格）
        if (raw.startswith(" ") or raw.startswith("  ")) and para_buf:
            _flush(para_buf, sink)
        para_buf.append(stripped)
        if stripped[-1:] in SENT_END:
            _flush(para_buf, sink)

    _flush(para_buf, sink)

    if not found:
        # 剥离开头的书名/作者短行（居中段，无句末标点），作为前言元信息
        head: list[str] = []
        while front and len(head) < 4:
            p0 = front[0]
            if len(p0) <= 30 and not re.search(r"[。！？；：?:：]", p0):
                head.append(front.pop(0))
            else:
                break
        return ([ParsedChapter(title="正文", paragraphs=front)] if front else []), head
    return [c for c in chapters if c.word_count > 0], ([] if chapters else front)


META_TITLE_RE = re.compile(r"(?:书名|书名：|title)\s*[:：]?\s*《?([^《》\n]{1,40}?)》?\s*$", re.I)
META_AUTHOR_RE = re.compile(r"(?:作者|著者|author)\s*[:：]\s*([^\n]{1,30})$", re.I)


def parse_text(text: str, fmt: str = "txt", filename: str = "") -> ParsedBook:
    text = clean_text(text)
    lines = text.split("\n")
    chapters, front = _lines_to_chapters(lines)

    title = ""
    author = ""
    intro_parts: list[str] = []

    # 书名：前言里的首个《》或第一行非空短行；作者：显式标注或"某某 著"
    for idx, p in enumerate(front[:12]):
        mt = META_TITLE_RE.search(p)
        ma = META_AUTHOR_RE.search(p)
        if mt and not title:
            title = mt.group(1).strip()
        if ma:
            author = ma.group(1).strip()
        # 第二行居中人名词条通常是作者
        if idx == 1 and not author and 2 <= len(p) <= 6 and not re.search(r"[，。！？：:；]", p):
            author = p.strip()
        if "简介" in p or "内容简介" in p:
            intro_parts.append(p)
        elif not title and 2 <= len(p) <= 30 and "：" not in p and ":" not in p:
            title = p.strip("《》 ")
        if len(p) > 40:
            intro_parts.append(p)
    if not title and chapters:
        first = chapters[0].title
        if not _heading_of(first):
            title = first.strip("《》 ")
    if not title:
        title = Path(filename).stem if filename else "未命名小说"
    title = re.sub(r"\.(txt|md|markdown|epub|pdf)$", "", title, flags=re.I).strip() or "未命名小说"

    if not author:
        m = re.search(r"([一-龥·]{2,15})\s*(?:著|作品)\s*$", "\n".join(front[:8]))
        if m:
            author = m.group(1)

    # 单章短篇：章节名直接用书名，不显示"正文"
    if len(chapters) == 1 and chapters[0].title == "正文":
        chapters[0].title = title

    intro = "\n".join(intro_parts)[:400]
    if not intro and chapters:
        intro = chapters[0].paragraphs[0][:160] if chapters[0].paragraphs else ""

    return ParsedBook(
        title=title, author=author, intro=intro, fmt=fmt,
        chapters=chapters or [ParsedChapter(title="正文", paragraphs=["（空文档）"])],
        raw_front=front,
    )


# 延迟导入，按需解析重格式
def parse_file(path: str | "Path") -> ParsedBook:
    p = Path(path)
    suffix = p.suffix.lower()
    data = p.read_bytes()

    if suffix in (".txt", ".text", ".md", ".markdown"):
        return parse_text(data.decode("utf-8", errors="ignore"),
                          "md" if suffix in (".md", ".markdown") else "txt", p.name)
    if suffix == ".epub":
        from ._epub import parse_epub
        return parse_epub(data, p.name)
    if suffix == ".pdf":
        from ._pdf import parse_pdf
        return parse_pdf(data, p.name)
    # 兜底：按文本试解析
    return parse_text(data.decode("utf-8", errors="ignore"), "txt", p.name)
