"""导出：TXT / Markdown / EPUB；支持全书、读者分支、批注笔记、阅读报告。"""
from __future__ import annotations

import io

from .. import db


def _chapters(book):
    return [(c.title, c.paragraphs) for c in book.chapters]


def export_text(book, extra=None, mode: str = "full") -> str:
    out = [book.title, f"作者：{book.author or '佚名'}", ""]
    if mode == "branch":
        out += ["【读者分支】" + (extra["name"] if extra else ""),
                f"改写指令：{extra['instruction'] if extra else ''}", ""]
    for title, paras in _chapters(book):
        out.append(title)
        out.append("")
        if mode == "branch":
            paras = _apply_branch_paras(title, paras, book, extra)
        out.extend(paras)
        out.append("")
    return "\n".join(out)


def export_markdown(book, extra=None, mode: str = "full") -> str:
    out = [f"# {book.title}", "", f"**作者**：{book.author or '佚名'}", ""]
    if mode == "branch":
        out += [f"> **读者分支：{extra['name']}**  ",
                f"> 改写指令：{extra['instruction']}", ""]
    if mode == "notes":
        return _notes_markdown(book)
    if mode == "report":
        return _report_markdown(book)
    for i, (title, paras) in enumerate(_chapters(book)):
        out.append(f"## {title}")
        out.append("")
        ps = paras
        if mode == "branch":
            ps = _apply_branch_paras(title, ps, book, extra)
        out.extend(ps)
        out.append("")
        if mode == "notes":
            anns = db.query(
                "SELECT persona,title,content,quote FROM annotations "
                "WHERE book_id=? AND chapter_idx=? ORDER BY para_idx",
                (book.id, i))
            for a in anns:
                out.append(f"> **[{a['persona']}] {a['title']}**：{a['content']}")
            out.append("")
    return "\n".join(out)


def _apply_branch_paras(title, paras, book, branch_row):
    if not branch_row:
        return paras
    scope = branch_row["scope"]
    ch_idx = branch_row["chapter_idx"]
    titles = [c.title for c in book.chapters]
    try:
        cur_idx = titles.index(title)
    except ValueError:
        return paras
    new = list(paras)
    content_lines = [p for p in branch_row["content"].split("\n") if p.strip()]
    if scope == "paragraph" and cur_idx == ch_idx:
        pi = branch_row["para_idx"] or 0
        if 0 <= pi < len(new):
            new[pi] = content_lines[0] if content_lines else new[pi]
    elif scope == "chapter" and cur_idx == ch_idx:
        new = content_lines
    elif scope in ("ending", "full") and cur_idx >= ch_idx:
        if cur_idx == ch_idx:
            new = content_lines
        elif scope == "full":
            new = []
    return new


def _notes_markdown(book) -> str:
    out = [f"# 《{book.title}》AI 陪读笔记", "",
           f"作者：{book.author or '佚名'}", ""]
    ch_rows = db.query("SELECT idx,title FROM chapters WHERE book_id=? ORDER BY idx",
                       (book.id,))
    for ch in ch_rows:
        anns = db.query(
            "SELECT * FROM annotations WHERE book_id=? AND chapter_idx=? "
            "ORDER BY para_idx,priority DESC", (book.id, ch["idx"]))
        if not anns:
            continue
        out.append(f"## {ch['title']}")
        out.append("")
        sm = db.query_one(
            "SELECT summary FROM chapter_summaries WHERE book_id=? AND chapter_idx=?",
            (book.id, ch["idx"]))
        if sm and sm["summary"]:
            out += ["**本章梗概**：" + sm["summary"], ""]
        for a in anns:
            if a["quote"]:
                out.append(f"> 原文：{a['quote']}")
            out.append(f"- **{a['title']}**：{a['content']}")
        out.append("")
    return "\n".join(out)


def _report_markdown(book) -> str:
    stats = db.query_one(
        "SELECT COALESCE(SUM(seconds),0) seconds, COALESCE(SUM(words),0) words, "
        "COUNT(DISTINCT day) days FROM sessions WHERE book_id=?", (book.id,))
    n_ann = db.query_one(
        "SELECT COUNT(*) n FROM annotations WHERE book_id=?", (book.id,))["n"]
    n_br = db.query_one(
        "SELECT COUNT(*) n FROM branches WHERE book_id=?", (book.id,))["n"]
    return "\n".join([
        f"# 《{book.title}》阅读报告", "",
        f"- 作者：{book.author or '佚名'}",
        f"- 总字数：{book.word_count}",
        f"- 阅读时长：{round((stats['seconds'] or 0)/60)} 分钟",
        f"- 阅读天数：{stats['days']} 天",
        f"- AI 批注：{n_ann} 条",
        f"- 读者分支：{n_br} 条",
    ])


def export_epub(book, extra=None, mode: str = "full") -> str | bytes:
    from ebooklib import epub
    eb = epub.EpubBook()
    eb.set_identifier(f"ai-reader-{book.id}")
    eb.set_title(book.title + ("（读者分支）" if mode == "branch" else ""))
    eb.set_language("zh")
    eb.add_author(book.author or "佚名")
    chs = []
    for i, (title, paras) in enumerate(_chapters(book)):
        ps = paras
        if mode == "branch":
            ps = _apply_branch_paras(title, ps, book, extra)
        html = "<h1>{}</h1>".format(title) + "".join(f"<p>{p}</p>" for p in ps)
        c = epub.EpubHtml(title=title, file_name=f"ch{i}.xhtml", lang="zh")
        c.content = html
        eb.add_item(c)
        chs.append(c)
    eb.toc = tuple(chs)
    eb.spine = ["nav"] + chs
    eb.add_item(epub.EpubNcx())
    eb.add_item(epub.EpubNav())
    buf = io.BytesIO()
    epub.write_epub(buf, eb)
    return buf.getvalue()
