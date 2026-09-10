"""REST / WebSocket 端到端测试。"""
import asyncio
import json

import pytest


def test_health_and_personas(client):
    assert client.get("/api/health").json()["ok"]
    personas = client.get("/api/personas").json()
    assert len(personas) == 6


def test_import_and_book_flow(client, sample_book):
    bid = sample_book
    # 书架
    books = client.get("/api/books").json()
    assert any(b["id"] == bid for b in books)
    # 章节
    chs = client.get(f"/api/books/{bid}/chapters").json()
    assert len(chs) == 3
    # 正文
    ch0 = client.get(f"/api/books/{bid}/chapters/0").json()
    assert len(ch0["paragraphs"]) >= 3
    # 分析结果
    chars = client.get(f"/api/books/{bid}/characters").json()
    assert any(c["name"] == "林秋白" for c in chars)
    assert client.get(f"/api/books/{bid}/relations").json()
    assert client.get(f"/api/books/{bid}/timeline").json()
    assert client.get(f"/api/books/{bid}/foreshadows").status_code == 200
    # 批注：密度过滤
    dense = client.get(f"/api/books/{bid}/annotations",
                       params={"chapter": 0, "density": "dense"}).json()
    sparse = client.get(f"/api/books/{bid}/annotations",
                        params={"chapter": 0, "density": "sparse"}).json()
    assert len(dense) >= len(sparse)
    personas = {a["persona"] for a in dense}
    assert len(personas) >= 4
    # 章末小结
    digest = client.get(f"/api/books/{bid}/chapters/2/digest").json()
    assert digest["summary"]


def test_ask_discuss_debate(client, sample_book):
    bid = sample_book
    r = client.post(f"/api/books/{bid}/ask", json={"q": "林秋白是谁？", "persona": "plot"}).json()
    assert r["answer"] and r["refs"]
    d = client.post(f"/api/books/{bid}/discuss", json={"q": "黑衣人是谁？"}).json()
    assert len(d["answers"]) >= 5
    b = client.post(f"/api/books/{bid}/debate", json={"topic": "复仇合理吗？"}).json()
    assert len(b["turns"]) == 4
    w = client.post(f"/api/books/{bid}/whatif", json={"hypothesis": "如果主角没有跳崖"}).json()
    assert len(w["answers"]) == 5


def test_branches_tree_and_export(client, sample_book):
    bid = sample_book
    r = client.post(f"/api/books/{bid}/branches", json={
        "scope": "ending", "chapter_idx": 2,
        "instruction": "让主角复仇成功，给一个大团圆结局",
        "name": "大团圆",
    }).json()
    br_id = r["id"]
    assert r["word_count"] > 100
    tree = client.get(f"/api/books/{bid}/branches/tree").json()
    names = [c["name"] for c in tree["children"]]
    assert "大团圆" in names
    mat = client.get(f"/api/books/{bid}/branches/{br_id}/materialized").json()
    assert mat["overrides"]
    # 三种导出
    for fmt, ct in [("txt", "text/plain"), ("markdown", "text/markdown"), ("epub", "epub")]:
        resp = client.get(f"/api/books/{bid}/branches/{br_id}/export?format={fmt}")
        assert resp.status_code == 200 and ct in resp.headers["content-type"]
    # 笔记导出
    assert client.get(f"/api/books/{bid}/export?type=notes").status_code == 200


def test_progress_bookmarks_highlights_stats(client, sample_book):
    bid = sample_book
    assert client.put(f"/api/books/{bid}/progress",
                      json={"chapter_idx": 2, "percent": 0.8}).json()["ok"]
    assert client.post(f"/api/books/{bid}/sessions",
                       json={"seconds": 600, "words": 3000}).json()["ok"]
    bm = client.post(f"/api/books/{bid}/bookmarks",
                     json={"chapter_idx": 1, "preview": "测试", "note": ""}).json()
    assert bm["id"]
    hl = client.post(f"/api/books/{bid}/highlights",
                     json={"chapter_idx": 1, "para_idx": 0, "start": 0,
                           "length": 4, "text": "测试", "color": "yellow"}).json()
    assert hl["id"]
    stats = client.get("/api/stats/overview").json()
    assert stats["book_count"] >= 1 and stats["total_seconds"] >= 600


def test_epub_import_and_pdf_parse(client):
    import io, ebooklib
    from ebooklib import epub
    from app.parsers import parse_file

    # 内存中构造 EPUB
    eb = epub.EpubBook()
    eb.set_identifier("t"); eb.set_title("测试武侠"); eb.set_language("zh")
    eb.add_author("某人")
    pages = []
    for i, body in enumerate(["李玄风在山门前大笑。", "忽然黑衣人从天而降，他一掌击出。"]):
        c = epub.EpubHtml(title=f"第{i+1}章", file_name=f"c{i}.xhtml")
        c.content = f"<h1>第{i+1}章</h1><p>{body}</p>"
        eb.add_item(c); pages.append(c)
    eb.toc = tuple(pages); eb.spine = ["nav"] + pages
    eb.add_item(epub.EpubNcx()); eb.add_item(epub.EpubNav())
    buf = io.BytesIO(); ebooklib.epub.write_epub(buf, eb)

    r = client.post("/api/books/import", files=[
        ("files", ("test.epub", buf.getvalue(), "application/epub+zip"))])
    assert r.status_code == 200
    bid = r.json()["created"][0]
    import time
    from app.services import books as bs
    for _ in range(40):
        if bs.analyze_status(bid)["status"] == "analyzed":
            break
        time.sleep(0.25)
    chs = client.get(f"/api/books/{bid}/chapters").json()
    assert len(chs) == 2
    assert client.get(f"/api/books/{bid}").json()["title"] == "测试武侠"

    # 无法解析的二进制 PDF 应优雅降级（不抛异常）
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"not a real pdf"); p = f.name
    bk = parse_file(p)
    os.unlink(p)
    assert bk.chapters  # 永远返回结构，不崩溃


def test_qrcode(client):
    r = client.get("/api/qrcode", params={"data": "http://example.com/book/1"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_websocket_rewrite_and_read(client, sample_book):
    import websockets
    bid = sample_book

    async def run():
        # 流式改写
        async with websockets.connect(
                f"ws://127.0.0.1:{client.port}/ws/rewrite/{bid}") as ws:
            await ws.send(json.dumps({
                "scope": "paragraph", "chapter_idx": 0, "para_idx": 0,
                "instruction": "让主角扬眉吐气", "name": "WS测试",
            }))
            full, branch = "", None
            while True:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                if m.get("event") == "delta":
                    full += m["delta"]
                if m.get("event") == "done":
                    branch = m["branch_id"]
                    break
            assert len(full) > 20 and branch
        # 陪读批注流
        async with websockets.connect(
                f"ws://127.0.0.1:{client.port}/ws/read/{bid}") as ws:
            await ws.send(json.dumps({"chapter": 0, "density": "sparse"}))
            kinds = []
            while True:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                kinds.append(m["event"])
                if m["event"] == "done":
                    break
            assert "annotation" in kinds and "digest" in kinds

    # 给 TestClient 选一个空闲端口并启动 ASGI server
    import uvicorn
    import socket
    from app.main import app as asgi_app
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(asgi_app, port=port, log_level="error"))
    config = client  # noqa: hold fixture
    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    client.port = port
    import time
    for _ in range(40):
        try:
            import httpx
            if httpx.get(f"http://127.0.0.1:{port}/api/health").status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.25)
    asyncio.run(run())
