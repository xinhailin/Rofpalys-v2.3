#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - reading helpers for the features that look at the listening history (Smart Mixes, Rewind, Goals)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""No window and no Tk in here: small, tested questions asked of rofpalys_analytics (the recorder and its log). Every function answers with plain lists and dicts
and never raises - when there is no history yet, the answer is simply empty.

  view()                       a View of the running recorder (always fresh) or, in another program, of the files (kept a few seconds)
  rank_days(v, a, b, ...)      the ranking of songs / artists / folders over the day numbers a..b
  day_numbers(date)            the day number (0 = 1970-01-01) of a datetime.date, and back with day_date(n)
  month_span(year, month)      (first day number, last day number) of a calendar month; year_span(year) the same for a year
  listen_days(v, a, b)         one row per day: {"i", "key", "wd", "listen", "open", "starts", "plays", "spotify", "top"}
  new_in_period(v, a, b)       the songs first played in those days
  recent_plays(v, n)           the latest finished plays [t_ms, utc_offset_min, path, listened_s, why, tier, reach]
  hour_of(t_ms, z)             the local hour of a play
  all_span(v)                  (first day with history, today)
  now_ms(v) / today(v)         the clock of the View and its local day number"""
import datetime as _dt
import threading
import time

try:
    import rofpalys_analytics as AN
    import rofpalys_analytics_calc as C
except Exception:
    AN = C = None

_EPOCH = _dt.date(1970, 1, 1).toordinal()
_LOCK = threading.Lock()
_CACHE = {"v": None, "t": 0.0}


def available():
    return AN is not None and C is not None


def view(max_age=15.0):
    """A View of the running recorder, or of the files (re-read at most every max_age seconds). None when the analytics files are not installed."""
    if not available():
        return None
    try:
        rec = AN.recorder()
        if rec is not None and rec.state == "running":
            return rec.view()
        with _LOCK:
            if _CACHE["v"] is None or time.time() - _CACHE["t"] > max_age:
                _CACHE["v"], _CACHE["t"] = AN.View(None), time.time()
            return _CACHE["v"]
    except Exception:
        return None


def forget():
    """The next view() reads the files again (after something was written)."""
    with _LOCK:
        _CACHE["v"] = None


def day_numbers(d):
    return d.toordinal() - _EPOCH


def day_date(n):
    return _dt.date.fromordinal(int(n) + _EPOCH)


def month_span(year, month):
    a = _dt.date(year, month, 1)
    b = _dt.date(year + (month == 12), (month % 12) + 1, 1) - _dt.timedelta(days=1)
    return day_numbers(a), day_numbers(b)


def year_span(year):
    return day_numbers(_dt.date(year, 1, 1)), day_numbers(_dt.date(year, 12, 31))


def all_span(v):
    """(first day number with any history, today) - (today, today) when there is none."""
    try:
        return v.span("all")
    except Exception:
        t = today(v)
        return t, t


def now_ms(v):
    try:
        return int(v.now_ms())
    except Exception:
        return int(time.time() * 1000)


def today(v):
    try:
        return int(v.today())
    except Exception:
        return day_numbers(_dt.date.today())


def hour_of(t_ms, z=0):
    return C.hour_of(t_ms, z) if C is not None else int(time.localtime(t_ms / 1000.0).tm_hour)


def rank_days(v, a, b, level="song", by="plays", rule="lastfm", n=0):
    """Rows of rofpalys_analytics_calc.rank over the day numbers a..b (see there); [] when anything is missing."""
    if v is None or C is None or b < a:
        return []
    try:
        return v._run(lambda ag, ov: C.rank(ag, int(a), int(b), by, level, rule, n, ov))
    except Exception:
        return []


def listen_days(v, a, b):
    if v is None or C is None or b < a:
        return []
    try:
        return v._run(lambda ag, ov: C.series(ag, int(a), int(b), ov))
    except Exception:
        return []


def totals_days(v, a, b):
    """C.totals over the days a..b: listen / open / starts / lastfm / songs / artists / hours[24] / active_days ..."""
    if v is None or C is None or b < a:
        return {}
    try:
        return v._run(lambda ag, ov: C.totals(ag, int(a), int(b), ov))
    except Exception:
        return {}


def streaks_days(v):
    """{"current", "longest", "longest_from", "longest_to", "active_days"} of the whole history."""
    if v is None or C is None:
        return {}
    try:
        t = today(v)
        return v._run(lambda ag, ov: C.streaks(ag, t, ov))
    except Exception:
        return {}


def recent_plays(v, n=300):
    if v is None:
        return []
    try:
        return v.plays(n)
    except Exception:
        return []


def new_in_period(v, a, b):
    """The songs whose FIRST play in the history falls on the day numbers a..b (what you discovered in that time)."""
    if v is None or C is None or b < a:
        return []
    try:
        z = v.z()

        def f(ag, ov):
            out = []
            for path, m in ag.songs.items():
                fi = int(m.get("first", 0) or 0)
                if fi and a <= C.day_index(fi, z) <= b:
                    out.append(path)
            return out
        return v._run(f)
    except Exception:
        return []


def song_meta(v, path):
    """(title, artist) as the history knows them ('' when unknown)."""
    try:
        t, a = v.title(path)
        return t or "", a or ""
    except Exception:
        return "", ""


def day_listen_seconds(v, day):
    """Seconds listened on one day number (today included, live)."""
    rows = listen_days(v, day, day)
    return float(rows[0]["listen"]) if rows else 0.0


# END-OF-FILE rofpalys_insight.py
