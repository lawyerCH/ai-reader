"""AI 分析结果 API：人物、关系图谱、时间线、地点地图、设定百科、前情提要。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db
from ..ai.loader import load_parsed_book, get_structure
from ..ai.summaries import build_recap, character_profile

router = APIRouter(prefix="/api/books/{bid}", tags=["analysis"])


def _require(bid: int):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404, "书籍不存在")


@router.get("/characters")
def characters(bid: int):
    _require(bid)
    return db.get_analysis(bid, "characters", [])


@router.get("/characters/{name}")
def character_detail(bid: int, name: str):
    _require(bid)
    chars = db.get_analysis(bid, "characters", [])
    c = next((x for x in chars if x["name"] == name or name in x.get("aliases", [])), None)
    if not c:
        raise HTTPException(404, "人物不存在")
    book = load_parsed_book(bid)
    titles = [ch.title for ch in book.chapters]
    return {**c, "profile": character_profile(c, titles)}


@router.get("/relations")
def relations(bid: int):
    _require(bid)
    return db.get_analysis(bid, "relations", [])


@router.get("/timeline")
def timeline(bid: int):
    _require(bid)
    return db.get_analysis(bid, "timeline", [])


@router.get("/locations")
def locations(bid: int):
    _require(bid)
    return db.get_analysis(bid, "locations", [])


@router.get("/settings")
def settings(bid: int, q: str | None = None):
    _require(bid)
    items = db.get_analysis(bid, "settings", [])
    if q:
        items = [x for x in items if q in x["term"] or q in x.get("summary", "")]
    return items


@router.get("/foreshadows")
def foreshadows(bid: int, status: str | None = None):
    _require(bid)
    items = db.get_analysis(bid, "foreshadows", [])
    if status:
        items = [x for x in items if x["status"] == status]
    return items


@router.get("/recap")
def recap(bid: int, upto: int = 0):
    _require(bid)
    st = get_structure(bid)
    summaries = db.get_analysis(bid, "chapter_summaries", [])
    return build_recap(st, summaries, upto)
