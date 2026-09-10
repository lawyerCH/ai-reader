"""轻量中文小说 NLP：句子切分、对白抽取、中文人名识别（无第三方模型依赖）。"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from . import lexicons as L

FULLWIDTH_MAP = {chr(0xFF21 + i): chr(0x41 + i) for i in range(26)}
FULLWIDTH_MAP.update({chr(0xFF41 + i): chr(0x61 + i) for i in range(26)})

SENT_SPLIT_RE = re.compile(r"(?<=[。！？…])")
QUOTE_RE = re.compile(r"[“「『]([^”」』]{1,400})[”」』]")

CN_CHAR = r"一-鿿㐀-䶿"
CN = f"[{CN_CHAR}]"

LEAD_PARTICLES = set("和与跟同连把被让向对给为是有又再就当着去从将比往朝令叫请陪随约了那这该及并或蒙过但而底得要使到说起初名未还知非深即配改反便在个如凡怕定你我他她咱看听见以替跟随按据向一二两三四五六七八九十百千万几数多有")
# 名字尾部功能字/常见动词：贪婪截到这些字时回收
TAIL_PARTICLES = set(
    "的了是也就便和又都再说想本进出来去上把被让向往给当似看听见要会敢肯应该能"
    "改变成作做为有无多少好坏前后里外中时人他你我她咱们或而且但则即若如着过"
    "笑哭怒骂打杀揍踢赶到抓捉抢偷讨要爱恨惧怕知道觉令使请叫说道问答叹喝")
# 物体/器物结尾：误识为人名时拒绝
OBJECT_TAIL = set("杠棒棍杖剑刀枪矛戟弓斧锤鞭碗筷锅盆桌椅门窗户墙车轿笔墨纸砚灯旗伞鼓铃钟镜裙衫帽鞋靴袜被褥箱匣柜篮盒瓶壶杯盘碟炉缸罐钵")
# 名字第二字若为功能字，基本是误截（是举/在举/大叫）
FUNCTIONAL_MID = set("是在此其也了在和与把被从到过上下大小有無无的着")
# 人名边界字：名字前/后遇到这些字，说明名字到此为止
NAME_BOUNDARY = set(
    "了着过和与及把被让向往对给是在有又也就才便都很最不还已正会能要想觉得看见听道说笑骂"
    "叫哭喊问答骂叹息怒慌忙快给已曾将把跟同随朝按照让使令这那他她你我咱其之个们"
    "，。、；：？！…—“”‘’「」『』 （）()《》〈〉·"
)
# 以这些字结尾的多半是地点/机构，不是人名
LOCATION_TAIL = set("祠庵寺庙府殿桥楼庄村镇城关寨谷江海河湖山峰山崖洞岛园苑铺坊馆厅阁堂社")

DIALOGUE_CUES = set("你我咱她他吗呢吧啊呀嘛么呗罢是不这那谁啥怎哪") | {"？", "！", "…"}

# 模式类候选的停用词
PATTERN_STOPWORDS = set(
    "大约 大多 大半 大夫 大小 小说 小事 小传 大传 自传 外传 内传 列传 别传 家传 老子 小子 小伙子 "
    "小说家 小孤孀 妈妈 老妈 老爷儿 老大 老小 老乡 小鬼 大师 大王 大方 大家 大声 大众 大叔 别人 "
    "于是他 于是我 于是她 这小子 那汉子 大竹杠 时候 那里 这里 那儿 这儿 东西 大抵 老兄 老弟 "
    "汉子 男人 女人 妇人 老人 孩子 儿子 女儿 里面 外面 前面 后面 未庄人 乡下人 城里人 "
    "从此 大概 大叫 老例 大防 大襟 大拇 小觑 文童 经停 怒目而视 从此他 翰林 "
    "阿呀 阿意 阿弥 阿唷 老鹰 老虎 老狗 老萝 小石 宣德炉 是举 在举 老婆 太太 奶奶 老头 "
    "那么 满足 大笑 小心 小半 大不 都没 大钱 大竹 小屋 大嚷 大洋 麻酱 能收 时却 "
    "大嚷 分辩 惶恐 一个老 长衫 两手叉在 历史癖 黄伞格 龙虎斗 刘海仙 农家 "
    "小姐 大姐 大哥 大娘 大嫂 公子 大儿子 和尚动".split()
)


def norm(text: str) -> str:
    for fw, hw in FULLWIDTH_MAP.items():
        text = text.replace(fw, hw)
    return text


def split_sentences(paragraph: str) -> list[str]:
    parts = [s.strip() for s in SENT_SPLIT_RE.split(paragraph) if s and s.strip()]
    return parts or ([paragraph] if paragraph else [])


def extract_quotes(paragraph: str):
    return [(m.group(1), m.start(), m.end()) for m in QUOTE_RE.finditer(paragraph)]


def is_dialogue(text: str) -> bool:
    if len(text) >= 9:
        return True
    return any(c in text for c in DIALOGUE_CUES)


# ---------- 人名识别 ----------

def _suffix_of(name: str):
    for suf in sorted(set(L.TITLE_SUFFIXES), key=len, reverse=True):
        if name.endswith(suf):
            return suf
    return ""


def _title_normalize(name: str, suffix: str) -> str:
    """头衔感知归一化：'非特秀才' -> '秀才'；'赵秀才' 保留。"""
    if not suffix:
        return name
    prefix = name[: -len(suffix)]
    if not prefix:
        return suffix
    if len(prefix) >= 2 and prefix[-2:] in L.COMPOUND_SURNAMES:
        return name
    if prefix[-1] in L.SINGLE_SURNAMES and len(prefix) <= 2:
        return name
    return suffix


def _trim_name(tok: str) -> str:
    tok = tok.strip("，。、：:；！？的 “”‘’「」『』()（）")
    # 先剥离开头虚词（"是赵太爷"->"赵太爷"），再做头衔归一化
    while tok and tok[0] in LEAD_PARTICLES and len(tok) > 2:
        tok = tok[1:]
    suf = _suffix_of(tok)
    if suf:
        return _title_normalize(tok, suf)
    changed = True
    while changed and len(tok) >= 2:
        changed = False
        if len(tok) > 2 and tok[-1] in TAIL_PARTICLES:
            t = tok[:-1]
            s = _suffix_of(t)
            if s:
                return _title_normalize(t, s)
            tok, changed = t, True
        if len(tok) > 2 and tok[0] in LEAD_PARTICLES:
            t = tok[1:]
            s = _suffix_of(t)
            if s:
                return _title_normalize(t, s)
            tok, changed = t, True
    return tok


def _is_personlike(name: str) -> bool:
    if name in PATTERN_STOPWORDS:
        return False
    if len(name) < 2 or len(name) > 4:
        return False
    if name[-1] in LOCATION_TAIL and not _suffix_of(name):
        return False
    if name[-1] in OBJECT_TAIL and not _suffix_of(name):
        return False
    # 名字中间夹功能词，多为误识（于是他 / 怒目而视 / 也回过头 / 是举）
    if len(name) == 3 and name[1] in "是此其也了":
        return False
    if len(name) == 4 and any(c in name[1:3] for c in "而之其相自无有不以于也又且或若如便则就过头来回"):
        return False
    if re.fullmatch(CN + r"+", name) and name[1] in FUNCTIONAL_MID:
        return False
    return True


def _patterns():
    suffixes = sorted(set(L.TITLE_SUFFIXES), key=len, reverse=True)
    suf_alt = "|".join(suffixes)
    speech = "|".join(sorted(set(L.SPEECH_VERBS), key=len, reverse=True))
    pats = [
        re.compile(rf"阿[{CN_CHAR}A-Za-z]"),
        # 小/老/大 + 单字（小D、老王），或 + 已知角色词尾（小尼姑）
        re.compile(rf"[小大老](?:尼姑|和尚|道士|妮子|丫头|头子|儿子|女儿|孩子|婆子|"
                   rf"姑娘|伙子|媳妇|官人|相公|孤孀|汉子)|[小大老][{CN_CHAR}A-Za-z]"),
        re.compile(rf"(?:假)?洋鬼子|{CN}{{0,2}}鬼子"),
        re.compile(rf"{CN}{{1,2}}(?:{suf_alt})"),
        re.compile(rf"{CN}{{0,2}}(?:娘子|婆子|婶子)"),
    ]
    return pats, speech


PATTERNS, SPEECH_ALT = _patterns()
SURNAME_CHARS = "".join(sorted(L.SINGLE_SURNAMES))
SURNAME_SCAN_RE = re.compile(rf"[{SURNAME_CHARS}]")
BARE_ROLES = ["举人老爷", "假洋鬼子", "洋鬼子", "小尼姑", "老尼姑",
              "地保", "把总", "掌柜", "举人", "秀才", "尼姑", "和尚", "道士",
              # 社会角色词（短篇中常以身份代姓名；只收区分度高的，避免泛词）
              "车夫", "老女人", "妇人", "乞丐", "丫鬟", "伙计", "老板娘",
              "船夫", "渔夫", "樵夫", "农夫", "屠夫", "更夫", "衙役",
              "捕快", "媒婆", "接生婆", "巡警", "警察", "护士", "房东",
              "短衣帮", "掌柜"]
# 可以把 "X秀才" 自动并到 "赵秀才" 的高区分度头衔
ROLE_MERGE_SUFFIXES = ("太爷", "秀才", "举人", "和尚", "尼姑", "把总", "地保",
                       "掌柜", "鬼子", "大人", "将军", "掌门", "帮主", "教主",
                       "宗主", "阁主", "长老")


def plausible_person(name: str) -> bool:
    """对白归属校验：候选必须长得像人名/角色，拒绝动词短语与形容词。"""
    if not name or not _is_personlike(name):
        return False
    if re.fullmatch(r"阿[一-鿿A-Za-z]", name):
        return True
    if re.fullmatch(r"[小大老][一-鿿A-Za-z]", name):
        return True
    if _suffix_of(name):
        return True
    if name in BARE_ROLES:
        return True
    if name.endswith("人物"):  # 长衫人物这类集体角色
        return True
    if re.fullmatch(CN + r"{2,3}", name):
        return name[0] in L.SINGLE_SURNAMES or name[:2] in L.COMPOUND_SURNAMES
    return False


def scan_surname_names(sentence: str):
    """在每个'边界后紧跟姓氏'的位置，尝试 2/3 字人名，做边界校验。"""
    out = set()
    for m in SURNAME_SCAN_RE.finditer(sentence):
        i = m.start()
        if i > 0 and sentence[i - 1] not in NAME_BOUNDARY:
            continue
        for length in (3, 2):
            tok = sentence[i:i + length]
            if len(tok) < length:
                continue
            if any(c in "，。、；：？！…“”‘’「」『』（）《》" for c in tok):
                continue
            if tok[-1] in TAIL_PARTICLES or tok[-1] in LOCATION_TAIL:
                continue
            # 尾部不做标点强约束：名字后常直接跟动词（"林秋白大惊"），
            # 假候选由跨章频次门槛过滤
            tok2 = _trim_name(tok)
            if tok2.endswith("家") and len(tok2) == 2:
                continue
            if len(tok2) >= 2 and tok2[0] in L.SINGLE_SURNAMES and _is_personlike(tok2):
                out.add(tok2)
            break  # 该位置只取一个最长合法候选
    return out


def extract_character_mentions(chapters: list[list[str]]):
    mentions: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "chapters": set(), "first": (0, 0),
        "titles": [], "sources": set(), "quotes": 0,
    })
    quotes: list[dict] = []

    def add(raw: str, ch: int, para: int, source: str, is_quote: bool = False):
        name = raw if source in ("role",) else _trim_name(raw)
        if not _is_personlike(name):
            return
        rec = mentions[name]
        rec["count"] += 1
        rec["chapters"].add(ch)
        rec["sources"].add(source)
        if is_quote:
            rec["quotes"] += 1
        if rec["count"] == 1:
            rec["first"] = (ch, para)
        suf = _suffix_of(name)
        if suf and suf not in rec["titles"]:
            rec["titles"].append(suf)

    for ci, paragraphs in enumerate(chapters):
        for pi, para0 in enumerate(paragraphs):
            para = norm(para0)
            sentences = split_sentences(para)
            for pat in PATTERNS:
                for m in pat.finditer(para):
                    add(m.group(0), ci, pi, "pattern")
            for role in BARE_ROLES:
                for rm in re.finditer(re.escape(role), para):
                    add(role, ci, pi, "role")
            for sentence in sentences:
                for tok in scan_surname_names(sentence):
                    add(tok, ci, pi, "freq")
            # 对白与归属（说话人必须通过人名合理性校验）
            for qm in QUOTE_RE.finditer(para):
                text = qm.group(1)
                dialogue = is_dialogue(text)
                after = para[qm.end(): qm.end() + 20]
                before = para[max(0, qm.start() - 22): qm.start()]
                speaker = None
                # 后置：“……”，XX（描述）道 —— 说话人必须紧跟引号之后
                am = re.match(
                    rf"[，。、；：\s]*({CN}{{2,4}}|[阿小大老][{CN_CHAR}A-Za-z])"
                    rf"(?:{CN}{{0,7}}?)(?:冷笑)?(?:{SPEECH_ALT})(?![{CN_CHAR}])",
                    after,
                )
                if am:
                    cand = _trim_name(am.group(1))
                    if plausible_person(cand):
                        speaker = cand
                if not speaker:
                    # 前置：XX（描述）道：“……” —— 取引号前最后一个合理人名
                    last = None
                    for nm in re.finditer(rf"({CN}{{2,4}}|[阿小大老][{CN_CHAR}A-Za-z])", before):
                        cand0 = _trim_name(nm.group(1))
                        if not plausible_person(cand0):
                            continue
                        tail = before[nm.end():]
                        if "。" in tail or "！" in tail or "？" in tail:
                            continue
                        if re.search(rf"(?:冷笑)?(?:{SPEECH_ALT})[：:]?\s*$", tail) and len(tail) <= 12:
                            last = cand0
                    if last:
                        speaker = last
                quotes.append({"ch": ci, "para": pi, "text": text,
                               "speaker": speaker, "is_dialogue": dialogue})
                if speaker and dialogue:
                    add(speaker, ci, pi, "speech", is_quote=True)

    kept: dict[str, dict] = {}
    for name, rec in mentions.items():
        # 泛称（老鹰、小石、阿七），需多次出现或有对白才保留
        weak_generic = (
            (re.fullmatch(rf"[小大老][{CN_CHAR}A-Za-z]", name)
             or re.fullmatch(rf"阿[{CN_CHAR}]", name))
            and not rec["titles"] and rec["quotes"] == 0)
        if rec["sources"] & {"role", "speech"}:
            kept[name] = rec
        elif "pattern" in rec["sources"]:
            if weak_generic and (rec["count"] < 3 or len(rec["chapters"]) < 2):
                continue
            kept[name] = rec
        elif rec["quotes"] > 0 or rec["titles"]:
            kept[name] = rec
        elif rec["count"] >= 4 and len(rec["chapters"]) >= 2:
            kept[name] = rec
        elif rec["count"] >= 7 and len(rec["chapters"]) >= 2:
            kept[name] = rec

    aliases = _cluster_aliases(kept)
    return kept, aliases, quotes


def _cluster_aliases(kept: dict[str, dict]) -> dict[str, set[str]]:
    groups: list[set[str]] = []

    def put(a: str, b: str):
        ga = next((g for g in groups if a in g), None)
        gb = next((g for g in groups if b in g), None)
        if ga and gb:
            if ga is not gb:
                ga |= gb
                groups.remove(gb)
        elif ga:
            ga.add(b)
        elif gb:
            gb.add(a)
        else:
            groups.append({a, b})

    names = list(kept)
    # 老Q / 阿Q / 小Q 同尾字归并
    for n in names:
        if len(n) == 2 and n[0] in "老小大阿":
            for n2 in names:
                if n2 != n and len(n2) == 2 and n2[0] in "老小大阿" and n2[1] == n[1]:
                    put(n, n2)
    # 高区分度头衔归并：仅当"唯一带姓氏头衔"时，把裸头衔并入；鬼子系特殊全并
    for suf in ROLE_MERGE_SUFFIXES:
        peers = [x for x in names if x == suf or (x.endswith(suf) and len(x) > len(suf))]
        if len(peers) <= 1:
            continue
        if suf == "鬼子":
            target = sorted(peers, key=lambda x: -kept[x]["count"])[0]
            for x in peers:
                if x != target:
                    put(x, target)
            continue
        titled = [x for x in peers
                  if len(x) > len(suf) and x[: -len(suf)][-1] in L.SINGLE_SURNAMES]
        bare = [x for x in peers if len(x) == len(suf)]
        if len(titled) == 1 and bare:
            for x in bare:
                put(x, titled[0])
    aliases: dict[str, set] = {}
    grouped: set[str] = set()
    for g in groups:
        main = sorted(g, key=lambda x: -kept[x]["count"])[0]
        aliases[main] = set(g)
        grouped |= g
    for n in names:
        if n not in grouped:
            aliases.setdefault(n, {n})
    return aliases


# ---------- BM25 词汇 ----------

def bigrams(text: str) -> list[str]:
    chars = re.findall(rf"{CN}|[A-Za-z0-9]+", norm(text))
    toks: list[str] = []
    cn_run = ""
    for c in chars:
        if re.fullmatch(CN, c):
            cn_run += c
        else:
            if cn_run:
                toks.extend(cn_run[i:i + 2] for i in range(max(0, len(cn_run) - 1)))
                cn_run = ""
            toks.append(c.lower())
    if cn_run:
        toks.extend(cn_run[i:i + 2] for i in range(max(0, len(cn_run) - 1)))
    return toks


def content_words(text: str, topk: int = 8) -> list[str]:
    c = Counter(bigrams(text))
    return [w for w, _ in c.most_common(topk)]
