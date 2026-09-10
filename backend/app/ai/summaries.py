"""抽取式章节摘要、前情提要、人物档案文本。"""
from __future__ import annotations

from .nlp import norm, split_sentences, extract_quotes

# 摘要打分关键词
SUMMARY_CUES = set(
    "打死杀打伤砍刺逃走奔来去到抢偷骗抓捉押判斩枪毙救婚嫁娶许诺给送买卖发现决定 "
    "宣布革命造反剪辫磕头跪骂哭喊吵闹聚散认赔赢输发财中举落榜投梦见终于最后结果 "
    "于是然后因此原来竟然没想到不料谁知忽然突然知道告诉吩咐答应拒绝同意".split()
)


def score_sentence(s: str, present: list[str], idx: int, total: int) -> float:
    score = 0.0
    score += sum(1.5 for _ in present)
    score += sum(1.2 for w in SUMMARY_CUES if w in s)
    if 10 <= len(s) <= 70:
        score += 2
    if any(t in s for t in ("原来", "终于", "没想到", "不料", "谁知", "结果", "最后", "决定", "宣布")):
        score += 3
    if "”" in s or "“" in s:
        score += 0.5
    if idx == 0:
        score += 1
    if idx >= total - 2:
        score += 1.2
    return score


def summarize_chapter(chapter, present_names=None, max_sentences: int = 3):
    """抽取式摘要：返回 (摘要文本, 关键句[{sent,para}])。"""
    present_names = present_names or []
    scored = []
    for pi, p0 in enumerate(chapter.paragraphs):
        p = norm(p0)
        sents = split_sentences(p)
        for si, s in enumerate(sents):
            sc = score_sentence(s, present_names, pi, len(chapter.paragraphs))
            if sc >= 4:
                scored.append((sc, pi, si, s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    picked: list[tuple] = []
    seen = set()
    for sc, pi, si, s in scored:
        key = s[:12]
        if key in seen:
            continue
        seen.add(key)
        picked.append((pi, si, s))
        if len(picked) >= max_sentences:
            break
    picked.sort(key=lambda x: (x[0], x[1]))
    highlights = [{"para": pi, "sent_idx": si, "text": s} for pi, si, s in picked]
    summary = "".join(_clip(s, 72) for _, _, s in picked)
    return summary, highlights


def _clip(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[:n].rstrip("，、；：") + "……"


def golden_sentences(chapter, limit: int = 4) -> list[dict]:
    """金句候选：短而工整、带判断/感叹/引语气质的句子。"""
    out = []
    for pi, p0 in enumerate(chapter.paragraphs):
        p = norm(p0)
        for s in split_sentences(p):
            if 8 <= len(s) <= 38 and (
                ("，" in s or "；" in s or "？" in s or "！" in s)
                or any(w in s for w in ("才是", "便是", "不过", "其实", "原来", "所谓"))
            ):
                if any(x in s for x in ("阿Q",)) or True:
                    out.append({"para": pi, "text": s})
            if len(out) >= limit * 3:
                break
    return out[:limit]


def build_recap(structure: dict, chapter_summaries: list[dict], upto_chapter: int,
                book_title: str = "") -> dict:
    """前情提要：读到 upto_chapter（含）为止。"""
    upto = max(0, min(upto_chapter, len(chapter_summaries) - 1))
    recaps = []
    for cs in chapter_summaries[: upto + 1]:
        if cs.get("summary"):
            recaps.append({"chapter": cs["chapter"], "title": cs.get("title", ""),
                           "summary": cs["summary"]})
    # 近三章活跃人物
    recent_chars: dict[str, int] = {}
    for ev in structure["timeline"]:
        if upto - 3 <= ev["chapter"] <= upto:
            for c in ev.get("chars", []):
                recent_chars[c] = recent_chars.get(c, 0) + 1
    active = [c for c, _ in sorted(recent_chars.items(), key=lambda x: -x[1])][:8]
    open_threads = [
        {"chapter": f["plant"]["chapter"], "text": f["plant"]["text"], "keyword": f["keyword"]}
        for f in structure.get("foreshadows", []) if f["status"] == "planted"
        and f["plant"]["chapter"] <= upto
    ][:4]
    text = _recap_text(recaps, active, open_threads)
    return {"upto_chapter": upto, "items": recaps, "active_characters": active,
            "open_threads": open_threads, "text": text}


def _recap_text(recaps, active, threads) -> str:
    parts = ["【前情提要】"]
    for r in recaps[-5:]:
        parts.append(f"· {r['title']}：{r['summary']}")
    if active:
        parts.append("近期活跃人物：" + "、".join(active))
    if threads:
        parts.append("尚未回收的伏笔：" + "；".join(
            f"第{t['chapter']+1}章「{t['text'][:18]}……」" for t in threads[:3]))
    return "\n".join(parts)


def character_profile(character: dict, chapter_titles: list[str]) -> str:
    """生成人物档案的自然语言版本。"""
    name = character["name"]
    first = character["first_chapter"]
    role_cn = {"protagonist": "主角", "supporting": "重要配角", "minor": "次要人物"}[
        character["role"]]
    lines = [
        f"{name}，{role_cn}，首次登场于第{first+1}章《{chapter_titles[first]}》。",
        f"截至目前，全书提及 {character['mentions']} 次，开口说话 {character['quote_count']} 次，"
        f"活跃于第 {min(character['chapters'])+1}–{max(character['chapters'])+1} 章。",
    ]
    if character.get("titles"):
        lines.append(f"称呼/头衔：{'、'.join(character['titles'])}。")
    if character.get("aliases"):
        lines.append(f"别名：{'、'.join(character['aliases'][:6])}。")
    if character.get("traits"):
        lines.append(f"性格侧写（依据相关情节推断）：{'、'.join(character['traits'])}。")
    rels = [r for r in character.get("relations", []) if r["label"] != "交集"][:4]
    if rels:
        lines.append("人物关系：" + "；".join(
            f"与{r['target']}—{r['label']}" for r in rels) + "。")
    events = character.get("key_events", [])[:3]
    if events:
        lines.append("关键事件：" + "；".join(
            f"第{e['chapter']+1}章 {e['summary'][:24]}" for e in events) + "。")
    if character.get("sample_quotes"):
        lines.append("代表台词：“" + "”“".join(character["sample_quotes"][:2]) + "”。")
    return "\n".join(lines)
