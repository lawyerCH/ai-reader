"""书籍导入、入库与分析调度。"""
from __future__ import annotations

import shutil
import threading
from pathlib import Path

from .. import db
from ..db import now
from ..config import BOOK_FILES
from ..parsers import parse_file, ParsedBook
from ..ai.pipeline import run_pipeline
from .covers import make_cover_svg


def import_file(path: str | Path, original_name: str = "", move: bool = False) -> int:
    path = Path(path)
    name = original_name or path.name
    stored = BOOK_FILES / f"{path.stem}_{path.suffix}"
    if move:
        shutil.move(str(path), stored)
    else:
        shutil.copy2(path, stored)
    parsed = parse_file(stored)
    return create_book(parsed, source_name=name, stored_path=str(stored))


def create_book(parsed: ParsedBook, source_name: str = "", stored_path: str = "") -> int:
    from ..db import now
    bid = db.execute(
        "INSERT INTO books(title,author,intro,cover,format,status,tags,language,"
        "word_count,chapter_count,source_name,meta,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (parsed.title, parsed.author, parsed.intro, "", parsed.fmt, "want",
         db.jdumps([]), "zh", parsed.word_count, len(parsed.chapters),
         source_name or parsed.title, db.jdumps({"stored_path": stored_path}),
         now(), now()),
    )
    cover = make_cover_svg(parsed.title, parsed.author, parsed.intro)
    _insert_chapters(bid, parsed)
    db.execute("UPDATE books SET cover=? WHERE id=?", (cover, bid))
    set_status(bid, "analyzing")
    threading.Thread(target=_analyze_safe, args=(bid, parsed), daemon=True).start()
    return bid


def _insert_chapters(bid: int, parsed: ParsedBook):
    rows = []
    for i, ch in enumerate(parsed.chapters):
        rows.append((bid, i, ch.title, "\n".join(ch.paragraphs),
                     db.jdumps(ch.paragraphs), ch.word_count))
    db.executemany(
        "INSERT INTO chapters(book_id,idx,title,content,paragraphs,word_count) "
        "VALUES(?,?,?,?,?,?)", rows)


def _analyze_safe(bid: int, parsed):
    try:
        result = run_pipeline(bid, parsed)
        set_status(bid, "analyzed" if bid > 0 else "ready", result=result)
    except Exception as e:  # noqa: BLE001
        set_status(bid, "error", error=str(e))
        raise


def set_status(bid: int, status: str, result=None, error=None):
    db.setting_set(f"analyze:{bid}", {"status": status, "result": result, "error": error})
    db.execute("UPDATE books SET updated_at=? WHERE id=?", (now(), bid))


def analyze_status(bid: int) -> dict:
    return db.setting_get(f"analyze:{bid}", {"status": "ready"})


def reanalyze(bid: int) -> dict:
    from ..ai.loader import load_parsed_book
    set_status(bid, "analyzing")
    book = load_parsed_book(bid)

    def job():
        try:
            result = run_pipeline(bid, book)
            set_status(bid, "analyzed", result=result)
        except Exception as e:  # noqa: BLE001
            set_status(bid, "error", error=str(e))
    threading.Thread(target=job, daemon=True).start()
    return {"status": "analyzing"}
