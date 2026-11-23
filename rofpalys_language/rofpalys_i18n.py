#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - ONE language system for everything: GUI, TUI, statistics, remote page, lyric translation (English, Indonesian, Chinese, German, Japanese, Russian)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""Every text of Rofpalys is written in English in its own file (a dictionary, or a plain string). When the language is not English, the English text is looked up
in the catalogue of that language and swapped:

    tr("Play next")                  -> "Als Nächstes" (German), "下一首播放" (Chinese) ...   (unknown text: the English text itself, never an error)
    tr("Sleep timer: %s") % "10 min"  -> the template is translated first, the numbers go in afterwards
    pick(TABLE, lang, "key")          -> the old per-file dictionaries: their own en / id entry when there is one, else tr() of their English entry

The catalogues are the files  rofpalys_i18n_<code>.py  (a dictionary  CAT = {english text: translated text}).  A language that has no file yet shows English: nothing breaks.
The language in use is the one the engine keeps (E.current_lang): the GUI menu, the TUI key X and  rofpalys lang  all change that one value.

ROFPALYS_PSEUDO_LANG=1 (tests only): tr() wraps every text it handles in  ⟦ ⟧  so a text that was NOT handled (a forgotten English string in the code) shows without them."""
import importlib
import os
import re
import sys

__version__ = "1.0"
CODES = ("en", "id", "zh", "de", "ja", "ru")
NAMES = {"en": "English", "id": "Bahasa Indonesia", "zh": "中文", "de": "Deutsch", "ja": "日本語", "ru": "Русский"}
SHORT = {"en": "EN", "id": "ID", "zh": "CN", "de": "DE", "ja": "JA", "ru": "RU"}          # what the small buttons say
ALIASES = {"cn": "zh", "zh-cn": "zh", "zh_cn": "zh", "zh-hans": "zh", "jp": "ja", "in": "id", "ind": "id", "eng": "en", "ger": "de", "rus": "ru"}
LYRIC_TARGET = {"en": "en", "id": "id", "zh": "zh-CN", "de": "de", "ja": "ja", "ru": "ru"}   # the code the translation services want
PSEUDO = bool(os.environ.get("ROFPALYS_PSEUDO_LANG"))
_CATS = {}                                                  # code -> {english: translated}   (loaded on first use)
_PAT = {}                                                   # code -> [(compiled regex of an English template, template, translated template)]


def norm(code):
    """'ZH', 'cn', 'zh_CN.UTF-8', 'ru-RU' ... -> one of CODES ('' when it is none of them)."""
    c = str(code or "").strip().lower().replace("_", "-").split(".")[0].split("@")[0]
    if not c:
        return ""
    c = ALIASES.get(c, c)
    if c in CODES:
        return c
    c = ALIASES.get(c.split("-")[0], c.split("-")[0])
    return c if c in CODES else ""


def current():
    """The language in use: the engine's current_lang (the GUI, the TUI and the menu all set that), else ROFPALYS_LANG / the system language, else English."""
    eng = sys.modules.get("rofpalys_engine")
    c = norm(getattr(eng, "current_lang", "")) if eng is not None else ""
    if not c:
        c = norm(os.environ.get("ROFPALYS_LANG") or os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "")
    return c or "en"


def catalog(lg):
    """The dictionary  {English text: translation}  of a language ({} for English or when its file is not installed)."""
    lg = norm(lg) or "en"
    if lg == "en":
        return {}
    if lg not in _CATS:
        try:
            mod = importlib.import_module("rofpalys_i18n_" + lg)
            cat = getattr(mod, "CAT", None)
            _CATS[lg] = cat if isinstance(cat, dict) else {}
        except Exception:
            _CATS[lg] = {}
    return _CATS[lg]


def has(lg):
    return lg == "en" or bool(catalog(lg))


_TOKEN = re.compile(r"(%%|%(?:\(\w+\))?[-+ #0-9.]*[sdif])")


def _template_rx(en):
    """'Sleep timer: %s' -> a regex that recognises it with the value filled in; %d / %f take numbers, %s takes anything; %% is a percent sign."""
    out = []
    for tok in _TOKEN.split(en):
        if tok == "%%":
            out.append("%")
        elif tok.startswith("%"):
            out.append(r"([+\-\u2212]?[0-9][0-9.,]*)" if tok[-1] in "dif" else "(.*?)")
        else:
            out.append(re.escape(tok))
    return re.compile("^" + "".join(out) + "$", re.S)


def _templates(lg):
    """Texts with a number or a name in them ('%d song(s)', 'Sleep timer: %s'): shown with the numbers filled in, so they are matched as patterns."""
    if lg not in _PAT:
        pats = []
        for en, tx in catalog(lg).items():
            if "%" not in en:
                continue
            try:
                pats.append((_template_rx(en), en, tx))
            except re.error:
                continue
        pats.sort(key=lambda p: -len(p[1]))
        _PAT[lg] = pats
    return _PAT[lg]


def tr(text, lg=None, deep=False):
    """English text -> the text in the language in use (or in `lg`). Anything that is not in the catalogue comes back unchanged.
    deep=True (the CyroKayAI report lines): the parts that were filled into a template are translated too ('verified online: %s' inside 'Creator: %s - %s  (%s)')."""
    if not isinstance(text, str) or not text:
        return text
    lg = norm(lg) or current()
    if PSEUDO and lg != "en":
        return "\u27e6" + text + "\u27e7"
    if lg == "en":
        return text
    cat = catalog(lg)
    v = cat.get(text)
    if v:
        return v
    s = text.strip()
    if s and s != text:                                      # '   Library' (the indent belongs to the layout)
        v = tr(s, lg, deep)
        if v != s:
            i = len(text) - len(text.lstrip())
            return text[:i] + v + text[len(text.rstrip()):]
        return text
    if "\n" in text:                                         # a text of several lines: line by line
        return "\n".join(tr(p, lg, deep) if p.strip() else p for p in text.split("\n"))
    for sep in ("  \u2022  ", " \u2022 "):                    # 'Mix  \u2022  7 songs  \u2022  never played': each piece for itself
        if sep in text:
            return sep.join(tr(p, lg, deep) for p in text.split(sep))
    for rx, en, tx in _templates(lg):                        # '3 song(s) added' <- '%d song(s) added'
        m = rx.match(text)
        if m:
            vals = [tr(g, lg, True) if deep else g for g in m.groups()]
            try:
                return tx % tuple(vals)
            except (TypeError, ValueError):
                try:
                    return re.sub(r"%[-+ #0-9.]*[sdif]", lambda _m, it=iter(vals): next(it, ""), tx.replace("%%", "%"))
                except Exception:
                    continue
    return text


def pick(table, lg, key):
    """The old per-file dictionaries  TABLE = {'en': {...}, 'id': {...}}:  the language's own entry when it has one, else the English entry through tr()."""
    lg = norm(lg) or "en"
    own = table.get(lg)
    if own:
        v = own.get(key)
        if v:
            return v
    en = (table.get("en") or {}).get(key)
    if en is None:
        return key
    if lg == "en":
        return en
    if isinstance(en, (tuple, list)):                        # weekday / month names
        return tuple(tr(x, lg) for x in en)
    return tr(en, lg)


def set_current(code):
    """Sets the language in use (the engine keeps the value) -> the code that is now in force."""
    c = norm(code)
    eng = sys.modules.get("rofpalys_engine")
    if c and eng is not None:
        eng.current_lang = c
    return current()


def cycle(step=1):
    c = current()
    i = CODES.index(c) if c in CODES else 0
    return CODES[(i + step) % len(CODES)]


def coverage(lg, english_texts):
    """Which of the English texts the catalogue of `lg` does not translate -> list (for the tests and  rofpalys lang check)."""
    cat = catalog(lg)
    return [t for t in english_texts if t not in cat and t.strip() not in cat]


def placeholders(s):
    return sorted(t for t in _TOKEN.findall(s or "") if t != "%%") + sorted(re.findall(r"\{\w*\}", s or ""))


def check(lg):
    """Problems of one catalogue: a placeholder that differs from the English text, a different number of lines, an empty value -> list of (english, problem)."""
    bad = []
    for en, tx in catalog(lg).items():
        if not isinstance(tx, str) or not tx.strip():
            bad.append((en, "empty"))
        elif placeholders(en) != placeholders(tx):
            bad.append((en, "placeholders %s != %s" % (placeholders(en), placeholders(tx))))
        elif en.count("\n") != tx.count("\n"):
            bad.append((en, "line breaks %d != %d" % (en.count("\n"), tx.count("\n"))))
    return bad


def cli(args=None):
    """rofpalys lang                 the language in use and the six languages (texts in each catalogue)
    rofpalys lang CODE            change it (en id zh de ja ru; cn, jp ... work too): the window and the terminal use it from the next start / at once
    rofpalys lang check [CODE]    every catalogue: placeholders, line breaks, texts the other catalogues have but this one has not
    rofpalys lang test [CODE]     does a lyric translation service answer from here? (needs internet)"""
    args = list(args or [])
    if args[:1] == ["test"]:
        import rofpalys_lyrictrans as LT
        return LT.main(args[1:])
    if args[:1] == ["check"]:
        want = [norm(a) for a in args[1:] if norm(a)] or list(CODES[1:])
        every = set()
        for lg in CODES[1:]:
            every.update(catalog(lg))
        bad = 0
        for lg in want:
            cat = catalog(lg)
            problems = check(lg)
            gaps = sorted(every - set(cat))
            print("%-3s %-17s %4d texts | problems %d | missing (others have it) %d" % (lg, NAMES[lg], len(cat), len(problems), len(gaps)))
            for en, why in problems[:8]:
                print("      %s: %r" % (why, en[:70]))
            for en in gaps[:5]:
                print("      missing: %r" % en[:70])
            bad += len(problems)
        return 1 if bad else 0
    try:
        import rofpalys_engine as E
        E.load_settings()
    except Exception as e:                                   # the engine needs files the catalogues do not: still show what there is
        E = None
        print("(settings not read: %s)" % e)
    if args:
        c = norm(args[0])
        if not c:
            print("Unknown language %r. Choose: %s" % (args[0], ", ".join("%s (%s)" % (k, NAMES[k]) for k in CODES)))
            return 1
        if E is not None:
            E.current_lang = c
            E.save_settings()
        print("Language: %s (%s)  -  %s" % (NAMES[c], SHORT[c], tr("Library", c)))
        return 0
    cur = norm(getattr(E, "current_lang", "")) if E is not None else current()
    for lg in CODES:
        print("%s %-3s %-17s %s" % ("*" if lg == cur else " ", lg, NAMES[lg], ("%d texts" % len(catalog(lg))) if lg != "en" else "(the texts of the program)"))
    print("change: rofpalys lang CODE | check: rofpalys lang check | lyric translation service: rofpalys lang test [CODE]")
    return 0


# END-OF-FILE rofpalys_i18n.py
