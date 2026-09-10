"""全书结构分析：人物档案、关系、时间线、地点、设定、伏笔。"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from . import lexicons as L
from .nlp import (
    CN, CN_CHAR, norm, split_sentences, extract_character_mentions, bigrams,
)

# 事件关键动作词
ACTION_CUES = set("打死杀打伤砍刺逃走奔来去到抢偷骗抓捉押判斩枪毙救婚嫁娶许诺给送买卖发现决定"
                  "宣布革命造反剪辫磕头跪骂哭喊吵闹聚散认赔赢输发财中举落榜投梦见")
EVENT_TIME_CUES = L.TIME_MARKERS

LOC_SUFFIXES = sorted((s for s in set(L.LOCATION_SUFFIX) if s not in ("原", "漠", "滩")),
                      key=len, reverse=True)
LOC_BUILDING_SUFFIX = {"祠", "庵", "寺", "庙", "观", "府", "殿", "阁", "堂", "楼",
                       "馆", "厅", "酒楼", "客栈", "茶馆", "书院", "宅院"}
HIGH_CONF_LOC = set("崖峰谷洞寨堡岛峡陵渡塔祠宫殿阁")
LOC_BOUND_BEFORE = set("，。、；：？！…—（）《》“”‘’「」『』 的之在去到从往来进出回过到往朝向沿经过了到上下去有个这那是和与管住处")
LOC_BOUND_AFTER = set("，。、；：？！…—（）《》“”‘’「」『』 的了着过在去到从往来进出回过向朝沿和与及是有，们里中门前上下去做当")
ORG_SUFFIXES_CLEAN = [s for s in sorted(set(L.ORG_SUFFIX), key=len, reverse=True)
                      if s not in ("门", "营", "朝", "国", "族")]
CULT_SUFFIXES_CLEAN = ["神功", "心法", "秘籍", "真经", "剑诀", "掌法", "拳法",
                       "功法", "法术", "阵法", "秘术", "内功", "口诀", "功", "诀", "丹"]


def _suffix_scan(text: str, suffixes: list[str], max_lead: int = 3,
                 loose: set[str] | None = None) -> Counter:
    """边界感知地扫描 'CN{1,max_lead}+后缀'，要求后缀后是边界字（建筑类后缀放宽）。"""
    loose = loose or set()
    out: Counter = Counter()
    for suf in suffixes:
        start = 0
        while True:
            i = text.find(suf, start)
            if i < 0:
                break
            start = i + len(suf)
            after = text[start:start + 1]
            if after and after not in LOC_BOUND_AFTER and suf not in loose:
                continue
            j = i
            lead = 0
            while j > 0 and lead < max_lead:
                c = text[j - 1]
                if not re.fullmatch(CN, c) or c in LOC_BOUND_BEFORE:
                    break
                j -= 1
                lead += 1
            if lead == 0:
                continue
            term = text[j:i + len(suf)]
            while term and term[0] in "有个这那到去往从在上下出进了是和与管住多":
                term = term[1:]
            if len(term) >= 2:
                out[term] += 1
    return out
CONCEPT_TAIL = ("制度", "规矩", "法子", "传统", "主义", "说法", "忌讳", "风俗",
                "办法", "习惯", "礼节", "名义", "大法")
BOOK_TITLE_RE = re.compile(r"《([^》]{2,12})》")
STOP_LOC = set("这个 那个 一个 两个 镇上人 村里人 城里人 山门 大山 小山 下山 上山 进城 "
               "城门 街前街后".split())


def _canonical_maps(aliases: dict[str, set[str]]):
    """alias 成员 -> 主名；主名 -> set（含自己）。"""
    member_to_main: dict[str, str] = {}
    for main, group in aliases.items():
        for m in group:
            member_to_main[m] = main
    return member_to_main


def analyze_structure(book) -> dict:
    """book: ParsedBook。"""
    chapters = book.chapters
    ch_texts = [c.paragraphs for c in chapters]
    mentions, aliases, quotes = extract_character_mentions(ch_texts)
    to_main = _canonical_maps(aliases)

    # ---------- 人物聚合 ----------
    agg: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "chapters": Counter(), "first": (10**9, 10**9),
        "titles": Counter(), "aliases": set(), "quotes": 0, "quote_texts": [],
        "co": Counter(), "speakers_to": Counter(),
    })

    def canon(name: str) -> str:
        return to_main.get(name, name)

    def touch(name: str, ch: int, pi: int):
        m = canon(name)
        a = agg[m]
        a["count"] += 1
        a["chapters"][ch] += 1
        if (ch, pi) < a["first"]:
            a["first"] = (ch, pi)
        return m

    for name, rec in mentions.items():
        main = touch(name, *rec["first"])
        agg[main]["aliases"].add(name)
        for ch in rec["chapters"]:
            agg[main]["chapters"][ch] += 0  # 确保章节键存在
        for t in rec["titles"]:
            agg[main]["titles"][t] += 1
        # 频次按归并后重算（下方全文扫描更准，这里先记录 quotes）
        agg[main]["quotes"] += rec["quotes"]

    # ---------- 全文统一扫描：频次/共现/对白/关系/地点/概念 ----------
    relation_evidence: dict[tuple[str, str], Counter] = defaultdict(Counter)
    loc_counter: Counter = Counter()
    loc_first: dict[str, int] = {}
    loc_sent: dict[str, str] = {}
    org_counter: Counter = Counter()
    cult_counter: Counter = Counter()
    concept_counter: Counter = Counter()
    definition_sent: dict[str, str] = {}
    book_titles: Counter = Counter()
    emotion_by_char: dict[str, Counter] = defaultdict(Counter)
    trait_by_char: dict[str, Counter] = defaultdict(Counter)
    char_events: dict[str, list[dict]] = defaultdict(list)
    time_events: list[dict] = []

    all_names = list(agg.keys())
    name_by_len = sorted(all_names, key=len, reverse=True)
    name_re = re.compile("|".join(re.escape(n) for n in name_by_len)) if name_by_len else None

    def record_def(term: str, sent: str):
        if term not in definition_sent and 6 <= len(sent) <= 90:
            definition_sent[term] = sent

    for ci, ch in enumerate(chapters):
        for pi, para in enumerate(ch.paragraphs):
            p = norm(para)
            present = sorted({canon(m.group(0)) for m in name_re.finditer(p)} ) if name_re else []
            for a in present:
                agg[a]["count"] += 1
                agg[a]["chapters"][ci] += 1
                if (ci, pi) < agg[a]["first"]:
                    agg[a]["first"] = (ci, pi)
            for i, a in enumerate(present):
                for b in present[i + 1:]:
                    agg[a]["co"][b] += 1
                    agg[b]["co"][a] += 1
            # 关系词证据（模板判定，避免同句误伤）
            for sent in split_sentences(p):
                hit_names = sorted({canon(m.group(0)) for m in name_re.finditer(sent)}) if name_re else []
                for i, a in enumerate(hit_names):
                    for b in hit_names[i + 1:]:
                        _label_relation(sent, a, b, relation_evidence)
                # 情绪/性格
                for n in hit_names:
                    for emo, words in L.EMOTIONS.items():
                        if any(w in sent for w in words):
                            emotion_by_char[n][emo] += 1
                    for trait, words in L.TRAIT_CUES.items():
                        if any(w in sent for w in words):
                            trait_by_char[n][trait] += 1
            # 地点 / 组织 / 功法（边界感知扫描）
            for loc, n in _suffix_scan(p, LOC_SUFFIXES, max_lead=3,
                                       loose=LOC_BUILDING_SUFFIX).items():
                if loc in STOP_LOC or len(loc) < 2:
                    continue
                loc_counter[loc] += n
                loc_first.setdefault(loc, ci)
                if loc not in loc_sent:
                    for sent in split_sentences(p):
                        if loc in sent:
                            loc_sent[loc] = sent[:80]
                            break
            org_counter.update(_suffix_scan(p, ORG_SUFFIXES_CLEAN, max_lead=3))
            cult_counter.update(_suffix_scan(p, CULT_SUFFIXES_CLEAN[:13], max_lead=4))
            cult_counter.update(_suffix_scan(p, CULT_SUFFIXES_CLEAN[13:], max_lead=3))
            for tail in CONCEPT_TAIL:
                for m in re.finditer(rf"{CN}{{2,5}}{tail}", p):
                    after = p[m.end():m.end() + 1]
                    if after and after not in LOC_BOUND_AFTER:
                        continue
                    term = m.group(0)
                    while term and term[0] in "的了是这那有和与":
                        term = term[1:]
                    if len(term) < len(tail) + 2:
                        continue
                    concept_counter[term] += 1
                    record_def(term, next((s for s in split_sentences(p) if term in s), p)[:80])
            for m in BOOK_TITLE_RE.finditer(p):
                book_titles[m.group(1)] += 1
            # 时间线事件
            if any(t in p for t in EVENT_TIME_CUES):
                sents = split_sentences(p)
                cue_sents = [s for s in sents if any(t in s for t in EVENT_TIME_CUES)
                             and any(c in s for c in ACTION_CUES)]
                for s in cue_sents[:1]:
                    time_events.append({
                        "chapter": ci, "para": pi,
                        "time": next((t for t in EVENT_TIME_CUES if t in s), ""),
                        "summary": _clip(s, 70),
                        "chars": present[:5],
                        "raw": s,
                    })

    # 对白归属：统计说话对象
    for q in quotes:
        if not q["speaker"] or not q["is_dialogue"]:
            continue
        sp = canon(q["speaker"])
        if sp not in agg:
            continue
        agg[sp]["quotes"] += 1
        if len(agg[sp]["quote_texts"]) < 6:
            agg[sp]["quote_texts"].append(q["text"])
        para = ch_texts[q["ch"]][q["para"]]
        listeners = {canon(m.group(0)) for m in name_re.finditer(para)} - {sp}
        for l in listeners:
            agg[sp]["speakers_to"][l] += 1
            relation_evidence[tuple(sorted((sp, l)))]  # 确保有键

    # ---------- 时间线：每章压缩为 1-3 个代表事件 ----------
    timeline = _build_timeline(chapters, name_re, canon)

    # ---------- 伏笔 ----------
    foreshadows = _detect_foreshadows(chapters, name_re, canon)

    # ---------- 人物档案 ----------
    characters = []
    max_count = max((a["count"] for a in agg.values()), default=1)
    # 主角只取全书提及最高者
    hero_name = max(agg.items(), key=lambda kv: kv[1]["count"])[0] if agg else None
    for name, a in agg.items():
        chs = sorted(c for c, n in a["chapters"].items() if n > 0) or [a["first"][0]]
        titles = [t for t, _ in a["titles"].most_common(2)]
        traits = [t for t, _ in trait_by_char[name].most_common(3)]
        emotions = {e: n for e, n in emotion_by_char[name].most_common(4)}
        importance = a["count"] / max_count
        if name == hero_name:
            role = "protagonist"
        elif importance > 0.12 or a["quotes"] >= 2:
            role = "supporting"
        else:
            role = "minor"
        rels = []
        for other, w in a["co"].most_common(8):
            labels = relation_evidence.get(tuple(sorted((name, other))))
            label = _best_label(labels)
            rels.append({"target": other, "weight": w, "label": label})
        events = [e for e in timeline if name in e["chars"]][:5]
        characters.append({
            "name": name,
            "aliases": sorted(a["aliases"] - {name}),
            "titles": titles,
            "role": role,
            "mentions": a["count"],
            "quote_count": a["quotes"],
            "first_chapter": min(chs),
            "chapters": chs,
            "traits": traits,
            "emotions": emotions,
            "relations": rels,
            "key_events": events,
            "sample_quotes": a["quote_texts"][:3],
            "importance": round(importance, 3),
        })
    characters.sort(key=lambda c: -c["mentions"])
    char_names = {c["name"] for c in characters}
    # 关系边（无向，带标签），剔除已被过滤的假人名
    for c in characters:
        c["relations"] = [r for r in c["relations"] if r["target"] in char_names][:8]
    edge_map: dict[tuple[str, str], dict] = {}
    for c in characters:
        for r in c["relations"]:
            key = tuple(sorted((c["name"], r["target"])))
            w = r["weight"]
            if key in edge_map:
                edge_map[key]["weight"] = max(edge_map[key]["weight"], w)
                if edge_map[key]["label"] == "交集" and r["label"] != "交集":
                    edge_map[key]["label"] = r["label"]
            else:
                edge_map[key] = {"source": key[0], "target": key[1],
                                 "weight": w, "label": r["label"],
                                 "chapter": _edge_chapter(characters, key)}
    relations = sorted(edge_map.values(), key=lambda e: -e["weight"])[:60]

    # ---------- 地点 ----------
    locations = []
    loc_stop = {"翰林", "一般都", "难关", "天下", "山下", "山上", "地上", "堂上"}
    for loc, cnt in loc_counter.most_common(40):
        if loc in loc_stop or loc in char_names:
            continue
        high_conf = len(loc) >= 3 and loc[-1] in HIGH_CONF_LOC
        if cnt < 2 and not high_conf:
            continue
        locations.append({
            "name": loc, "mentions": cnt,
            "first_chapter": loc_first[loc],
            "chapters": sorted({c for c, ch in enumerate(chapters) if loc in norm(ch.title) or any(loc in p for p in ch.paragraphs)}),
            "desc": loc_sent.get(loc, ""),
        })

    # ---------- 设定百科 ----------
    def _junk_setting(t: str) -> bool:
        return (t[0] in "的了是这那有和与一不也又都很最"
                or any(x in t for x in ("已经", "然而", "于是", "这个", "那个", "什么",
                                        "我们", "你们", "他们", "一个", "没有", "不是")))

    settings = []
    for term, cnt in (cult_counter + org_counter + concept_counter + book_titles).most_common(60):
        kind = "功法武学" if term in cult_counter else (
            "组织势力" if term in org_counter else ("文献典故" if term in book_titles else "社会概念"))
        if term not in book_titles and (cnt < 2 or _junk_setting(term)):
            continue
        if kind in ("功法武学", "组织势力") and _junk_setting(term):
            continue
        settings.append({
            "term": term, "type": kind, "mentions": cnt,
            "first_chapter": next((i for i, ch in enumerate(chapters)
                                   if term in norm(ch.title) or any(term in p for p in ch.paragraphs)), 0),
            "summary": definition_sent.get(term, ""),
        })

    return {
        "characters": characters,
        "relations": relations,
        "timeline": timeline,
        "locations": locations,
        "settings": settings,
        "foreshadows": foreshadows,
        "raw_quotes": quotes,
        "canonical": to_main,
    }


LABEL_PRIORITY = ["父亲", "母亲", "儿子", "女儿", "妻子", "丈夫", "师父", "徒弟",
                  "兄长", "姐姐", "弟弟", "妹妹", "主仆", "同门", "爱慕", "仇敌",
                  "朋友", "冲突"]


def _best_label(labels: Counter | None) -> str:
    if not labels:
        return "交集"
    for lab in LABEL_PRIORITY:
        if labels.get(lab):
            return lab
    return labels.most_common(1)[0][0] if labels else "交集"


CONFLICT_WORDS = ["打", "骂", "揍", "踢", "杀", "抓", "捉", "赶", "恨", "欺", "扇",
                  "啐", "挖苦", "瞧不起", "嘲笑", "打嘴", "斥", "撞", "抢", "骗", "揍了"]
LOVE_WORDS = ["喜欢", "爱上", "爱慕", "暗恋", "求爱", "调戏", "钟情", "相思", "心动",
              "动情", "野合", "勾引", "勾搭", "相好", "思慕", "娶", "嫁", "困觉",
              "说亲", "求亲", "恋爱", "情人", "姘"]
FRIEND_WORDS = ["朋友", "好友", "知己", "故交", "结拜", "师兄弟", "同门"]


def _label_relation(sent: str, a: str, b: str, evidence):
    key = tuple(sorted((a, b)))
    # 亲属/师徒模板：A是B的父亲、A的父亲是B、A父亲B……
    for label, words in L.RELATION_PATTERNS:
        for w in words:
            if re.search(rf"{re.escape(a)}是{re.escape(b)}的{w}", sent):
                evidence[key][label] += 2
            elif re.search(rf"{re.escape(b)}是{re.escape(a)}的{w}", sent):
                evidence[key][label] += 2
            elif re.search(rf"{re.escape(a)}的{w}[^。；！？]{{0,8}}?{re.escape(b)}", sent):
                evidence[key][label] += 2
            elif re.search(rf"{re.escape(b)}的{w}[^。；！？]{{0,8}}?{re.escape(a)}", sent):
                evidence[key][label] += 2
            elif re.search(rf"{re.escape(a)}[与和]{re.escape(b)}[^\n。]{{0,6}}{w}", sent) \
                    or re.search(rf"{re.escape(b)}[与和]{re.escape(a)}[^\n。]{{0,6}}{w}", sent):
                evidence[key][label] += 1
    if any(w in sent for w in CONFLICT_WORDS):
        evidence[key]["冲突"] += 1
    if any(w in sent for w in LOVE_WORDS):
        evidence[key]["爱慕"] += 1
    if any(w in sent for w in FRIEND_WORDS):
        evidence[key]["朋友"] += 1


def _edge_chapter(characters, key):
    idx = {c["name"]: c for c in characters}
    chs = []
    for n in key:
        c = idx.get(n)
        if c:
            chs.append(c["first_chapter"])
    return min(chs) if chs else 0


def _clip(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[:n].rstrip("，、；：") + "……"


def _event_score(s: str, present: list[str]) -> int:
    score = len(present) * 2
    score += sum(3 for c in ACTION_CUES if c in s)
    if any(t in s for t in EVENT_TIME_CUES):
        score += 4
    if 12 <= len(s) <= 60:
        score += 2
    if "“" in s or "”" in s:
        score += 1
    return score


def _build_timeline(chapters, name_re, canon):
    timeline = []
    for ci, ch in enumerate(chapters):
        scored: list[tuple[int, str, list[str], int]] = []
        for pi, p0 in enumerate(ch.paragraphs):
            p = norm(p0)
            present = sorted({canon(m.group(0)) for m in name_re.finditer(p)}) if name_re else []
            for s in split_sentences(p):
                sc = _event_score(s, present)
                if any(t in s for t in EVENT_TIME_CUES):
                    sc += 3
                if sc >= 7:
                    scored.append((sc, s, present, pi))
        scored.sort(key=lambda x: -x[0])
        chosen, seen_sents = [], set()
        for sc, s, present, pi in scored:
            key = s[:14]
            if key in seen_sents:
                continue
            seen_sents.add(key)
            chosen.append({
                "chapter": ci, "para": pi,
                "time": next((t for t in EVENT_TIME_CUES if t in s), ch.title),
                "title": ch.title,
                "summary": _clip(s, 64),
                "chars": present[:5],
            })
            if len(chosen) >= 3:
                break
        if not chosen:
            # 兜底：取章内首段含人名的句子
            for pi, p0 in enumerate(ch.paragraphs[:6]):
                p = norm(p0)
                present = sorted({canon(m.group(0)) for m in name_re.finditer(p)}) if name_re else []
                if present:
                    s = split_sentences(p)[0]
                    chosen.append({"chapter": ci, "para": pi, "time": ch.title,
                                   "title": ch.title, "summary": _clip(s, 64),
                                   "chars": present[:5]})
                    break
        timeline.extend(chosen)
    return timeline


def _detect_foreshadows(chapters, name_re, canon):
    plants: list[dict] = []
    payoffs: list[dict] = []
    for ci, ch in enumerate(chapters):
        for pi, p0 in enumerate(ch.paragraphs):
            p = norm(p0)
            for si, s in enumerate(split_sentences(p)):
                cue_hits = [c for c in L.PLANT_CUES if c in s]
                if cue_hits and len(s) >= 12:
                    words = set(bigrams(s))
                    plants.append({"chapter": ci, "para": pi, "text": _clip(s, 80),
                                   "cue": cue_hits[0], "words": words})
                pay_hits = [c for c in L.PAYOFF_CUES if c in s]
                if pay_hits and ci > 0 and len(s) >= 10:
                    words = set(bigrams(s))
                    payoffs.append({"chapter": ci, "para": pi, "text": _clip(s, 80),
                                    "cue": pay_hits[0], "words": words})
    pairs, used_plants, used_payoffs = [], set(), set()
    for pf in plants:
        best, best_overlap = None, 0
        for k, po in enumerate(payoffs):
            if k in used_payoffs or po["chapter"] <= pf["chapter"]:
                continue
            overlap = len(pf["words"] & po["words"])
            ratio = overlap / max(1, min(len(pf["words"]), len(po["words"])))
            score = overlap + ratio * 3
            if score > best_overlap:
                best, best_overlap = k, score
        if best is not None and best_overlap >= 4.2:
            used_plants.add(id(pf))
            used_payoffs.add(best)
            po = payoffs[best]
            pairs.append({
                "status": "resolved",
                "plant": {"chapter": pf["chapter"], "para": pf["para"], "text": pf["text"]},
                "payoff": {"chapter": po["chapter"], "para": po["para"], "text": po["text"]},
                "keyword": "、".join(sorted(pf["words"] & po["words"])[:3]),
            })
    # 未回收的伏笔
    unresolved = []
    for pf in plants:
        if id(pf) not in used_plants and pf["cue"] in (
                "谁也没有想到", "谁也没料到", "他不知道", "她不知道", "没有人知道",
                "嘱咐", "来历不明", "身份不明", "不祥", "神秘", "埋下", "藏"):
            unresolved.append({
                "status": "planted",
                "plant": {"chapter": pf["chapter"], "para": pf["para"], "text": pf["text"]},
                "payoff": None, "keyword": pf["cue"],
            })
    return pairs + unresolved[:20]
