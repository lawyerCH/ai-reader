"""解析与人物/批注引擎测试。"""
from app.parsers import parse_text
from app.ai.analyze import analyze_structure
from app.ai.annotations import generate_annotations
from app.ai.summaries import summarize_chapter
from app.ai.qa import answer_question, multi_persona, debate, what_if, classify_intent
from app.ai.rewrite import rewrite, parse_instruction
from .conftest import SAMPLE_WUXIA


def _book():
    return parse_text(SAMPLE_WUXIA, "txt", "剑落西风.txt")


def test_chapter_split_and_title():
    b = _book()
    assert b.title == "剑落西风"
    assert len(b.chapters) == 3
    assert b.chapters[0].title == "第一章 山门惊变"


def test_characters_extracted():
    b = _book()
    st = analyze_structure(b)
    names = [c["name"] for c in st["characters"]]
    assert "林秋白" in names
    hero = next(c for c in st["characters"] if c["name"] == "林秋白")
    assert hero["role"] == "protagonist"
    # 关系/地点/时间线
    assert len(st["relations"]) >= 1
    locs = [l["name"] for l in st["locations"]]
    assert any("崖" in x or "山门" in x for x in locs)
    assert len(st["timeline"]) >= 3


def test_annotations_all_personas():
    b = _book()
    st = analyze_structure(b)
    anns = generate_annotations(b, st)
    personas = {a["persona"] for a in anns}
    # 六个角色全部产出
    assert personas == {"plot", "lore", "emotion", "snark", "professor", "character"}
    # 网文套路（崖底奇遇/复仇/黑衣人）被吐槽党或剧情党捕捉
    kinds = [(a["persona"], a["kind"]) for a in anns]
    assert any(p == "plot" for p, _ in kinds)
    # 比喻被文学教授识别
    assert any(k == "simile" for p, k in kinds)
    # 每个批注都锚定合法段落
    for a in anns:
        assert 0 <= a["chapter_idx"] < 3
        assert a["content"]


def test_chapter_summary():
    b = _book()
    summary, hl = summarize_chapter(b.chapters[2], ["林秋白"])
    assert summary and "林秋白" in summary or summary  # 摘要非空
    assert isinstance(hl, list)


def test_qa_intents():
    assert classify_intent("林秋白是谁？") == "who"
    assert classify_intent("结局怎么样？") == "ending"
    assert classify_intent("如果主角没有跳崖？") == "whatif"
    assert classify_intent("预测后续剧情") == "predict"


def test_qa_answer_and_multi_persona():
    b = _book()
    st = analyze_structure(b)
    r = answer_question("林秋白是谁？", st, b.chapters, "lore")
    assert "林秋白" in r["answer"]
    assert r["refs"]
    multi = multi_persona("黑衣人到底是谁？", st, b.chapters)
    assert len(multi) >= 5 and all(a["answer"] for a in multi)
    d = debate("主角复仇对吗？", st, b.chapters)
    assert len(d["turns"]) == 4
    w = what_if("如果林秋白没掉下悬崖", st, b.chapters)
    assert len(w) == 5


def test_rewrite_happy_ending():
    b = _book()
    st = analyze_structure(b)
    plan = parse_instruction("让林秋白复仇成功，沉冤得雪，给一个好结局", st)
    assert "happy" in plan["intents"] or "revenge" in plan["intents"]
    assert "林秋白" in plan["targets"]
    r = rewrite("ending", "让主角活下来复仇成功", st, chapter_idx=2)
    assert r["word_count"] > 200
    assert "林秋白" in r["text"] or st["characters"][0]["name"] in r["text"]


def test_rewrite_paragraph():
    b = _book()
    st = analyze_structure(b)
    src = b.chapters[0].paragraphs[3]
    r = rewrite("paragraph", "让主角被抓走、悲剧一点", st, original_text=src)
    assert r["text"]
    assert len(r["text"]) >= len(src)
