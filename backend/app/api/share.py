"""分享与导出 API：二维码、全书/笔记/报告/分支导出。"""
from __future__ import annotations

import io
from urllib.parse import quote

import qrcode
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from .. import db
from ..ai.loader import load_parsed_book
from ..services import exporters

router = APIRouter(prefix="/api", tags=["share"])


def _download_header(filename: str) -> dict:
    return {"Content-Disposition":
            f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}"}


@router.get("/qrcode")
def make_qr(data: str = Query(...)):
    img = qrcode.make(data, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/books/{bid}/export")
def export_book(bid: int, format: str = "markdown", type: str = "full",
                branch_id: int | None = None):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404)
    book = load_parsed_book(bid)
    branch_row = None
    if branch_id:
        branch_row = db.query_one("SELECT * FROM branches WHERE id=?", (branch_id,))
    fname = book.title
    if type == "notes":
        data = exporters.export_markdown(book, mode="notes")
        media, ext = "text/markdown; charset=utf-8", "md"
    elif type == "report":
        data = exporters.export_markdown(book, mode="report")
        media, ext = "text/markdown; charset=utf-8", "md"
    elif branch_row:
        fname += f"-{branch_row['name']}"
        if format == "txt":
            data, media, ext = exporters.export_text(book, branch_row, "branch"), \
                "text/plain; charset=utf-8", "txt"
        elif format == "epub":
            data, media, ext = exporters.export_epub(book, branch_row, "branch"), \
                "application/epub+zip", "epub"
        else:
            data, media, ext = exporters.export_markdown(book, branch_row, "branch"), \
                "text/markdown; charset=utf-8", "md"
    else:
        if format == "txt":
            data, media, ext = exporters.export_text(book), "text/plain; charset=utf-8", "txt"
        elif format == "epub":
            data, media, ext = exporters.export_epub(book), "application/epub+zip", "epub"
        else:
            data, media, ext = exporters.export_markdown(book), \
                "text/markdown; charset=utf-8", "md"
    if isinstance(data, str):
        data = data.encode("utf-8")
    return Response(content=data, media_type=media,
                    headers=_download_header(f"{fname}.{ext}"))
