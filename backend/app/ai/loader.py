"""从数据库装配 ParsedBook（供分析/问答/改写复用）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import db


@dataclass
class LoadedChapter:
    title: str
    paragraphs: list[str] = field(default_factory=list)

    @property
    def word_count(self):
        return sum(len(p) for p in self.paragraphs)


@dataclass
class LoadedBook:
    id: int
    title: str
    author: str
    intro: str
    fmt: str
    chapters: list


def load_parsed_book(book_id: int) -> LoadedBook:
    brow = db.query_one("SELECT * FROM books WHERE id=?", (book_id,))
    if not brow:
        raise ValueError(f"book {book_id} not found")
    ch_rows = db.query(
        "SELECT title, paragraphs FROM chapters WHERE book_id=? ORDER BY idx",
        (book_id,))
    chapters = []
    for r in ch_rows:
        paragraphs = db.jloads(r["paragraphs"], [])
        chapters.append(LoadedChapter(title=r["title"], paragraphs=paragraphs))
    return LoadedBook(
        id=book_id, title=brow["title"], author=brow["author"] or "",
        intro=brow["intro"] or "", fmt=brow["format"], chapters=chapters,
    )


def get_structure(book_id: int) -> dict:
    return {
        "characters": db.get_analysis(book_id, "characters", []),
        "relations": db.get_analysis(book_id, "relations", []),
        "timeline": db.get_analysis(book_id, "timeline", []),
        "locations": db.get_analysis(book_id, "locations", []),
        "settings": db.get_analysis(book_id, "settings", []),
        "foreshadows": db.get_analysis(book_id, "foreshadows", []),
    }
