"""SQLite 数据访问层（标准库 sqlite3，JSON 承载结构化分析结果）。"""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import DB_PATH

_lock = threading.RLock()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


CONN = get_conn()


def query(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with _lock:
        return CONN.execute(sql, tuple(params)).fetchall()


def query_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with _lock:
        return CONN.execute(sql, tuple(params)).fetchone()


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with _lock:
        cur = CONN.execute(sql, tuple(params))
        CONN.commit()
        return cur.lastrowid


def executemany(sql: str, seq: Iterable[Iterable[Any]]) -> None:
    with _lock:
        CONN.executemany(sql, [tuple(p) for p in seq])
        CONN.commit()


def jdumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def jloads(text: str | None, default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


SCHEMA = """
CREATE TABLE IF NOT EXISTS books(
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT DEFAULT '',
  intro TEXT DEFAULT '',
  cover TEXT DEFAULT '',
  format TEXT DEFAULT 'txt',
  status TEXT DEFAULT 'want',          -- want/reading/finished/dropped
  tags TEXT DEFAULT '[]',
  language TEXT DEFAULT 'zh',
  word_count INTEGER DEFAULT 0,
  chapter_count INTEGER DEFAULT 0,
  source_name TEXT DEFAULT '',
  meta TEXT DEFAULT '{}',
  created_at TEXT, updated_at TEXT, last_read_at TEXT
);
CREATE TABLE IF NOT EXISTS chapters(
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  idx INTEGER NOT NULL,
  title TEXT,
  content TEXT,
  paragraphs TEXT,                    -- JSON list[str]
  word_count INTEGER DEFAULT 0,
  UNIQUE(book_id, idx)
);
CREATE TABLE IF NOT EXISTS analysis(
  book_id INTEGER NOT NULL,
  kind TEXT NOT NULL,                 -- characters/relations/timeline/locations/settings/foreshadows/recap/qa_index
  payload TEXT,
  updated_at TEXT,
  PRIMARY KEY(book_id, kind)
);
CREATE TABLE IF NOT EXISTS annotations(
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  chapter_idx INTEGER NOT NULL,
  para_idx INTEGER NOT NULL,
  persona TEXT NOT NULL,
  kind TEXT,
  title TEXT,
  content TEXT,
  quote TEXT DEFAULT '',
  priority REAL DEFAULT 0.5,
  payload TEXT DEFAULT '{}',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS chapter_summaries(
  book_id INTEGER NOT NULL,
  chapter_idx INTEGER NOT NULL,
  summary TEXT,
  highlights TEXT,
  PRIMARY KEY(book_id, chapter_idx)
);
CREATE TABLE IF NOT EXISTS conversations(
  id INTEGER PRIMARY KEY,
  book_id INTEGER,
  scope TEXT DEFAULT 'book',          -- book/chapter/annotation/branch
  anchor TEXT DEFAULT '',
  title TEXT DEFAULT '',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL,
  role TEXT,                          -- user/persona/system
  persona TEXT DEFAULT '',
  content TEXT,
  refs TEXT DEFAULT '[]',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS branches(
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  parent_id INTEGER,                  -- NULL = 挂在原版根上
  name TEXT,
  instruction TEXT,
  scope TEXT DEFAULT 'paragraph',     -- paragraph/chapter/ending/full
  chapter_idx INTEGER,
  para_idx INTEGER,
  end_chapter_idx INTEGER,
  content TEXT,
  replace_from INTEGER,
  replace_to INTEGER,
  status TEXT DEFAULT 'ready',
  meta TEXT DEFAULT '{}',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS progress(
  book_id INTEGER PRIMARY KEY,
  chapter_idx INTEGER DEFAULT 0,
  para_idx INTEGER DEFAULT 0,
  offset REAL DEFAULT 0,
  percent REAL DEFAULT 0,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS bookmarks(
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  chapter_idx INTEGER, para_idx INTEGER,
  preview TEXT, note TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS highlights(
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  chapter_idx INTEGER, para_idx INTEGER,
  start INTEGER, length INTEGER,
  text TEXT, color TEXT DEFAULT 'yellow',
  note TEXT DEFAULT '', created_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  day TEXT NOT NULL,
  seconds INTEGER DEFAULT 0,
  words INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kv(
  k TEXT PRIMARY KEY, v TEXT
);
"""


def init_db() -> None:
    with _lock:
        CONN.executescript(SCHEMA)
        CONN.commit()


def save_analysis(book_id: int, kind: str, payload: Any) -> None:
    execute(
        "INSERT OR REPLACE INTO analysis(book_id,kind,payload,updated_at) VALUES(?,?,?,?)",
        (book_id, kind, jdumps(payload), now()),
    )


def get_analysis(book_id: int, kind: str, default=None):
    row = query_one("SELECT payload FROM analysis WHERE book_id=? AND kind=?", (book_id, kind))
    return jloads(row["payload"], default) if row else default


def setting_get(key: str, default=None):
    row = query_one("SELECT v FROM kv WHERE k=?", (key,))
    return jloads(row["v"], default) if row else default


def setting_set(key: str, value: Any) -> None:
    execute("INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)", (key, jdumps(value)))


init_db()
