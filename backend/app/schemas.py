"""Pydantic 请求/响应模型（保持精简，大部分载荷直接使用 dict）。"""
from pydantic import BaseModel, Field


class AskIn(BaseModel):
    q: str
    persona: str = "plot"
    chapter_idx: int | None = None
    conversation_id: int | None = None


class DiscussIn(BaseModel):
    q: str
    chapter_idx: int | None = None
    personas: list[str] | None = None


class DebateIn(BaseModel):
    topic: str
    side_a: str = "plot"
    side_b: str = "snark"
    chapter_idx: int | None = None


class WhatIfIn(BaseModel):
    hypothesis: str


class BranchIn(BaseModel):
    parent_id: int | None = None
    name: str = "我的改写"
    instruction: str
    scope: str = "paragraph"   # paragraph/chapter/ending/full
    chapter_idx: int = 0
    para_idx: int | None = None
    original_text: str = ""
    end_chapter_idx: int | None = None


class ProgressIn(BaseModel):
    chapter_idx: int = 0
    para_idx: int = 0
    offset: float = 0
    percent: float = 0


class BookmarkIn(BaseModel):
    chapter_idx: int
    para_idx: int = 0
    preview: str = ""
    note: str = ""


class HighlightIn(BaseModel):
    chapter_idx: int
    para_idx: int
    start: int = 0
    length: int = 0
    text: str = ""
    color: str = "yellow"
    note: str = ""


class BookPatch(BaseModel):
    title: str | None = None
    author: str | None = None
    intro: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    cover: str | None = None


class SessionIn(BaseModel):
    seconds: int = 0
    words: int = 0


class ImportTextIn(BaseModel):
    filename: str = "导入小说.txt"
    text: str
    title: str | None = None
    author: str | None = None
