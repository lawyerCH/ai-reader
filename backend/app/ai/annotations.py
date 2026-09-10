"""六角色 AI 批注引擎。

每个角色（plot/lore/emotion/snark/professor/character）是一组信号->批注的规则，
所有批注锚定到 (chapter, paragraph)，内容必须引用真实文本证据（人名/原句/章节号）。
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict

from . import lexicons as L
from .nlp import CN, CN_CHAR, norm, split_sentences, extract_quotes, bigrams


def pick(seed: str, options: list[str]) -> str:
    h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def clip(s: str, n: int = 46) -> str:
    s = s.strip()
    return s if len(s) <= n else s[:n].rstrip("，、；：") + "……"


# ---------- 历史/世界观小词典（考据党）----------
GLOSSARY = {
    "秀才": "秀才是明清科举制度中府州县学的生员，算是读书人挤进绅士阶层的第一道门槛。赵太爷的儿子中了秀才，在未庄就是特权阶层。",
    "举人": "举人是乡试中试者，比秀才高一级，已有做官资格，所以举人老爷在县里、乡里都极有势力。",
    "进士": "进士是会试、殿试中试者，科举塔尖，直接授官。",
    "状元": "殿试第一名为状元，科举制度的最高功名。",
    "把总": "把总是清代低级武官，约管几百兵丁，县里的兵丁归他带——阿Q最后的生死，正捏在这种人手里。",
    "地保": "地保是清代地方基层的差役，管治安、传讯、收贿，是官权伸进村子的末梢神经。",
    "太爷": "\"太爷\"是百姓对知县（县长）的尊称，也用来攀称有权势的乡绅，比如赵太爷。",
    "皇帝": "皇帝是封建王朝的最高统治者。故事背景在清末，皇帝、辫子、杀头都是那个时代的符号。",
    "辫子": "清朝强迫男子剃发留辫，辫子是归顺清廷的标志；剪辫子在清末是\"革命\"姿态，风险极高。",
    "革命": "这里指辛亥革命（1911）。革命党反清，但消息传到未庄这样的乡村，已经被传得面目全非。",
    "革命党": "革命党即清末反清革命组织成员，在乡民口中是\"反贼\"又是\"新贵\"，人人怕又人人想攀。",
    "自由党": "民国初年的政党。乡里传成\"柿油党\"（读音相近），还演化出\"银桃子\"的想象，是典型的信息失真。",
    "柿油党": "\"柿油党\"是\"自由党\"在乡间以讹传讹的叫法——谣言经过文盲社会加工后的产物。",
    "银桃子": "\"银桃子\"是乡民想象中革命党人的徽章（自由党徽章其实是铜质小章），把新权力想象成旧式功名。",
    "崇祯": "崇祯是明朝末代皇帝。乡下人以为革命就是替崇祯皇帝报仇，反清复明，可见他们对革命毫无理解。",
    "崇正": "\"崇正\"是\"崇祯\"的乡间讹读，乡下人把革命理解成\"反清复明\"。",
    "宣统": "宣统是清末代皇帝溥仪的年号，故事就发生在宣统三年（1911）辛亥革命前后。",
    "大团圆": "\"大团圆\"本是戏曲/小说术语，指圆满结局。这里用作杀人示众的委婉说法，是极冷的反讽。",
    "杀头": "杀头是清代主要死刑方式，公开行刑、万人围观，是鲁迅反复批判的\"看客文化\"场景。",
    "枪毙": "枪毙是随近代化军队出现的新式死刑；用枪毙代替杀头，在小说里成了革命带来的唯一\"新气象\"。",
    "土谷祠": "土谷祠即土地庙，祭土地神的乡间小庙，通常破败，住的是最底层的流民——阿Q的\"公馆\"。",
    "静修庵": "静修庵是带发修行的小庙，供奉佛像；革命一起来，庵里的龙牌先被砸，是闹剧式的\"革命对象\"。",
    "龙牌": "龙牌是写着皇帝万岁的牌位，皇权在民间的具象象征。砸龙牌=象征性的造反。",
    "宣德炉": "明宣宗宣德年间铸造的铜炉，后世视作古董珍品。赵太爷家被讹传窝藏宣德炉，是借机敲诈。",
    "尼姑": "尼姑是出家女性。静修庵里的老尼姑、小尼姑是弱者中的弱者，阿Q受了气便去欺辱她们。",
    "和尚": "和尚是出家男性。\"和尚动得，我动不得？\"是阿Q欺辱小尼姑时的混账逻辑。",
    "立传": "正史立传（传记）是传统士大夫追求的不朽事业。小说开头反复辨析\"传\"的名目，是在戏仿史传笔法。",
    "正史": "正史指官方认可的纪传体史书（二十四史）。阿Q不配进正史，小说偏用正史笔法写他，形成反讽。",
}

# 反复修辞/口头禅：跨章复现即"反复"
CATCHPHRASES = [
    "儿子打老子", "我们先前", "你算是什么东西", "状元不也是", "精神胜利",
    "优胜", "你配", "和尚动得",
]

# 名场面（吐槽君定制，命中后用定制吐槽，避免把经典当俗套骂）
SIGNATURE_SCENES = [
    (["儿子打老子"], "被打了就默念\"儿子打老子\"，挨打方秒变长辈——这套精神胜利法，堪称人类自我安慰界的祖师爷级发明。"),
    (["我们先前", "阔得多"], "\"我们先前——比你阔多啦！\" 古今中外通用句式，至今评论区随处可见。"),
    (["你算是什么东西"], "阿Q骂人三连的核心句式，自带一套鄙视链：我打不过的，我就从辈分上压过你。"),
    (["和尚动得", "动不得"], "\"和尚动得，我动不得？\"——顶级滑坡逻辑：别人做了坏事，所以我也做得。"),
    (["优胜记略", "续优胜"], "章节名就叫\"优胜记略\"——明明节节败退，却处处记功，标题本身就是反讽。"),
    (["大团圆"], "注意这个\"大团圆\"：全书最惨的结局，偏用最喜庆的词，鲁迅的刀藏在标题里。"),
    (["柿油党", "银桃子"], "自由党→柿油党，铜徽章→银桃子。消息每经过一张嘴就变一次形，百年前的谣言传播学。"),
    (["精神胜利"], "精神胜利法的精髓：物理上输了没关系，只要我宣布自己赢了，那我就是赢了。"),
]

# 通用网文套路（吐槽君）——在网文演示文本中命中
from .lexicons import TROPES, LOGIC_SMELLS  # noqa: E402

EMOTION_WORDS = set("怒喜哀惧爱恨羞急".split())


def hash01(*parts) -> float:
    h = hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class AnnotationBuilder:
    def __init__(self, book, structure: dict):
        self.book = book
        self.chapters = book.chapters
        self.st = structure
        self.canonical = structure.get("canonical", {})
        self.names = [c["name"] for c in structure["characters"]]
        self.name_re = re.compile("|".join(
            re.escape(n) for n in sorted(self.names, key=len, reverse=True))) if self.names else None
        self.out: list[dict] = []
        self.caps: dict[tuple[str, int], int] = defaultdict(int)
        self._seen: set[tuple] = set()

    def add(self, ch, pi, persona, kind, title, content, quote="", priority=0.5,
            cap_key=None, cap=None, dedupe=True, **payload):
        if cap_key is not None and cap is not None:
            if self.caps[(persona, ch, cap_key)] >= cap:
                return
            self.caps[(persona, ch, cap_key)] += 1
        if dedupe:
            dkey = (persona, kind, ch, content[:36])
            if dkey in self._seen:
                return
            self._seen.add(dkey)
        self.out.append({
            "chapter_idx": ch, "para_idx": pi, "persona": persona, "kind": kind,
            "title": title, "content": content, "quote": quote,
            "priority": round(priority, 3), "payload": payload,
        })

    def canon(self, raw: str) -> str:
        return self.canonical.get(raw, raw)

    def present(self, text: str) -> list[str]:
        if not self.name_re:
            return []
        return sorted({self.canon(m.group(0)) for m in self.name_re.finditer(text)})

    # ------------------------------------------------------------------
    def build(self) -> list[dict]:
        self._book_level()
        seen_names: set[str] = set()
        seen_locations: set[str] = set()
        seen_settings: set[str] = set()
        motif_count: Counter = Counter()

        for ci, ch in enumerate(self.chapters):
            for pi, p0 in enumerate(ch.paragraphs):
                p = norm(p0)
                present = self.present(p)
                for n in present:
                    if n not in seen_names:
                        seen_names.add(n)
                        self._character_enter(ci, pi, n, p)
                self._plot_signals(ci, pi, p, present)
                self._lore_signals(ci, pi, p, present, seen_locations, seen_settings)
                self._emotion_signals(ci, pi, p, present)
                self._snark_signals(ci, pi, p, present)
                self._professor_signals(ci, pi, p, ch, present, motif_count)
                self._character_voices(ci, pi, p, present)
            self._chapter_end(ci)

        self._foreshadow_annotations()
        self.out.sort(key=lambda a: (a["chapter_idx"], a["para_idx"], -a["priority"]))
        return self.out

    # ---------------- 全书级 ----------------
    def _book_level(self):
        title = self.book.title
        self.add(0, 0, "lore", "book_intro", "考据党已就位",
                 f"《{title}》开篇之前先报个到：我会在地名、官职、风俗出现时补充背景，"
                 "并顺手核查前后设定有没有打架。", priority=0.4, cap_key="intro", cap=1)
        n_chars = len(self.st["characters"])
        self.add(0, 0, "plot", "book_intro", "剧情党已就位",
                 f"全书共 {len(self.chapters)} 章，目前识别出 {n_chars} 个有名有姓的角色。"
                 "我负责盯伏笔、猜走向、标转折——咱们边读边对。", priority=0.4,
                 cap_key="intro", cap=1)

    # ---------------- 人物登场（剧情党）----------------
    def _character_enter(self, ci, pi, name, para):
        rec = next((c for c in self.st["characters"] if c["name"] == name), None)
        if not rec:
            return
        role_cn = {"protagonist": "主角", "supporting": "重要人物", "minor": "次要人物"}
        if rec["role"] == "protagonist":
            title, pri = "主角登场", 0.95
            content = (f"{name}登场了——本书的绝对主角。第一次被提起就带着身份悬念："
                       f"姓什么、叫什么都没人说得清。先记住他，后面整本书都围着他转。")
        elif rec["role"] == "supporting":
            title, pri = "重要人物出场", 0.85
            alias = f"（{'、'.join(rec['aliases'][:3])}）" if rec["aliases"] else ""
            content = f"新面孔：{name}{alias}，{role_cn[rec['role']]}，头衔：{'、'.join(rec['titles']) or '无'}。这人后面戏份不轻，先混个脸熟。"
        else:
            title, pri = "人物出场", 0.55
            t = f"，{rec['titles'][0]}" if rec["titles"] else ""
            content = f"{name}{t} 出场。未庄群像又添一位，留意他和主角的关系。"
        self.add(ci, pi, "plot", "character_enter", title, content,
                 quote=clip(para, 30), priority=pri)
        # 考据党给头衔加注
        for t in rec.get("titles", []):
            if t in GLOSSARY and self.caps[("lore", ci, "gloss")] < 3:
                self.add(ci, pi, "lore", "title_gloss", f"设定注释：{t}",
                         GLOSSARY[t], quote=name, priority=0.7,
                         cap_key="gloss", cap=3)

    # ---------------- 剧情党 ----------------
    def _plot_signals(self, ci, pi, p, present):
        # 转折/惊变
        for cue in ("突然", "忽然", "不料", "没想到", "谁知", "竟然", "居然", "殊不知"):
            if cue in p and len(p) > 20:
                sent = next((s for s in split_sentences(p) if cue in s), p)
                self.add(ci, pi, "plot", "turning_point", f"剧情转折（{cue}）",
                         pick(f"{ci}{pi}{cue}", [
                             f"注意这个\"{cue}\"——叙事节奏在这里拐了个弯，作者不会无缘无故安排意外。",
                             f"\"{cue}\"是转折点信号灯：{clip(sent, 34)} 接下来多半要变天。",
                             f"敲黑板，\"{cue}\"出现了。这种地方最容易埋后文要回收的东西。",
                         ]), quote=clip(sent, 40), priority=0.8)
                break
        # 关键行动
        for cue, label in [("决定", "决断时刻"), ("宣布", "风向变了"), ("终于", "关键节点"),
                           ("原来", "真相揭开"), ("结果", "结果来了"), ("最后", "收束信号")]:
            if cue in p and len(p) > 24:
                sent = next((s for s in split_sentences(p) if cue in s), None)
                if sent:
                    self.add(ci, pi, "plot", "key_event", label,
                             f"{cue}之后的叙述通常是作者在给剧情定调：{clip(sent, 40)}",
                             quote=clip(sent, 40), priority=0.62,
                             cap_key="key_event", cap=2)
                break

    def _chapter_end(self, ci):
        ch = self.chapters[ci]
        if ci == len(self.chapters) - 1:
            # 全书结尾
            self.add(ci, len(ch.paragraphs) - 1, "professor", "ending_note",
                     "结尾手法：示众与看客",
                     "结尾没有刑场特写，只有人群、喝彩声和一句关于\"狼眼睛\"的比喻。"
                     "真正被处决的不只是阿Q，还有围观者的良知——这是鲁迅式的留白。",
                     priority=0.9)
            return
        last_para = norm(ch.paragraphs[-1]) if ch.paragraphs else ""
        # 章末钩子
        hook = None
        if last_para.rstrip().endswith(("？", "？”", "？”")):
            hook = "本章以问号收尾，悬念是故意吊在这儿的。"
        elif any(w in last_para for w in ("不知", "未卜", "且看", "后事", "等待", "等候")):
            hook = "作者把悬念明着留在了最后一句，标准的章末钩子。"
        if hook:
            self.add(ci, len(ch.paragraphs) - 1, "plot", "cliffhanger",
                     "章末钩子", hook, quote=clip(last_para, 40), priority=0.72)
        # 剧情预测（基于本章人物与事件）
        evs = [e for e in self.st["timeline"] if e["chapter"] == ci]
        active = evs[-1]["chars"][:3] if evs else []
        if active:
            lead = active[0]
            pred = pick(f"pred{ci}", [
                f"我赌五毛：下一章 {lead} 的处境还会继续下坠，而且会有人来踩最后一脚——本书的规律是祸不单行。",
                f"预测：{lead} 刚经历的这件事不会就这么过去，要么引来更大的羞辱，要么引来一次虚假的转机。",
                f"按目前的走向，{ ('、'.join(active[:2])) if len(active)>1 else lead } 之间的账还没算完，下章必有回响。",
                f"留意：本章埋的情绪（{ '、'.join(active[:2]) if len(active)>1 else lead }）会在后面加倍奉还，鲁迅写屈辱从来当场不结账。",
            ])
            self.add(ci, len(ch.paragraphs) - 1, "plot", "prediction",
                     "剧情党预测", pred, priority=0.66)

    def _foreshadow_annotations(self):
        for k, f in enumerate(self.st.get("foreshadows", [])):
            pf, po = f["plant"], f.get("payoff")
            if f["status"] == "resolved" and po:
                self.add(pf["chapter"], pf["para"], "plot", "foreshadow_plant",
                         "伏笔埋设",
                         f"这里像是在埋线（信号词：{f['keyword'] or '暗示'}）。"
                         f"记住这个细节，它在第{po['chapter']+1}章会有回响。",
                         quote=pf["text"], priority=0.75,
                         cap_key="fs", cap=4)
                self.add(po["chapter"], po["para"], "plot", "foreshadow_payoff",
                         "伏笔回收",
                         f"呼应上了！第{pf['chapter']+1}章埋的线索（{clip(pf['text'], 20)}）"
                         f"在这里被揭开——前后对照着看特别有味道。",
                         quote=po["text"], priority=0.9,
                         cap_key="fp", cap=4)
            else:
                self.add(pf["chapter"], pf["para"], "plot", "foreshadow_plant",
                         "悬而未决的疑点",
                         f"此处作者有意留白/暗示（{f['keyword']}），先存个档，看后文如何回收。",
                         quote=pf["text"], priority=0.6, cap_key="fs", cap=4)

    # ---------------- 考据党 ----------------
    def _lore_signals(self, ci, pi, p, present, seen_loc, seen_set):
        # 词典注释（全书每词首次遇到即注）
        for term, gloss in GLOSSARY.items():
            if term in p and term not in seen_set:
                seen_set.add(term)
                self.add(ci, pi, "lore", "title_gloss", f"设定注释：{term}",
                         gloss, quote=term, priority=0.75, cap_key="gloss", cap=4)
        # 新地点
        for loc in self.st.get("locations", []):
            name = loc["name"]
            if name in p and name not in seen_loc:
                seen_loc.add(name)
                kind = "新地点"
                desc = loc.get("desc", "")
                self.add(ci, pi, "lore", "new_location", f"{kind}：{name}",
                         f"地图新增坐标：{name}。"
                         + (f"原文语境：{clip(desc, 40)}" if desc else
                            "留意这个空间在后续情节中的功能（居所/公共空间/权力场所）。"),
                         quote=name, priority=0.6, cap_key="loc", cap=4)
        # 新设定/组织/功法/文献
        for s in self.st.get("settings", []):
            term = s["term"]
            if s["type"] == "文献典故" and term in self.book.title:
                continue
            if term in p and term not in seen_set:
                seen_set.add(term)
                type_cn = {"组织势力": "组织/势力", "功法武学": "武学设定",
                           "社会概念": "社会设定", "文献典故": "文献典故"}[s["type"]]
                self.add(ci, pi, "lore", "new_setting", f"{type_cn}：{term}",
                         self._setting_text(s), quote=term, priority=0.55,
                         cap_key="setting", cap=3)
        # 称谓/数字一致性轻核查
        m = re.search(r"(.{0,6})([一二三四五六七八九十两\d]+)年(.{0,10})", p)
        if m and self.caps[("lore", ci, "era")] == 0 and any(
                w in p for w in ("宣统", "光绪", "咸丰", "同治", "民国", "崇祯")):
            self.add(ci, pi, "lore", "worldview_note", "纪年核查",
                     "出现了具体纪年，这是考据党最爱的锚点——可以据此排出故事的真实时间线。",
                     quote=clip(p, 24), priority=0.5, cap_key="era", cap=1)

    def _setting_text(self, s):
        t = s["type"]
        if t == "文献典故":
            return f"文中提到的作品/典故：《{s['term']}》。鲁迅喜欢把典籍和俗语并置，互文是理解反讽的钥匙。"
        if t == "社会概念":
            base = s.get("summary", "")
            return f"社会设定条目：{s['term']}。" + (f"语境：{clip(base, 44)}" if base else "")
        if t == "组织势力":
            return f"组织/场所条目：{s['term']}，在第{s['first_chapter']+1}章首次出现。"
        return f"设定条目：{s['term']}（{t}）。"

    # ---------------- 情感分析师 ----------------
    def _emotion_signals(self, ci, pi, p, present):
        emotions = []
        for emo, words in L.EMOTIONS.items():
            hits = [w for w in words if w in p]
            if hits:
                emotions.append((emo, hits[0]))
        quotes = extract_quotes(p)
        dlg = [q for q in quotes if q[0] and len(q[0]) >= 4]
        # 两人同框+情绪（以含情绪词的句子内人物为准）
        if len(present) >= 2 and emotions:
            emo, word = emotions[0]
            sent = next((s for s in split_sentences(p) if word in s), p)
            in_sent = self.present(sent)
            if len(in_sent) >= 2:
                a, b = in_sent[0], in_sent[1]
            elif len(in_sent) == 1 and present:
                a = in_sent[0]
                b = next((x for x in present if x != a), present[0])
            else:
                a, b = present[0], present[1]
            emo_cn = {"怒": "愤怒/敌意", "喜": "喜悦", "哀": "悲伤", "惧": "恐惧",
                      "爱": "爱意", "恨": "恨意", "羞": "羞赧", "急": "焦急"}[emo]
            self.add(ci, pi, "emotion", "relationship_moment",
                     f"关系中的{emo_cn}",
                     pick(f"emo{ci}{pi}", [
                         f"{a} 和 {b} 同框，情绪词是\"{word}\"。表面写动作，实际在给两人的关系定调。",
                         f"注意 {a} 对 {b} 的{emo_cn}（\"{word}\"）——人物关系的变化往往先从语气泄露。",
                         f"这一段的情绪重心是{emo_cn}。{a}、{b} 之间的张力，比台词本身更重要。",
                     ]), quote=clip(sent, 40), priority=0.7, cap_key="rel", cap=3)
        # 恋爱/性张力信号
        for cue in ("喜欢", "困觉", "娶", "嫁", "调戏", "下跪", "跪", "动情", "恋爱", "求爱"):
            if cue in p and len(present) >= 1 and self.caps[("emotion", ci, "love")] < 2:
                self.add(ci, pi, "emotion", "romance", "情感线警报",
                         f"出现\"{cue}\"这类信号词。本章是感情线的关键节点——"
                         "注意当事人事后关系的变化，文学作品里没有无缘无故的靠近。",
                         quote=clip(p, 40), priority=0.66, cap_key="love", cap=2)
                break
        # 纯对白段：潜台词提醒
        if len(dlg) >= 3 and self.caps[("emotion", ci, "subtext")] < 1:
            self.add(ci, pi, "emotion", "subtext", "密集对白：听弦外之音",
                     "连续多句对话，注意人物没说出口的那部分——问非所问、答非所答，往往才是真情绪。",
                     quote=clip(dlg[1][0], 30), priority=0.55, cap_key="subtext", cap=1)

    # ---------------- 吐槽君 ----------------
    def _snark_signals(self, ci, pi, p, present):
        # 名场面优先
        for cues, line in SIGNATURE_SCENES:
            if all(c in p for c in [cues[0]]) and any(c in p for c in cues):
                if self.caps[("snark", ci, "sig")] < 3:
                    self.add(ci, pi, "snark", "signature_scene", "名场面预警",
                             line, quote=clip(p, 40), priority=0.88,
                             cap_key="sig", cap=3)
                    return
        # 网文套路
        for cues, _key, line in TROPES:
            if any(c in p for c in cues) and self.caps[("snark", ci, "trope")] < 2:
                hit = next((s for s in split_sentences(p) if any(c in s for c in cues)), p)
                self.add(ci, pi, "snark", "trope", "桥段雷达",
                         line, quote=clip(hit, 36),
                         priority=0.7, cap_key="trope", cap=2)
                return
        # 逻辑异味
        for cues, _key, line in LOGIC_SMELLS:
            if any(c in p for c in cues) and self.caps[("snark", ci, "logic")] < 2:
                self.add(ci, pi, "snark", "logic_smell", "逻辑小问号",
                         line, quote=clip(p, 36), priority=0.6,
                         cap_key="logic", cap=2)
                return
        # 自我安慰/精神胜利名场面模式（挨打+立刻想开）
        if any(w in p for w in ("打", "揍", "骂", "欺")) and any(
                w in p for w in ("胜利", "得意", "心满意足", "反倒", "反而高兴", "笑嘻嘻")) and \
                self.caps[("snark", ci, "comfort")] < 1:
            self.add(ci, pi, "snark", "signature_scene", "经典自我PUA现场",
                     "刚挨完打立刻就能给自己找补回来——伤害转化率百分之百，建议书名改成《我的情绪价值由我自己创造》。",
                     quote=clip(p, 40), priority=0.78, cap_key="comfort", cap=1)

    # ---------------- 文学教授 ----------------
    def _professor_signals(self, ci, pi, p, ch, present, motif_count):
        # 元叙事（序章叙述者跳出来）
        if ci == 0 and any(w in p for w in ("我要给", "做正传", "立言", "名目", "传的名目")) \
                and self.caps[("professor", ci, "meta")] < 2:
            self.add(ci, pi, "professor", "meta_narrative", "元小说开篇",
                     "小说不从故事写起，反而先花一整章讨论\"该怎么给阿Q立传\"——"
                     "这是对正史笔法的戏仿，也提前声明：本书的主人公不配被传统史书记住。",
                     quote=clip(p, 40), priority=0.9, cap_key="meta", cap=2)
        # 比喻
        for cue in ("像", "仿佛", "宛如", "犹如", "如同", "似的", "般"):
            if cue in p:
                sent = next((s for s in split_sentences(p) if cue in s), None)
                if sent and 8 < len(sent) < 90 and self.caps[("professor", ci, "simile")] < 2:
                    frag = self._simile_frag(sent, cue)
                    self.add(ci, pi, "professor", "simile", "比喻赏析",
                             f"这里用了比喻（\"{cue}\"）：{clip(frag, 46)} "
                             "用具象之物写抽象之态，是鲁迅白描里常见的冷峻笔法。",
                             quote=clip(frag, 40), priority=0.62,
                             cap_key="simile", cap=2)
                    break
        # 口头禅/反复修辞
        for phrase in CATCHPHRASES:
            if phrase in p:
                motif_count[phrase] += 1
                if motif_count[phrase] == 2 and self.caps[("professor", ci, "rep")] < 2:
                    self.add(ci, pi, "professor", "repetition", "反复修辞",
                             f"\"{phrase}\"在书里第二次出现了。鲁迅有意让同一句话反复出现——"
                             "这叫\"反复\"修辞：重复本身就是讽刺，重复的次数越多，人物越显得可悲。",
                             quote=phrase, priority=0.72, cap_key="rep", cap=2)
        # 反讽信号
        for cue in ("高尚", "光荣", "文明", "优胜", "可敬", "盛世", "大团圆", "完美"):
            if cue in p and self.caps[("professor", ci, "irony")] < 2:
                sent = next((s for s in split_sentences(p) if cue in s), p)
                self.add(ci, pi, "professor", "irony", "反讽识别",
                         f"\"{cue}\"是褒义词，但它出现的语境却是负面情节——"
                         "词义与情境的落差，就是反讽。读鲁迅时越是漂亮词越要警惕。",
                         quote=clip(sent, 36), priority=0.7, cap_key="irony", cap=2)
                break
        # 插叙/补叙
        for cue in ("回想", "回忆", "那年", "多年前", "从前", "当初", "小时候"):
            if cue in p and self.caps[("professor", ci, "flash")] < 1:
                self.add(ci, pi, "professor", "flashback", "插叙/补叙",
                         f"\"{cue}\"把时间线拉回过去——插叙不是闲笔，它在用往事解释此刻人物的行为逻辑。",
                         quote=clip(p, 36), priority=0.55, cap_key="flash", cap=1)
                break
        # 环境开篇
        if pi <= 2 and any(w in p[:12] for w in
                           ("月光", "月色", "秋风", "春风", "微风", "夕阳", "黄昏",
                            "大雪", "细雨", "阴雨", "清晨", "傍晚", "夜里", "那一日", "第二天")) \
                and self.caps[("professor", ci, "scene")] < 1:
            self.add(ci, pi, "professor", "scene_setting", "环境定调",
                     "以时间/景物开场，是为全章定情绪基调。留意这段天气与人物命运之间的呼应。",
                     quote=clip(p, 30), priority=0.5, cap_key="scene", cap=1)

    def _simile_frag(self, sent: str, cue: str) -> str:
        i = sent.find(cue)
        lo = max(0, i - 14)
        hi = min(len(sent), i + 22)
        return sent[lo:hi]

    # ---------------- 角色本人 ----------------
    VOICE_STYLE = {
        "阿Q": [
            "哼，儿子打老子！等我发达了……我们先前，可比你阔得多啦。",
            "（摸了摸后脑勺）你懂什么，我这是儿子打老子，赢的是我。",
        ],
        "赵太爷": [
            "混账！未庄有我赵太爷在，哪里轮得到你说话？",
            "（满脸溅朱）你也配姓赵？",
        ],
        "假洋鬼子": [
            "我说你们啊，根本不懂什么叫革命。来，听我讲外面的世界。",
        ],
        "吴妈": [
            "啊呀，这可叫我以后怎么做人……我要去告诉太太！",
        ],
        "小尼姑": [
            "（红着脸）我招谁惹谁了……和尚动得，关我什么事呀。",
        ],
        "王胡": [
            "嗤。（胡子一翘，并不答话）",
        ],
        "小D": [
            "我……我又没惹你。（往后缩了缩）",
        ],
        "举人老爷": [
            "这种事体，合乎中庸的么？总要周全，周全才好。",
        ],
        "地保": [
            "走走走，太爷叫你呢。（掂了掂手里的酒钱）规矩你是懂的。",
        ],
        "把总": [
            "立正！本总在此，杀一儆百——不好看，那也是要示众的。",
        ],
    }

    def _character_voices(self, ci, pi, p, present):
        if not present or self.caps[("character", ci, "voice")] >= 2:
            return
        # 选一个“最该说话”的人：有定制台词 > 该段有对白且本人在场 > 情绪冲突
        candidate = None
        styled = [n for n in present if n in self.VOICE_STYLE]
        if styled:
            candidate = styled[0]
        if not candidate:
            for qt, _, _ in extract_quotes(p):
                qnames = self.present(qt)
                for n in qnames:
                    rec = next((c for c in self.st["characters"] if c["name"] == n), None)
                    if rec and rec["sample_quotes"]:
                        candidate = n
                        break
                if candidate:
                    break
        if not candidate:
            hot = [w for w in ("打", "骂", "哭", "怒", "跪", "死", "抓", "赶",
                               "刺", "剑", "击", "倒", "求饶", "仇", "杀") if w in p]
            if hot and present:
                # 优先选有定制台词/主角
                styled = [n for n in present if n in self.VOICE_STYLE]
                candidate = styled[0] if styled else present[0]
        if not candidate:
            return
        rec = next((c for c in self.st["characters"] if c["name"] == candidate), None)
        if not rec:
            return
        styles = self.VOICE_STYLE.get(candidate)
        if styles:
            line = pick(f"voice{ci}{pi}{candidate}", styles)
            content = f"【{candidate}的心声】{line}"
        else:
            # 通用心声模板
            trait = rec["traits"][0] if rec["traits"] else ""
            content = pick(f"voice{ci}{pi}{candidate}", [
                f"【{candidate}的心声】这事儿搁我身上，我先记下了。{('他们说我'+trait+'，可谁又问过我是怎么想的。') if trait else ''}",
                f"【{candidate}的心声】（看了一眼在场的人，没作声）有些话，不必说出口。",
                f"【{candidate}的心声】若你是我，这一刻只怕也未必有第二个选法。",
            ])
        self.add(ci, pi, "character", "in_character", f"{candidate}本人发话",
                 content, quote=clip(p, 30), priority=0.58,
                 cap_key="voice", cap=2)


def generate_annotations(book, structure: dict) -> list[dict]:
    return AnnotationBuilder(book, structure).build()
