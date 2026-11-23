#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - lyric translation: a translation under every lyric line, in the language chosen in Language (EN, ID, CN, DE, JA, RU)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""The lyric lines of a song are translated into the language of the program (Language = CN -> Chinese, RU -> Russian ...) and shown under each original line:

    And dream of perfect man
    梦想成为完美的男人

    res = translate(lines, "zh-CN")          # Result: .lines (one per input line, "" = nothing to show), .status, .service, .detected
    MGR.ensure(lines, target)                # in the background, answers are kept on disk (one small file per song text and language)
    MGR.get(lines, target) / MGR.state(lines, target)

HONEST LIMITS (the screens say it too):
  * It is MACHINE translation. Song lyrics are poetry, slang and wordplay: the result is a help to understand, not a poem.
  * It needs internet and it SENDS the lyric text to the free service: Google Translate's public web endpoint (translate.googleapis.com, the one the Google pages
    use, no key; unofficial, so Google may change or limit it any day) and, when that fails, MyMemory (api.mymemory.translated.net, a small free quota per day).
    Nothing else is sent: no file names, no account, no listening history.
  * Lines that are already in the target language (the service says what it detected), music notes and lines the service leaves unchanged get no translation row.
  * Nothing here needs Tk or curses: the GUI and the terminal player both call it.
Run  python3 rofpalys_lyrictrans.py zh  to check from your own phone that a service answers."""
import hashlib
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import rofpalys_i18n as I18N
import rofpalys_library as lib

__version__ = "1.0"
DIR = os.path.join(lib.CACHE_DIR, "lyrtrans")
UA = "Mozilla/5.0 (X11; Linux) Rofpalys/5.11"
GOOGLE = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=%s&dt=t&q=%s"
MYMEMORY = "https://api.mymemory.translated.net/get?q=%s&langpair=%s"
MAX_Q = 1400                                          # characters of one request's text after URL-encoding (a GET url must stay short)
TIMEOUT = 8.0
RETRY_AFTER = 90.0                                    # a failed translation of the same lyrics is tried again only after this many seconds
KEEP_FILES = 400


class TransError(Exception):
    """kind: 'net' (nothing answered), 'bad' (an answer that could not be read), 'quota'."""

    def __init__(self, kind, text=""):
        Exception.__init__(self, "%s %s" % (kind, text))
        self.kind = kind


class Result:
    __slots__ = ("lines", "status", "service", "detected", "target")

    def __init__(self, lines, status, service="", detected="", target=""):
        self.lines, self.status, self.service, self.detected, self.target = lines, status, service, detected, target

    def shown(self):
        return sum(1 for x in self.lines if x)


# ------------------------------------------------------------------ small helpers
def target_code(lang=None):
    """The code the services want for a program language ('zh' -> 'zh-CN')."""
    return I18N.LYRIC_TARGET.get(I18N.norm(lang) or I18N.current(), "en")


def translatable(s):
    """A lyric line that has words in it (not '', not a music note, not only symbols)."""
    return bool(s) and any(ch.isalpha() for ch in s)


def _script(ch):
    try:
        n = unicodedata.name(ch)
    except ValueError:
        return ""
    if n.startswith(("CJK", "IDEOGRAPHIC")):
        return "han"
    if n.startswith(("HIRAGANA", "KATAKANA")):
        return "kana"
    if n.startswith("HANGUL"):
        return "hangul"
    if n.startswith("CYRILLIC"):
        return "cyrillic"
    if n.startswith("LATIN"):
        return "latin"
    return "other"


def scripts(lines):
    """{'latin': share, 'han': share ...} of the letters of the lyrics."""
    cnt, tot = {}, 0
    for s in lines:
        for ch in s:
            if ch.isalpha():
                k = _script(ch)
                cnt[k] = cnt.get(k, 0) + 1
                tot += 1
    return {k: v / tot for k, v in cnt.items()} if tot else {}


def already_target(lines, target):
    """True when the lyrics are plainly in the target language already (checked on the letters alone, nothing is sent). Latin languages can not be told apart
    like this (English / Indonesian / German): there the service's own language detection decides."""
    sc = scripts(lines)
    if not sc:
        return False
    t = target.split("-")[0].lower()
    if t == "zh":
        return sc.get("han", 0) >= 0.6 and sc.get("kana", 0) < 0.05
    if t == "ja":
        return (sc.get("kana", 0) + sc.get("han", 0)) >= 0.6 and sc.get("kana", 0) >= 0.1
    if t == "ru":
        return sc.get("cyrillic", 0) >= 0.6
    return False


def _same_lang(detected, target):
    d, t = (detected or "").lower().replace("_", "-"), target.lower()
    return bool(d) and d.split("-")[0] == t.split("-")[0] and (d.split("-")[0] != "zh" or d in ("zh", "zh-cn", "zh-hans") or t in ("zh", "zh-cn", "zh-hans"))


def _http(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise TransError("quota" if e.code in (429, 403) else "net", "HTTP %s" % e.code)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise TransError("net", repr(e)[:80])


# ------------------------------------------------------------------ the services
def google(texts, target, http=None):
    """texts (no blank, no line break inside) -> ([translation of each], detected source language). One request; TransError when the line count does not match."""
    http = http or _http
    q = "\n".join(texts)
    raw = http(GOOGLE % (urllib.parse.quote(target), urllib.parse.quote(q, safe="")))
    try:
        data = json.loads(raw)
        segs = data[0] or []
        out = "".join(sg[0] for sg in segs if sg and isinstance(sg[0], str))
        det = data[2] if len(data) > 2 and isinstance(data[2], str) else ""
    except (ValueError, IndexError, TypeError, KeyError):
        raise TransError("bad", "google answer")
    parts = [p.strip() for p in out.replace("\r", "").split("\n")]
    while parts and not parts[-1]:
        parts.pop()
    if len(parts) != len(texts):
        raise TransError("bad", "line count %d != %d" % (len(parts), len(texts)))
    return parts, det


def mymemory(text, target, http=None):
    """One line -> its translation (MyMemory: 500 characters per request, the source language is guessed by the service)."""
    http = http or _http
    raw = http(MYMEMORY % (urllib.parse.quote(text[:480], safe=""), urllib.parse.quote("Autodetect|" + target, safe="")))
    try:
        data = json.loads(raw)
        st = int(data.get("responseStatus", 200))
        tx = (data.get("responseData") or {}).get("translatedText") or ""
    except (ValueError, TypeError, AttributeError):
        raise TransError("bad", "mymemory answer")
    if st == 429 or "MYMEMORY WARNING" in tx.upper():
        raise TransError("quota", "mymemory")
    if st != 200 or not tx:
        raise TransError("bad", "mymemory status %s" % st)
    return tx.strip()


def _chunks(texts):
    """Lines grouped so that one request stays short."""
    cur, size, out = [], 0, []
    for t in texts:
        n = len(urllib.parse.quote(t, safe="")) + 3
        if cur and size + n > MAX_Q:
            out.append(cur)
            cur, size = [], 0
        cur.append(t)
        size += n
    if cur:
        out.append(cur)
    return out


def translate(lines, target, http=None, stop=None, progress=None):
    """Translate the lyric lines -> Result. Result.lines has one entry per input line ('' = no row: blank, note, or the service left it as it was).
    status: 'ok' | 'same' (the lyrics are already in the target language) | 'none' (no words in them) | 'net' (no service answered) | 'quota'."""
    lines = [str(x or "").strip() for x in lines]
    out = [""] * len(lines)
    idx = [i for i, s in enumerate(lines) if translatable(s)]
    if not idx:
        return Result(out, "none", target=target)
    uniq = list(dict.fromkeys(lines[i] for i in idx))              # a chorus that is sung five times is sent once
    if already_target([lines[i] for i in idx], target):
        return Result(out, "same", detected=target, target=target)
    done, det, svc, errs = {}, "", "", []
    alive = {"g": True, "m": True}                                   # a service that did not answer (network, quota) is not asked again in this run
    stopped = lambda: bool(stop and stop())                         # noqa: E731

    def via_google(group):
        nonlocal det, svc
        try:
            tr, d = google(group, target, http)
        except TransError as e:
            errs.append(e)
            if e.kind in ("net", "quota"):
                alive["g"] = False
            raise
        det, svc = det or d, svc or "google"
        for a, b in zip(group, tr):
            done[a] = b

    def via_mymemory(t):
        nonlocal svc
        try:
            done[t] = mymemory(t, target, http)
        except TransError as e:
            errs.append(e)
            if e.kind in ("net", "quota"):
                alive["m"] = False
            return
        svc = svc or "mymemory"

    def run(group):
        if stopped() or not (alive["g"] or alive["m"]):
            return
        if alive["g"]:
            try:
                via_google(group)
                return
            except TransError as e:
                if e.kind == "bad" and len(group) > 1:               # the service merged or split lines: smaller groups keep them apart
                    h = (len(group) + 1) // 2
                    run(group[:h])
                    run(group[h:])
                    return
        for t in group:                                              # google is out of reach or gave nothing usable for this line: the backup, line by line
            if stopped() or not alive["m"]:
                return
            via_mymemory(t)

    total = len(uniq)
    first = True
    for grp in _chunks(uniq):
        if stopped() or not (alive["g"] or alive["m"]):
            break
        run(grp)
        if first:
            first = False
            if det and _same_lang(det, target):                      # google says: this is already the language asked for
                return Result(out, "same", "google", det, target)
        if progress:
            try:
                progress(min(1.0, len(done) / max(1, total)))
            except Exception:
                pass
    if not done and errs and all(e.kind in ("net", "quota") for e in errs):
        return Result(out, "quota" if any(e.kind == "quota" for e in errs) else "net", target=target)
    for i in idx:
        t = done.get(lines[i], "")
        if t and t.strip().lower() != lines[i].strip().lower():
            out[i] = t
    if not any(out):
        return Result(out, "net" if not done else "ok", svc, det, target)
    return Result(out, "ok", svc, det, target)


# ------------------------------------------------------------------ the disk cache (one small file per lyric text and language)
def _key(lines, target):
    h = hashlib.sha1(("\n".join(str(x or "").strip() for x in lines) + "\x00" + target).encode("utf-8", "replace")).hexdigest()[:24]
    return h


def cache_path(lines, target):
    return os.path.join(DIR, "%s_%s.json" % (_key(lines, target), target))


def cache_load(lines, target):
    try:
        with open(cache_path(lines, target), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d.get("lines"), list) and len(d["lines"]) == len(lines):
            return Result([str(x or "") for x in d["lines"]], d.get("status", "ok"), d.get("service", ""), d.get("detected", ""), target)
    except (OSError, ValueError, AttributeError):
        pass
    return None


def cache_save(lines, target, res):
    try:
        os.makedirs(DIR, exist_ok=True)
        p = cache_path(lines, target)
        tmp = p + ".part"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"target": target, "status": res.status, "service": res.service, "detected": res.detected, "at": int(time.time()), "lines": res.lines}, f, ensure_ascii=False)
        os.replace(tmp, p)
        names = sorted((os.path.join(DIR, n) for n in os.listdir(DIR) if n.endswith(".json")), key=lambda x: os.path.getmtime(x))
        for old in names[:-KEEP_FILES]:
            try:
                os.remove(old)
            except OSError:
                pass
    except OSError:
        pass


def clear_cache():
    n = 0
    try:
        for name in os.listdir(DIR):
            if name.endswith((".json", ".part")):
                os.remove(os.path.join(DIR, name))
                n += 1
    except OSError:
        pass
    MGR.forget()
    return n


# ------------------------------------------------------------------ the manager: ask for a translation, look again later
class Manager:
    """ensure() starts one background job per (lyrics, language); get() answers from memory / disk without waiting; state() is what the screen shows:
    'ready' | 'busy' | 'same' | 'none' | 'net' | 'quota' | 'idle' (nothing asked yet)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.res = {}                                    # key -> Result
        self.busy = {}                                   # key -> progress 0..1
        self.failed = {}                                 # key -> (time, status)
        self.miss = {}                                   # key -> time of a look at the disk that found nothing (the screens ask many times a second)
        self.http = None                                 # tests give a fake network here

    def _k(self, lines, target):
        return (_key(lines, target), target)

    def forget(self):
        with self.lock:
            self.res.clear()
            self.failed.clear()
            self.miss.clear()

    def get(self, lines, target):
        """The translation when it is ready (memory or disk), else None. A 'same' / 'none' answer is a Result with no rows."""
        k = self._k(lines, target)
        with self.lock:
            r = self.res.get(k)
            if r is None and time.time() - self.miss.get(k, 0.0) < 3.0:
                return None
        if r is None:
            r = cache_load(lines, target)
            with self.lock:
                if r is not None:
                    self.res[k] = r
                else:
                    self.miss[k] = time.time()
        return r

    def state(self, lines, target):
        r = self.get(lines, target)
        k = self._k(lines, target)
        if r is not None:
            return "ready" if r.status == "ok" else r.status
        with self.lock:
            if k in self.busy:
                return "busy"
            f = self.failed.get(k)
        if f and time.time() - f[0] < RETRY_AFTER:
            return f[1]
        return "idle"

    def progress(self, lines, target):
        with self.lock:
            return self.busy.get(self._k(lines, target), 0.0)

    def ensure(self, lines, target, stop=None):
        """Start translating when nothing is known yet -> the state."""
        lines = [str(x or "").strip() for x in lines]
        st = self.state(lines, target)
        if st != "idle":
            return st
        if not any(translatable(s) for s in lines):
            return "none"
        k = self._k(lines, target)
        with self.lock:
            if k in self.busy:
                return "busy"
            self.busy[k] = 0.0

        def prog(p, k=k):
            with self.lock:
                if k in self.busy:
                    self.busy[k] = p

        def work():
            try:
                res = translate(lines, target, self.http, stop, prog)
            except Exception as e:                       # a translation must never break the player
                res = Result([""] * len(lines), "net", target=target)
                _log("translate: %r" % (e,))
            if res.status in ("ok", "same"):                 # on disk first: "ready" always means the next start needs no network
                cache_save(lines, target, res)
            with self.lock:
                self.busy.pop(k, None)
                self.miss.pop(k, None)
                if res.status in ("ok", "same", "none"):
                    self.res[k] = res
                    self.failed.pop(k, None)
                else:
                    self.failed[k] = (time.time(), res.status)

        threading.Thread(target=work, daemon=True, name="rofpalys-lyrictrans").start()
        return "busy"


def _log(msg):
    try:
        lib.log(msg)
    except Exception:
        pass


MGR = Manager()


def rows_for(lines, lang=None):
    """The translations to show under `lines` in the program language -> (list aligned with lines or None, state). Starts the background job when needed.
    The caller shows the rows when state == 'ready' and asks again a little later while it is 'busy'."""
    target = target_code(lang)
    lines = [str(x or "").strip() for x in lines]
    st = MGR.ensure(lines, target)
    r = MGR.get(lines, target)
    if r is not None and r.status == "ok":
        return r.lines, "ready"
    return None, st


def main(argv=None):
    """python3 rofpalys_lyrictrans.py zh  [text ...]: does a service answer from here?"""
    argv = list(sys.argv[1:] if argv is None else argv)
    lang = argv.pop(0) if argv else I18N.current()
    target = target_code(lang)
    lines = argv or ["And dream of perfect man", "Hello, how are you today?"]
    r = translate(lines, target)
    print("target %s | status %s | service %s | detected %s" % (target, r.status, r.service or "-", r.detected or "-"))
    for a, b in zip(lines, r.lines):
        print("  %s\n  %s" % (a, b or "(no translation row)"))
    return 0 if r.status in ("ok", "same") else 1


if __name__ == "__main__":
    sys.exit(main())

# END-OF-FILE rofpalys_lyrictrans.py
