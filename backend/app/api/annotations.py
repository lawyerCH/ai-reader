"""AI 批注 API：按章节/角色/密度过滤，章末小结。"""
from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException, Query

from .. import db
from ..config import PERSONAS, PERSONA_MAP, DENSITY_PROFILES

router = APIRouter(prefix="/api/books/{bid}", tags=["annotations"])


def _require(bid: int):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404, "书籍不存在")


@router.get("/annotations")
def list_annotations(
    bid: int,
    chapter: int | None = None,
    personas: str | None = Query(None, description="逗号分隔的角色 id"),
    density: str = "normal",
):
    _require(bid)
    sql = "SELECT * FROM annotations WHERE book_id=?"
    params = [bid]
    if chapter is not None:
        sql += " AND chapter_idx=?"
        params.append(chapter)
    rows = [dict(r) for r in db.query(sql, params)]
    if personas:
        wanted = {p for p in personas.split(",") if p}
        rows = [r for r in rows if r["persona"] in wanted]

    # 密度采样：同章同角色按 priority 限额
    prof = DENSITY_PROFILES.get(density, DENSITY_PROFILES["normal"])
    buckets: dict[tuple, list] = defaultdict(list)
    for r in rows:
        buckets[(r["chapter_idx"], r["persona"])].append(r)
    out = []
    for key, items in buckets.items():
        items.sort(key=lambda x: -x["priority"])
        kept_n = max(1, int(prof["per_chapter"] / 6 * (len(PERSONAS) / 1)) + 2) \
            if density != "dense" else 99
        kept_n = {"dense": 99, "normal": 4, "sparse": 2, "keyonly": 1}[density]
        chosen = items[:kept_n]
        # keyonly 只保留高优
        if density == "keyonly":
            chosen = [c for c in chosen if c["priority"] >= 0.7] or chosen[:1]
        elif density == "sparse" and len(chosen) > 2:
            chosen = chosen[:2]
        out.extend(chosen)
    out.sort(key=lambda r: (r["chapter_idx"], r["para_idx"]))
    return out


@router.get("/annotations/stats")
def annotation_stats(bid: int):
    _require(bid)
    rows = db.query(
        "SELECT persona, COUNT(*) n FROM annotations WHERE book_id=? GROUP BY persona",
        (bid,))
    return {"by_persona": {r["persona"]: r["n"] for r in rows},
            "total": sum(r["n"] for r in rows)}


@router.get("/chapters/{idx}/digest")
def chapter_digest(bid: int, idx: int):
    """章末小结：中性摘要 + 各角色本章批注精华 + 金句。"""
    _require(bid)
    row = db.query_one(
        "SELECT summary, highlights FROM chapter_summaries WHERE book_id=? AND chapter_idx=?",
        (bid, idx))
    ch = db.query_one("SELECT title FROM chapters WHERE book_id=? AND idx=?", (bid, idx))
    anns = [dict(r) for r in db.query(
        "SELECT * FROM annotations WHERE book_id=? AND chapter_idx=? ORDER BY priority DESC",
        (bid, idx))]
    persona_picks = {}
    for a in anns:
        persona_picks.setdefault(a["persona"], a)
    golden = []
    if row:
        extra = db.jloads(row["highlights"], {})
        golden = extra.get("golden", [])
    return {
        "chapter": idx,
        "title": ch["title"] if ch else "",
        "summary": row["summary"] if row else "",
        "golden": golden,
        "persona_picks": list(persona_picks.values()),
        "annotation_count": len(anns),
    }


@router.get("/personas")
def list_personas():
    return PERSONAS
