"""读者分支改写引擎。

本地模式（默认）：指令解析 -> 抽取故事状态（人物/地点/矛盾）-> 模板化多幕生成，
保证实体与人设一致、情节连贯；支持段落/章节/结局/全篇范围。
配置 OpenAI 兼容 LLM 后（见 provider.py）自动升级为模型生成。
"""
from __future__ import annotations

import re
from .nlp import norm, split_sentences

HAPPY = ["happy", "he", "圆满", "好结局", "好结果", "皆大欢喜", "活下来", "活下去",
         "赢", "胜利", "成功", "得救", "救回", "团聚", "团圆", "在一起", "复合", "洗白",
         "原谅", "平反", "昭雪", "翻身", "发达", "娶", "嫁"]
TRAGIC = ["be", "悲剧", "死", "死掉", "死了", "处死", "枪毙", "杀", "灭", "毁灭",
          "孤独", "离散", "失败", "入狱", "流放", "疯", "背叛"]
VILLAIN = ["反派", "黑化", "变坏", "幕后黑手", "阴谋", "陷害", "背叛", "大boss", "boss"]
REVENGE = ["复仇", "报仇", "雪恨", "讨回", "清算", "报复"]
ROMANCE = ["在一起", "相爱", "结婚", "嫁给", "娶", "重逢", "私奔", "表白"]


def parse_instruction(instruction: str, structure: dict) -> dict:
    q = norm(instruction)
    intents = []
    if any(k in q.lower() for k in ["he", "happy"]) or any(k in q for k in HAPPY):
        intents.append("happy")
    if any(k in q.lower() for k in ["be"]) or any(k in q for k in TRAGIC):
        intents.append("tragic")
    if any(k in q for k in VILLAIN):
        intents.append("villain")
    if any(k in q for k in REVENGE):
        intents.append("revenge")
    if any(k in q for k in ROMANCE):
        intents.append("romance")
    if not intents:
        intents.append("happy" if any(k in q for k in ("改", "换", "不要", "不想")) else "custom")
    # 目标人物
    targets = []
    for c in structure["characters"][:15]:
        names = [c["name"]] + c.get("aliases", [])
        if any(n and n in q for n in names):
            targets.append(c["name"])
    return {"intents": intents, "targets": targets or _default_targets(structure),
            "raw": instruction}


def _default_targets(structure):
    chars = structure["characters"]
    return [c["name"] for c in chars[:2]]


def story_state(structure: dict, upto_chapter: int | None = None) -> dict:
    chars = structure["characters"]
    hero = chars[0]["name"] if chars else "主角"
    antagonists = [r["target"] for c in chars[:1] for r in c.get("relations", [])
                   if r["label"] in ("冲突", "仇敌")][:3]
    friends = [r["target"] for c in chars[:1] for r in c.get("relations", [])
               if r["label"] in ("朋友", "爱慕", "妻子", "丈夫", "同门")][:3]
    locs = [l["name"] for l in structure.get("locations", [])[:3]]
    last_events = [e["summary"] for e in structure.get("timeline", [])
                   if upto_chapter is None or e["chapter"] >= upto_chapter - 2][-4:]
    return {"hero": hero, "antagonists": antagonists or ["当权者"],
            "friends": friends or [], "locations": locs or ["故地"],
            "recent": last_events}


# ---------------- 段落级改写 ----------------

PHRASE_SWAP_HAPPY = [
    ("被抓", "主动现身"), ("被捉", "将计就计"), ("被押", "从容随行"),
    ("枪毙", "当堂释放"), ("杀头", "官复原职"), ("处死", "赦免"),
    ("输了", "赢了"), ("败了", "胜了"), ("失败", "得胜"),
    ("哭", "笑"), ("叹气", "松了口气"), ("绝望", "重新燃起希望"),
    ("冷笑", "相视一笑"), ("怒骂", "拱手相让"),
]
PHRASE_SWAP_TRAGIC = [
    ("赢了", "一败涂地"), ("得胜", "中计"), ("笑", "惨笑"),
    ("团圆", "永别"), ("得救", "无人来救"), ("希望", "泡影"),
]


def rewrite_paragraph(text: str, plan: dict) -> str:
    p = norm(text)
    swaps = PHRASE_SWAP_HAPPY if "happy" in plan["intents"] or "revenge" in plan["intents"] \
        else PHRASE_SWAP_TRAGIC if "tragic" in plan["intents"] else []
    for a, b in swaps:
        p = p.replace(a, b)
    target = plan["targets"][0] if plan["targets"] else "主角"
    # 补一个转机/转折句，保证改写可读且有新情节
    if "happy" in plan["intents"] or "revenge" in plan["intents"]:
        add = pick_line(plan["raw"], [
            f"就在这时，人群外忽然有人高声称冤，原来{target}早留了一手凭据，场面陡然逆转。",
            f"谁也没料到，{target}此前埋下的人情在此刻应验，局势轰然倒转。",
            f"千钧一发之际，一封文书快马送到——{target}的冤屈当堂昭雪。",
        ])
    elif "tragic" in plan["intents"]:
        add = pick_line(plan["raw"], [
            f"{target}张了张嘴，却发现四周没有一个人肯与他对视，风从长街尽头吹来，比刀子还冷。",
            "人群轰的一声围拢又散开，像什么都没有发生过，只有风声格外响。",
        ])
    elif "villain" in plan["intents"]:
        add = f"{target}缓缓转过身，眼底最后一点犹豫也熄灭了——从这一刻起，再没有退路。"
    else:
        add = f"这一幕落在{target}眼里，心里那杆秤，已经悄悄偏了方向。"
    # 把新句子插在段末标点之前
    if p.endswith(("。", "！", "？", "”", "…")):
        return p + add
    return p + "。" + add


def pick_line(seed: str, opts: list[str]) -> str:
    import hashlib
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return opts[h % len(opts)]


# ---------------- 章节/结局级生成 ----------------

def generate_ending(plan: dict, state: dict, mode: str = "ending") -> list[str]:
    intents = set(plan["intents"])
    hero = state["hero"]
    target = plan["targets"][0] if plan["targets"] else hero
    enemy = state["antagonists"][0]
    loc = state["locations"][0]
    friends = "、".join(state["friends"]) if state["friends"] else "旧日相识"
    recent = state["recent"][-1] if state["recent"] else "此前的风波"

    paras = []
    if "tragic" in intents and "happy" not in intents:
        paras = _tragic_beats(hero, enemy, loc, recent, friends)
    elif "villain" in intents and "happy" not in intents:
        paras = _villain_beats(target, hero, enemy, loc)
    elif "romance" in intents and "happy" not in intents and "revenge" not in intents:
        paras = _romance_beats(target, plan["targets"][-1] if len(plan["targets"]) > 1 else "心上人", loc)
    else:  # happy / revenge / 含 romance 的 HE 圆满向
        paras = _happy_beats(hero, enemy, loc, recent, friends,
                             revenge="revenge" in intents, target=target)
        if "romance" in intents:
            paras.extend(_romance_beats(target,
                                        plan["targets"][-1] if len(plan["targets"]) > 1 else "心上人",
                                        loc))
    # 模式标签
    label = {"ending": "结局改写", "chapter": "章节改写", "full": "全篇改写"}.get(mode, "改写")
    return [f"【{label}】"] + paras


def _happy_beats(hero, enemy, loc, recent, friends, revenge=False, target=None) -> list[str]:
    target = target or hero
    verb = "清算旧账" if revenge else "扭转了局面"
    return [
        f"谁也没有想到，最先变的是风向。那桩被所有人认定的旧事——{recent}——"
        f"在{loc}的一个清晨，被一封迟到的供状重新翻开。作证的不是旁人，"
        f"正是当年亲手经办的人；他说，良心债背了这些年，不能再背进棺材里。",
        f"{target}听到消息时，正蹲在墙根晒太阳。他没有像众人以为的那样跳起来，"
        f"只是慢慢站直身子，把皱了多年的衣角一下一下抹平。{friends}围过来时，"
        f"他才开口，声音很轻：\"我等这一天，等得都快忘了自己在等什么。\"",
        f"{enemy}起初还端着架子，要拿旧规矩压人。可这一回，围观的人没有跟着哄笑，"
        f"也没有人急着划清界限——供状、人证、当年被刻意漏掉的细枝末节，一件件摆上桌。"
        f"堂前的风向掉了个头，{target}没有挥拳，也没有骂人，他只是把当年咽下去的话，"
        f"一字一句地说了出来；那些话比拳头重得多。",
        f"等到一切落定，{target}在{loc}重新走了一遍从前的路。从前朝他关门的人家开了门，"
        f"叫错他名字的人主动让到路边。他并没有得意，只在经过旧地时停了停——"
        f"他知道自己赢的不是哪一场争执，而是\"终于被当个人看\"这件事。",
        "这一年的冬天来得很晚。日头照进巷口，墙根下的影子缩成短短的一团。"
        "风还是从前的风，可从风里走过的人，腰杆是直的。",
    ]


def _tragic_beats(hero, enemy, loc, recent, friends) -> list[str]:
    return [
        f"{recent}之后，事情并没有像大家私下盼望的那样缓过来。{loc}的日子照旧，"
        f"该出工的出工，该看热闹的看热闹，仿佛那场风波只是茶余饭后的一点盐。",
        f"{hero}后来又去过几次从前热闹的地方。门照旧开着，人却不再是那些人了："
        f"有人远远看见他便拐进巷子，有人当着面说笑，声音却刻意压低。"
        f"他渐渐明白，被记住的不是他受的委屈，而是他让别人不舒服过。",
        f"唯一一次转机在一个雨天，{friends}冒雨送来一句口信，说事情或许还有转圜。"
        f"可雨停之后，口信便没了下文，像一滴水落进土里。{hero}在门口坐到天黑，"
        f"第一次没有给自己找任何台阶。",
        f"最后的消息传来时，{loc}正赶上一场热闹，鞭炮和人声混作一团，"
        f"没有谁顾得上为一个小人物的结局停下筷子。多年以后，偶尔有老人提起他，"
        f"想了半天，只说：\"哦，是有这么个人。\"",
        "风穿过空巷子，卷起半张旧纸，又轻轻放下。这世上少了一个人，"
        "像水缸里少了一瓢水，水面晃了晃，便再没有痕迹。",
    ]


def _villain_beats(target, hero, enemy, loc) -> list[str]:
    return [
        f"没有人知道{target}是从哪一刻开始变的。也许是被推到泥里的那个雨夜，"
        f"也许是更早——在他一次次选择退让、却只换来变本加厉的那些瞬间。",
        f"他开始不动声色地做事：对羞辱过他的人微笑，把每一笔账记得清清楚楚，"
        f"在别人需要时恰好出现，又在事成之后恰好退开。{loc}的人都说他变了个人，"
        f"变得通情达理、值得托付。只有他自己知道，那张网已经织了多久。",
        f"收网那天，{enemy}甚至没有反应过来。从前他怎样被规矩碾过，"
        f"如今他就怎样让规矩替自己碾人——他没有亲手做任何一件坏事，"
        f"但每一件坏事落下时，都恰好合了他的意。",
        f"站在从前挨耳光的地方，{target}低头看着自己的手。他终于活成了没人敢欺负的人，"
        f"也终于明白了当年那些人为什么笑得出来。风很冷，他却笑出了声，"
        f"笑声在空巷里打转，和当年如出一辙。",
    ]


def _romance_beats(target, other, loc) -> list[str]:
    return [
        f"那场风波过后，{target}和{other}谁也没有先开口，倒是{loc}的邻里先看出了端倪："
        f"一个的伞总往另一个那边偏，一个碗里的好菜总往对方碗里夹。",
        f"真正把话说破，是在一个极寻常的傍晚。没有锣鼓，没有围观，"
        f"{target}只是把一件缝了又缝的旧衣递过去，闷声道：\"以后别再一个人扛了。\""
        f"{other}愣了愣，红着眼眶笑：\"这话，你让我等了太久。\"",
        f"日子照旧清贫，流言也没有一夜消失。但清早的灶火是两个人的，"
        f"晚归时巷口的那盏灯也是两个人的。这世间的大团圆未必都轰轰烈烈，"
        f"对他们而言，门里有一盏灯，已是圆满。",
    ]


# ---------------- 改写调度 ----------------

def rewrite(scope: str, instruction: str, structure: dict,
            original_text: str = "", chapter_idx: int | None = None) -> dict:
    plan = parse_instruction(instruction, structure)
    state = story_state(structure, chapter_idx)
    if scope == "paragraph":
        new_text = rewrite_paragraph(original_text, plan)
    else:
        paras = generate_ending(plan, state, scope)
        new_text = "\n".join(paras)
    return {
        "instruction": instruction,
        "plan": plan,
        "state": {k: v for k, v in state.items() if k != "recent"},
        "text": new_text,
        "word_count": len(new_text),
        "scope": scope,
    }


def stream_rewrite(scope, instruction, structure, original_text="", chapter_idx=None):
    """逐句产出，供 WebSocket 流式输出。"""
    result = rewrite(scope, instruction, structure, original_text, chapter_idx)
    buffer = ""
    for ch in result["text"]:
        buffer += ch
        if ch in "。！？…\n" and len(buffer) >= 6:
            yield {"delta": buffer}
            buffer = ""
    if buffer:
        yield {"delta": buffer}
    yield {"done": True, "meta": {"plan": result["plan"], "word_count": result["word_count"]}}
