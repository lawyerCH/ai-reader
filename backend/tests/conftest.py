"""测试夹具：独立的临时数据库 + TestClient + 演示书。"""
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def tmp_data():
    d = tempfile.mkdtemp(prefix="ai-reader-test-")
    os.environ["AIREADER_DATA"] = d
    os.environ["AIREADER_NO_SEED"] = "1"
    # 在导入 app 前重定向数据目录
    from app import config
    config.DATA_DIR = Path(d)
    config.BOOK_FILES = Path(d) / "books"
    config.BOOK_FILES.mkdir(parents=True, exist_ok=True)
    import app.db as db
    db.DATA = d
    db.DB_PATH = Path(d) / "test.db"
    db.CONN = db.sqlite3.connect(str(db.DB_PATH), check_same_thread=False)
    db.CONN.row_factory = db.sqlite3.Row
    db.init_db()
    yield d


SAMPLE_WUXIA = """# 剑落西风

佚名

## 第一章 山门惊变

　　青云山下着小雨，黄昏时分，林秋白在山门外捡到一个婴儿。
　　“这孩子骨相清奇，是练武的料。”玄铁掌门说。
　　突然，黑衣人从屋顶跃下，一掌击向掌门！林秋白大惊失色。
　　玄铁掌门像一尊铁塔般挡住来人，沉声道：“魔教妖人，休得猖狂。”
　　林秋白心想，这一夜之后，山门再也回不到从前了。

## 第二章 崖下奇遇

　　三个月后，林秋白被推下断魂崖。不料崖底竟是一处古洞。
　　洞里有一部残剑秘籍，他大喜过望，开始日夜修炼。
　　“等我练成，一定要回去讨个公道。”林秋白自言自语。
　　没人知道，崖顶的黑衣人正盯着他的行踪，原来此人正是内奸。

## 第三章 一剑封喉

　　三年后，林秋白重回山门。仇人相见，分外眼红。
　　最后关头，他一剑刺出，黑衣人倒地求饶。
　　玄铁掌门叹道：“江湖恩怨，终有了结之日。”
　　夕阳照在山门的石阶上，像铺了一层血。
"""


@pytest.fixture
def client(tmp_data):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    return c


@pytest.fixture
def sample_book(client):
    r = client.post("/api/books/import/text", json={
        "filename": "剑落西风.txt",
        "text": SAMPLE_WUXIA,
        "title": "剑落西风",
        "author": "测试作者",
    })
    bid = r.json()["created"][0]
    # 等待后台分析线程完成
    import time
    from app.services import books as bs
    for _ in range(60):
        st = bs.analyze_status(bid)
        if st["status"] in ("analyzed", "ready", "error"):
            break
        time.sleep(0.25)
    assert bs.analyze_status(bid)["status"] == "analyzed", bs.analyze_status(bid)
    return bid
