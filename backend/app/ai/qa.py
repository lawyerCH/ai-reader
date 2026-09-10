"""全书问答、多角色回答、辩论与剧情预测（本地检索式，零模型依赖）。"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from .nlp import norm, split_sentences, bigrams
from .summaries import character_profile


class BM25:
    def __init__(self, docs: list[dict], k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tokens = [bigrams(d["text"]) for d in docs]
        self.dl = [len(t) for t in self.tokens]
        self.avgdl = max(1, sum(self.dl) / len(self.dl))
        self.df: Counter = Counter()
        for toks in self.tokens:
            for t in set(toks):
                self.df[t] += 1
        self.N = len(docs)

    def search(self, query: str, topk: int = 6, chapter_set=None):
        qtoks = bigrams(query)
        scores = []
        for i, toks in enumerate(self.tokens):
            if chapter_set is not None and self.docs[i]["ch"] not in chapter_set:
                continue
            if not toks:
                continue
            tf = Counter(toks)
            score = 0.0
            for q in qtoks:
                if q not in tf or q not in self.df:
                    continue
                idf = math.log(1 + (self.N - self.df[q] + 0.5) / (self.df[q] + 0.5))
                score += idf * (tf[q] * (self.k1 + 1)) / (
                    tf[q] + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl))
            if score > 0:
                scores.append((score, i))
        scores.sort(reverse=True)
        return [self.docs[i] for _, i in scores[:topk]]


def build_index(chapters) -> BM25:
    docs = []
    for ci, ch in enumerate(chapters):
        for pi, p in enumerate(ch.paragraphs):
            docs.append({"ch": ci, "para": pi, "text": norm(p),
                         "title": ch.title})
        docs.append({"ch": ci, "para": -1, "text": norm(ch.title), "title": ch.title})
    return BM25(docs)


def classify_intent(q: str) -> str:
    if re.search(r"如果|假如|要是|倘若|假设", q):
        return "whatif"
    if re.search(r"结局|最后怎样|结局是|下场|会死|结局如何", q):
        return "ending"
    if re.search(r"预测|后来会|接下来会|会怎样|会发生|后面怎么", q):
        return "predict"
    if re.search(r"是谁|什么人|哪个人", q):
        return "who"
    if re.search(r"关系|什么关系", q):
        return "relation"
    if re.search(r"哪里|什么地方|在哪|地点", q):
        return "where"
    if re.search(r"为什么|为何|怎么回事|什么意思|啥意思|讲了什么", q):
        return "explain"
    if re.search(r"写得|手法|修辞|文风|写作", q):
        return "literary"
    return "general"


def find_entities(q: str, structure: dict):
    chars = []
    for c in structure["characters"]:
        names = [c["name"]] + c.get("aliases", [])
        if any(n and n in q for n in names):
            chars.append(c["name"])
    locs = [l["name"] for l in structure.get("locations", []) if l["name"] in q]
    sets = [s["term"] for s in structure.get("settings", []) if s["term"] in q]
    return chars[:4], locs[:3], sets[:3]


PERSONA_VOICE = {
    "plot": {
        "prefix": "从剧情结构看，",
        "general": "结合伏笔和走向来看：{answer} 这条线在结构上是有迹可循的，留意前后呼应。",
        "predict": "按这本书目前埋的线索，我押这三种走向之一：{guesses}",
    },
    "lore": {
        "prefix": "考据角度说，",
        "general": "查证了一下原文与设定：{answer} 这点在书内是自洽的，背景信息见下。",
    },
    "emotion": {
        "prefix": "从人物心理看，",
        "general": "重点不在事情本身，而在人物的情绪逻辑：{answer}",
    },
    "snark": {
        "prefix": "我就直说了——",
        "general": "讲真：{answer} 这操作，搁评论区是要被截图的。",
        "predict": "别的不敢说，flag 已经立好了：{guesses} 到时候别说是乌鸦嘴。",
    },
    "professor": {
        "prefix": "从叙事学角度，",
        "general": "这一处值得细读：{answer} 注意作者选择的视角与措辞，文本的意义往往藏在这里。",
        "literary": "从写作手法看，{answer} 这是作者自觉的叙事安排，而非闲笔。",
    },
    "character": {
        "prefix": "（角色视角）",
        "general": "若由当事人开口：{answer}",
    },
}


def _evidence(index: BM25, q: str, chapter_set=None, topk=5):
    hits = index.search(q, topk=topk, chapter_set=chapter_set)
    return [{"ch": h["ch"], "para": h["para"], "title": h["title"],
             "text": (h["text"][:120] + "……") if len(h["text"]) > 120 else h["text"]}
            for h in hits]


def _character_answer(name: str, structure, chapters) -> str:
    c = next((x for x in structure["characters"] if x["name"] == name), None)
    if not c:
        return ""
    titles = [ch.title for ch in chapters]
    return character_profile(c, titles)


def _relation_answer(a: str, b: str, structure) -> str:
    for c in structure["characters"]:
        if c["name"] == a:
            for r in c.get("relations", []):
                if r["target"] == b:
                    desc = {
                        "冲突": f"{a} 与 {b} 存在正面冲突（同框多伴随打骂/对立情节），两人共现 {r['weight']} 次。",
                        "爱慕": f"{a} 对 {b} 有情欲/爱慕线索，同框 {r['weight']} 次。",
                        "朋友": f"{a} 与 {b} 是朋友/同阵营关系。",
                        "儿子": f"{b} 是 {a} 的儿子。",
                        "父亲": f"{b} 是 {a} 的父亲。",
                        "妻子": f"{b} 是 {a} 的妻子。",
                        "丈夫": f"{b} 是 {a} 的丈夫。",
                        "交集": f"全书 {a} 与 {b} 同框 {r['weight']} 次，有不少对手戏，但关系更接近日常交集。",
                    }.get(r["label"], f"{a} 与 {b} 的关系是：{r['label']}（同框 {r['weight']} 次）。")
                    return desc
    return f"书中没有明确交代 {a} 与 {b} 的固定关系，他们多在群像场景中同框。"


def _end_answer(structure, chapters, index) -> tuple[str, list]:
    n = len(chapters)
    evs = [e for e in structure["timeline"] if e["chapter"] >= n - 2]
    last_text = "；".join(e["summary"] for e in evs[-4:])
    text = (f"全书共 {n} 章，结局落在最后一章《{chapters[-1].title}》。"
            f"收尾的关键事件：{last_text}。结局没有走大团圆路线，主角的命运在示众场景中收束。")
    ev = _evidence(index, chapters[-1].title + "结局", topk=3,
                   chapter_set={n - 1})
    return text, ev


def _predict(structure, chapters, q: str) -> str:
    chars, _, _ = find_entities(q, structure)
    lead = chars[0] if chars else (structure["characters"][0]["name"]
                                   if structure["characters"] else "主角")
    open_fs = [f for f in structure.get("foreshadows", []) if f["status"] == "planted"]
    g = []
    g.append(f"围绕 {lead} 的矛盾会先以\"看似化解\"的方式反弹一次，制造短暂假象")
    if open_fs:
        g.append("此前埋下的疑点（" + "、".join(f["keyword"] for f in open_fs[:2]) + "）会被翻出来")
    g.append(f"和 {lead} 冲突最深的人会在结局前再踩一脚，完成主题闭环")
    return "；".join(g) + "。"


def answer_question(q: str, structure: dict, chapters, persona: str = "plot",
                    scope: dict | None = None) -> dict:
    """单角色回答。scope: {chapter_idx} 限定章节。"""
    q = norm(q.strip())
    index = chapters_index(chapters)
    chapter_set = None
    if scope and scope.get("chapter_idx") is not None:
        chapter_set = {scope["chapter_idx"]}
    intent = classify_intent(q)
    chars, locs, sets = find_entities(q, structure)
    refs = []
    parts = []

    if intent == "ending":
        text, refs = _end_answer(structure, chapters, index)
    elif intent in ("who",) and chars:
        text = _character_answer(chars[0], structure, chapters)
        refs = _evidence(index, chars[0], chapter_set, topk=3)
    elif intent == "relation" and len(chars) >= 2:
        text = _relation_answer(chars[0], chars[1], structure)
        refs = _evidence(index, f"{chars[0]} {chars[1]}", chapter_set, topk=4)
    elif intent == "where" and locs:
        loc = next((l for l in structure["locations"] if l["name"] == locs[0]), None)
        text = f"{locs[0]} 首次出现于第{(loc['first_chapter']+1) if loc else '?'}章。"
        if loc and loc.get("desc"):
            text += f"原文语境：{loc['desc']}"
        refs = _evidence(index, locs[0], topk=3)
    elif intent == "predict" or intent == "whatif":
        guesses = _predict(structure, chapters, q)
        voice = PERSONA_VOICE[persona]
        if intent == "whatif":
            text = f"假设成立的话，因果链会这样改写：{guesses} 这个脑洞最大的看点，是其他人物的反应会连锁改变。"
        else:
            text = voice.get("predict", PERSONA_VOICE["plot"]["predict"]).format(guesses=guesses)
        refs = _evidence(index, q, chapter_set, topk=3)
    elif intent == "literary":
        refs = _evidence(index, q, topk=5)
        body = "；".join(r["text"][:50] for r in refs[:3])
        text = PERSONA_VOICE["professor"]["general"].format(answer=body)
    else:
        refs = _evidence(index, q, chapter_set=chapter_set, topk=5)
        if refs:
            body = refs[0]["text"]
            if chars:
                body = f"关于{'、'.join(chars)}——" + body
        else:
            body = "原文中没有直接答案，以下是根据已有线索的推断。"
        if persona == "character" and chars:
            c = next((x for x in structure["characters"] if x["name"] == chars[0]), None)
            quote = (c["sample_quotes"][0] if c and c.get("sample_quotes") else "")
            text = f"【{chars[0]}的口吻】“{quote}”——这事儿我最清楚：{body}"
        else:
            voice = PERSONA_VOICE[persona]
            text = voice.get("general", PERSONA_VOICE["plot"]["general"]).format(answer=body)
        if intent == "explain" and persona == "professor":
            parts.append("补充一句：这种写法通常承担主题表达，人物的遭遇是更大社会结构的缩影。")

    if not text.startswith(PERSONA_VOICE[persona]["prefix"]) and persona not in ("character",):
        text = PERSONA_VOICE[persona]["prefix"] + text
    return {"persona": persona, "answer": text, "intent": intent,
            "entities": {"characters": chars, "locations": locs, "settings": sets},
            "refs": refs, "extra": "\n".join(parts)}


# 进程内缓存
_INDEX_CACHE: dict[int, BM25] = {}


def chapters_index(chapters) -> BM25:
    key = id(chapters)
    if key not in _INDEX_CACHE:
        _INDEX_CACHE.clear()
        _INDEX_CACHE[key] = build_index(chapters)
    return _INDEX_CACHE[key]


def multi_persona(q: str, structure, chapters, personas=None, scope=None) -> list[dict]:
    personas = personas or ["plot", "lore", "emotion", "snark", "professor"]
    return [answer_question(q, structure, chapters, p, scope) for p in personas]


DEBATE_TURNS = {
    "plot": [
        "我先立观点：情节的功能是推动主题，所以这件事即便不近人情，也是结构性的必然。证据在第{ch}章——{ev}",
        "对方只谈\"应该怎样\"，可伏笔早就给了答案：{ev}",
        "总结：作者的安排服务于整体结构，局部的不舒服正是主题需要。",
    ],
    "emotion": [
        "我同意结构论，但人物此刻的情绪才是读者真实的代入点。你看原文：{ev}",
        "一个人不会按\"结构\"行事，只会按创伤和欲望行事——这才是关键。",
        "所以评判这个选择，要先理解他为什么只能这么选。",
    ],
    "snark": [
        "我反对。不合理就是不合理，别拿结构给桥段洗白。原文这段：{ev}",
        "人物动机不够，巧合来凑——这是创作上的偷懒，不是什么必然。",
        "结论：可以写，但本吐槽君不接受洗白。",
    ],
    "professor": [
        "各位都有道理。放到叙事传统里看，这处安排属于经典的\"反讽结构\"：{ev}",
        "作者让读者同时产生同情与不适，这种间离效果是自觉的美学选择。",
        "文学不提供标准答案，它提供的是可供反复阐释的张力。",
    ],
}


def debate(topic: str, structure, chapters, side_a="plot", side_b="snark",
           scope=None) -> list[dict]:
    """两个角色围绕有争议话题自动辩论（剧情党 vs 吐槽君默认）。"""
    refs = _evidence(chapters_index(chapters), topic,
                     {scope["chapter_idx"]} if scope and scope.get("chapter_idx") is not None else None,
                     topk=4)
    evs = [r["text"] for r in refs[:3]] or [topic]
    turns = []
    order = [side_a, side_b, side_a, side_b]
    bank = {side_a: DEBATE_TURNS.get(side_a, DEBATE_TURNS["plot"]),
            side_b: DEBATE_TURNS.get(side_b, DEBATE_TURNS["snark"])}
    ia = ib = 0
    for i, who in enumerate(order):
        tpl = bank[who][min(ia if who == side_a else ib, 2)]
        ia += who == side_a
        ib += who == side_b
        ev = evs[min(i, len(evs) - 1)]
        ch = refs[min(i, len(refs) - 1)]["ch"] + 1 if refs else "?"
        turns.append({"persona": who, "content": tpl.format(ev=ev, ch=ch)})
    return {"topic": topic, "turns": turns, "refs": refs}


def what_if(hypothesis: str, structure, chapters) -> list[dict]:
    """脑洞讨论：各角色脑补\"如果……会怎样\"。"""
    chars, locs, _ = find_entities(hypothesis, structure)
    lead = chars[0] if chars else (structure["characters"][0]["name"]
                                   if structure["characters"] else "主角")
    lines = {
        "plot": f"如果\"{hypothesis}\"成立，至少三条伏笔要改道：{lead} 的核心矛盾提前解决，"
                f"后半本书的冲突将由第二顺位的对立关系顶上，结局基调整体反转。",
        "lore": f"设定层面要先问可行性：{lead} 所处的社会结构不变，单点假设会被环境拉回原位——"
                "除非连权力结构一起改，否则历史的惯性会让故事滑回原来的轨道。",
        "emotion": f"最值得写的是关系变化：{lead} 的心态会先经历不信、试探、患得患失三阶段，"
                   "相关人物之间的信任要重建，这部分反而是新故事最有戏的地方。",
        "snark": f"行，开脑洞是吧？{lead} 真要遂了愿，第一件事大概率是飘——"
                 "然后被现实用另一种姿势毒打。人物不成长，换个副本照样翻车。",
        "professor": f"这其实是经典的\"反事实叙事\"练习：改变一个变量，观察主题是否成立。"
                     f"如果改完后讽刺性消失，说明原来的情节并非随意安排，而是主题的必要条件。",
    }
    return [{"persona": p, "content": c} for p, c in lines.items()]
