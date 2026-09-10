"""分析流水线：解析 -> 结构化分析 -> 章节摘要 -> 六角色批注，并持久化。"""
from __future__ import annotations

from .analyze import analyze_structure
from .annotations import generate_annotations
from .summaries import summarize_chapter, golden_sentences
from .. import db


def run_pipeline(book_id: int, book=None):
    """对已入库的书籍跑全量分析。book 可传 ParsedBook（避免重新装配）。"""
    from .loader import load_parsed_book
    if book is None:
        book = load_parsed_book(book_id)

    structure = analyze_structure(book)
    char_names = [c["name"] for c in structure["characters"]]

    # 章节摘要 + 金句
    chapter_summaries = []
    for ci, ch in enumerate(book.chapters):
        present = [c["name"] for c in structure["characters"]
                   if ci in c["chapters"]][:8]
        summary, highlights = summarize_chapter(ch, present)
        golden = golden_sentences(ch, limit=3)
        db.execute(
            "INSERT OR REPLACE INTO chapter_summaries(book_id,chapter_idx,summary,highlights) "
            "VALUES(?,?,?,?)",
            (book_id, ci, summary, db.jdumps({"highlights": highlights, "golden": golden})),
        )
        chapter_summaries.append({"chapter": ci, "title": ch.title,
                                  "summary": summary, "golden": golden})

    # 批注
    db.execute("DELETE FROM annotations WHERE book_id=?", (book_id,))
    annotations = generate_annotations(book, structure)
    from ..db import now
    rows = [
        (book_id, a["chapter_idx"], a["para_idx"], a["persona"], a["kind"],
         a["title"], a["content"], a["quote"], a["priority"], now(),
         db.jdumps(a.get("payload", {})))
        for a in annotations
    ]
    db.executemany(
        "INSERT INTO annotations(book_id,chapter_idx,para_idx,persona,kind,title,"
        "content,quote,priority,created_at,payload) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )

    # 结构化结果落库
    result = {
        "characters": len(structure["characters"]),
        "relations": len(structure["relations"]),
        "timeline": len(structure["timeline"]),
        "locations": len(structure["locations"]),
        "settings": len(structure["settings"]),
        "foreshadows": len(structure["foreshadows"]),
        "annotations": len(annotations),
        "summaries": len(chapter_summaries),
    }
    db.save_analysis(book_id, "characters", structure["characters"])
    db.save_analysis(book_id, "relations", structure["relations"])
    db.save_analysis(book_id, "timeline", structure["timeline"])
    db.save_analysis(book_id, "locations", structure["locations"])
    db.save_analysis(book_id, "settings", structure["settings"])
    db.save_analysis(book_id, "foreshadows", structure["foreshadows"])
    db.save_analysis(book_id, "chapter_summaries", chapter_summaries)
    db.setting_set(f"analyze:{book_id}", {"status": "analyzed", "result": result})

    return result
