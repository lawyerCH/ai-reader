"""演示数据种子：预装《阿Q正传》《孔乙己》《一件小事》（鲁迅，公有领域），
并生成完整分析、批注、示例分支、阅读统计。

运行：python -m app.seed        （幂等：已存在同名书则跳过）
"""
from __future__ import annotations

import datetime
import random
from pathlib import Path

from . import db
from .db import now
from .parsers import parse_file
from .ai.pipeline import run_pipeline
from .ai import rewrite as rw
from .ai.loader import get_structure
from .services.covers import make_cover_svg

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

SEED_BOOKS = [
    ("阿Q正传.md", {"author": "鲁迅", "status": "reading",
                    "tags": ["经典", "中篇", "讽刺"], "intro_hint": ""}),
    ("孔乙己.md", {"author": "鲁迅", "status": "finished",
                   "tags": ["经典", "短篇", "人情"]}),
    ("一件小事.md", {"author": "鲁迅", "status": "want",
                     "tags": ["经典", "短篇"]}),
]


def _seed_book(fname: str, meta: dict):
    path = SEED_DIR / fname
    title_guess = fname.rsplit(".", 1)[0]
    exists = db.query_one("SELECT id FROM books WHERE title=?", (title_guess,))
    if exists:
        return exists["id"]
    parsed = parse_file(path)
    parsed.author = meta["author"]
    bid = db.execute(
        "INSERT INTO books(title,author,intro,cover,format,status,tags,language,"
        "word_count,chapter_count,source_name,meta,created_at,updated_at,last_read_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (parsed.title, parsed.author, parsed.intro[:400],
         make_cover_svg(parsed.title, parsed.author),
         parsed.fmt, meta["status"], db.jdumps(meta["tags"]), "zh",
         parsed.word_count, len(parsed.chapters), fname,
         db.jdumps({"seed": True}), now(), now(),
         now() if meta["status"] == "reading" else None),
    )
    rows = [(bid, i, c.title, "\n".join(c.paragraphs), db.jdumps(c.paragraphs), c.word_count)
            for i, c in enumerate(parsed.chapters)]
    db.executemany(
        "INSERT INTO chapters(book_id,idx,title,content,paragraphs,word_count)"
        " VALUES(?,?,?,?,?,?)", rows)
    result = run_pipeline(bid, parsed)
    print(f"  ✓ {parsed.title}：{len(parsed.chapters)} 章 / {parsed.word_count} 字，"
          f"{result['annotations']} 条批注，{result['characters']} 个人物")
    return bid


def _seed_progress_and_stats(bid: int, n_chapters: int, status: str):
    if status == "reading":
        ch = min(6, n_chapters - 1)
        db.execute(
            "INSERT OR REPLACE INTO progress(book_id,chapter_idx,para_idx,offset,percent,updated_at)"
            " VALUES(?,?,?,?,?,?)", (bid, ch, 0, 0.55, 0.55, now()))
        # 模拟最近 14 天的阅读记录（看板图表）
        for d in range(13, -1, -1):
            day = (datetime.date.today() - datetime.timedelta(days=d)).isoformat()
            secs = random.choice([0, 0, 620, 1180, 1540, 2400, 800])
            if secs:
                db.execute("INSERT INTO sessions(book_id,day,seconds,words) VALUES(?,?,?,?)",
                           (bid, day, secs, secs * 7))
    elif status == "finished":
        db.execute(
            "INSERT OR REPLACE INTO progress(book_id,chapter_idx,para_idx,offset,percent,updated_at)"
            " VALUES(?,?,?,?,?,?)", (bid, n_chapters - 1, 0, 1.0, 1.0, now()))
        for d in range(30, 16, -1):
            day = (datetime.date.today() - datetime.timedelta(days=d)).isoformat()
            db.execute("INSERT INTO sessions(book_id,day,seconds,words) VALUES(?,?,?,?)",
                       (bid, day, random.choice([700, 1200, 900]), 5000))
        db.execute("UPDATE books SET last_read_at=? WHERE id=?",
                   ((datetime.date.today() - datetime.timedelta(days=16)).isoformat(), bid))


def _seed_highlights_bookmarks(bid: int):
    paras = db.jloads(db.query_one(
        "SELECT paragraphs FROM chapters WHERE book_id=? AND idx=?", (bid, 2))["paragraphs"], [])
    if len(paras) > 5:
        db.execute(
            "INSERT INTO highlights(book_id,chapter_idx,para_idx,start,length,text,color,note,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (bid, 2, 5, 0, min(24, len(paras[5])), paras[5][:24], "yellow", "", now()))
    db.execute(
        "INSERT INTO bookmarks(book_id,chapter_idx,para_idx,preview,note,created_at)"
        " VALUES(?,?,?,?,?,?)",
        (bid, 6, 0, "第七章 革命", "革命闹剧开始", now()))


def _seed_branch(bid: int):
    if db.query_one("SELECT id FROM branches WHERE book_id=?", (bid,)):
        return
    st = get_structure(bid)
    # 结局改写（从第八章开始改 HE）
    r = rw.rewrite("ending", "我不喜欢这个悲剧结局，让阿Q活下来，沉冤得雪，来一个温暖的好结局",
                   st, chapter_idx=8)
    db.execute(
        "INSERT INTO branches(book_id,parent_id,name,instruction,scope,chapter_idx,content,"
        "status,meta,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (bid, None, "阿Q活下来了（HE改写）",
         "让主角活下来、沉冤得雪的好结局", "ending", 8, r["text"], "ready",
         db.jdumps({"plan": r["plan"], "word_count": r["word_count"]}), now()))
    # 再挂一个子分支
    r2 = rw.rewrite("chapter", "在结局前加一段吴妈为阿Q作证的情节", st, chapter_idx=8)
    db.execute(
        "INSERT INTO branches(book_id,parent_id,name,instruction,scope,chapter_idx,content,"
        "status,meta,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (bid, db.query_one("SELECT MAX(id) m FROM branches WHERE book_id=?", (bid,))["m"],
         "吴妈作证", "加一段吴妈为阿Q作证的情节", "chapter", 8, r2["text"], "ready",
         db.jdumps({"plan": r2["plan"], "word_count": r2["word_count"]}), now()))


def run():
    random.seed(42)
    print("🌱 写入演示数据……")
    for fname, meta in SEED_BOOKS:
        bid = _seed_book(fname, meta)
        n = db.query_one(
            "SELECT COUNT(*) c FROM chapters WHERE book_id=?", (bid,))["c"]
        _seed_progress_and_stats(bid, n, meta["status"])
        if fname.startswith("阿"):
            _seed_highlights_bookmarks(bid)
            _seed_branch(bid)
    print("✅ 种子完成。默认书：《阿Q正传》——打开即可看到 AI 读书会。")


if __name__ == "__main__":
    run()
