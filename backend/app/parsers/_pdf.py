"""PDF 解析：逐页抽取文本后复用通用章节切分。"""
from __future__ import annotations

import io

from pypdf import PdfReader

from . import ParsedBook, parse_text


def parse_pdf(data: bytes, filename: str = "") -> ParsedBook:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        # 损坏/非 PDF：优雅降级为空结构，避免导入整体失败
        return parse_text("", "pdf", filename)
    pages: list[str] = []
    title = ""
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
        if i == 0:
            try:
                meta_title = reader.metadata.title if reader.metadata else ""
                title = meta_title or ""
            except Exception:
                title = ""
    text = "\n".join(pages)
    book = parse_text(text, "pdf", filename)
    if title:
        book.title = title
    return book
