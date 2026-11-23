#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Smart Mixes (playlists that make themselves from how you listen)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""A new tab "Mix" in the library with playlists that Rofpalys builds from your own listening history and keeps up to date by itself:

  Heavy rotation       what you played most in the last 14 days
  On repeat            songs you played three times or more this week
  Forgotten favorites  songs you loved (many plays, or a favourite) and have not heard for 6 weeks
  Fresh finds          songs in your library that you never played, the newest files first
  Night mix            what you play late at night (22:00 - 05:00)
  Morning mix          what you play in the morning (05:00 - 11:00)
  Daily mix            a new mix every day: songs of the artists you play most, with a few you have not heard yet
  All-time top         your 50 most played songs ever

A mix opens like a folder (play, shuffle, queue, favourite ... all work) and is also found by the search field and the command palette (Ctrl+K). A mix with fewer than
three songs is not shown. The numbers come from rofpalys_analytics.py (the history Rofpalys keeps of your listening); without it the mixes still work from the play counts
in stats.json (All-time top and Fresh finds)."""
import random
import time

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    import rofpalys_insight as IN
except Exception:
    IN = None
try:
    import rofpalys_analytics as AN
except Exception:
    AN = None

FEATURE = {"name": "mixes", "title": "Smart Mixes: playlists made from your listening", "version": "1.0", "order": 30, "enabled": True}
CHIP = "smartmix"
MIN_SONGS, MAX_SONGS = 3, 60
FORGOTTEN_DAYS = 42
REFRESH_S = 120.0

TEXTS = {
    "en": dict(smartmix_chip="Mix", sm_heavy="Heavy rotation", sm_repeat="On repeat", sm_forgot="Forgotten favorites", sm_fresh="Fresh finds", sm_night="Night mix",
               sm_morning="Morning mix", sm_daily="Daily mix", sm_top="All-time top",
               sm_heavy_s="last 14 days", sm_repeat_s="this week", sm_forgot_s="not played for 6 weeks", sm_fresh_s="never played", sm_night_s="22:00 - 05:00",
               sm_morning_s="05:00 - 11:00", sm_daily_s="new every day", sm_top_s="most played ever",
               sm_intro="Playlists that build themselves from what you play", sm_empty="Play some songs and your mixes appear here. They update by themselves.",
               sm_refresh="Update mixes"),
    "id": dict(smartmix_chip="Mix", sm_heavy="Sering diputar", sm_repeat="Diulang terus", sm_forgot="Favorit yang terlupa", sm_fresh="Temuan baru", sm_night="Mix malam",
               sm_morning="Mix pagi", sm_daily="Mix harian", sm_top="Terbanyak sepanjang masa",
               sm_heavy_s="14 hari terakhir", sm_repeat_s="minggu ini", sm_forgot_s="belum diputar 6 minggu", sm_fresh_s="belum pernah diputar", sm_night_s="22.00 - 05.00",
               sm_morning_s="05.00 - 11.00", sm_daily_s="baru setiap hari", sm_top_s="paling sering diputar",
               sm_intro="Playlist yang dibuat sendiri dari lagu yang kamu putar", sm_empty="Putar beberapa lagu, lalu mix-mu muncul di sini. Isinya diperbarui otomatis.",
               sm_refresh="Perbarui mix"),
}


def build(songs, cfg_stats, favorites, mtimes, v=None, now=None, day_seed=None):
    """The mixes as [(key, [paths])] in the order they are shown. Pure: everything comes in as arguments (v = a View of the history or None), so it can be tested without a window.
    Never raises; a mix that cannot be made is left out."""
    songs = list(songs or [])
    have = set(songs)
    stats = cfg_stats or {}
    favorites = favorites or set()
    out = []
    now = time.time() if now is None else now

    def keep(paths):
        seen, res = set(), []
        for p in paths:
            if p in have and p not in seen:
                seen.add(p)
                res.append(p)
            if len(res) >= MAX_SONGS:
                break
        return res

    def add(key, paths):
        paths = keep(paths)
        if len(paths) >= MIN_SONGS:
            out.append((key, paths))

    today = None
    rows14 = rows7 = rows_all = []
    if v is not None and IN is not None:
        try:
            today = IN.today(v)
            rows14 = IN.rank_days(v, today - 13, today)
            rows7 = IN.rank_days(v, today - 6, today)
            first = IN.all_span(v)[0]
            rows_all = IN.rank_days(v, first, today)
        except Exception:
            rows14 = rows7 = rows_all = []
    played_hist = {r["name"] for r in rows_all}
    cfg_plays = {p: int((stats.get(p) or {}).get("plays", 0) or 0) for p in songs}

    add("heavy", [r["name"] for r in rows14 if r["plays"] >= 2] or [r["name"] for r in rows14])
    add("repeat", [r["name"] for r in rows7 if r["plays"] >= 3])
    forgotten = []
    if v is not None and IN is not None and rows_all and today is not None:
        cutoff_ms = (now - FORGOTTEN_DAYS * 86400) * 1000.0
        recent = {r["name"] for r in IN.rank_days(v, today - FORGOTTEN_DAYS + 1, today)}
        last_of = {r["name"]: r["last"] for r in rows_all}
        plays_of = {r["name"]: r["plays"] for r in rows_all}
        for p in songs:
            n = max(plays_of.get(p, 0), cfg_plays.get(p, 0))
            fav = p in favorites
            if (n < 3 and not fav) or p in recent:
                continue
            last = last_of.get(p, 0)
            if not last or last < cutoff_ms:                      # loved, and not played for six weeks (or never since the history began)
                forgotten.append((n + (3 if fav else 0), p))
    forgotten.sort(key=lambda x: -x[0])
    add("forgot", [p for _n, p in forgotten])
    fresh = [p for p in songs if cfg_plays.get(p, 0) == 0 and p not in played_hist]
    fresh.sort(key=lambda p: -float((mtimes or {}).get(p, 0) or 0))
    add("fresh", fresh)
    if v is not None and IN is not None:
        try:
            min_t = (now - 60 * 86400) * 1000.0                    # only what you played in the last two months says what your nights sound like
            plays = [r for r in IN.recent_plays(v, 300) if r[0] >= min_t]
            for key, hours in (("night", set([22, 23, 0, 1, 2, 3, 4])), ("morning", set([5, 6, 7, 8, 9, 10]))):
                cnt = {}
                for row in plays:
                    if IN.hour_of(row[0], row[1]) in hours and row[3] >= 30 and row[2] in have:
                        cnt[row[2]] = cnt.get(row[2], 0) + 1
                add(key, [p for p, _n in sorted(cnt.items(), key=lambda kv: -kv[1])])
        except Exception:
            pass
    # the daily mix: the songs of the artists you play most, a few that were never played, shuffled with the date as the seed (the same all day, new tomorrow)
    try:
        seed = day_seed if day_seed is not None else (today if today is not None else int(now // 86400))
        rnd = random.Random(seed * 7919 + 17)
        top_artists = []
        if v is not None and IN is not None and today is not None:
            top_artists = [str(r["name"]).strip().lower() for r in IN.rank_days(v, today - 90, today, level="artist", n=6)]
        pool = []
        if top_artists:
            by_artist = {}
            for p in songs:
                by_artist.setdefault(_artist_of(p).strip().lower(), []).append(p)
            for a in top_artists:
                pool += by_artist.get(a, [])
        if not pool:
            pool = sorted(songs, key=lambda p: -cfg_plays.get(p, 0))[:40]
        unheard = [p for p in fresh]
        rnd.shuffle(pool)
        rnd.shuffle(unheard)
        mix = pool[:22] + unheard[:8]
        rnd.shuffle(mix)
        add("daily", mix)
    except Exception:
        pass
    top = [r["name"] for r in rows_all[:50]] if rows_all else [p for p, n in sorted(cfg_plays.items(), key=lambda kv: -kv[1]) if n > 0][:50]
    add("top", top)
    return out


def _artist_of(path):
    try:
        a, _t = M.name_meta(path)
        if a:
            return a
    except Exception:
        pass
    return os.path.basename(path).split(" - ")[0]


class Mixin:
    def sm_texts(self, key):
        return self.T("sm_" + key), self.T("sm_" + key + "_s")

    def sm_compute(self):
        v = IN.view() if IN is not None else None
        try:
            return build(E.songs_all, (getattr(self, "cfg", None) or {}).get("stats", {}), E.favorites, E.library_mtimes, v)
        except Exception as e:
            log("mixes: %r" % (e,))
            return []

    def sm_groups(self):
        """The group provider: the mixes as folders-like groups (they are rebuilt with the library, and every two minutes when what you play changed them)."""
        if self.sm_cache is None or time.time() - self.sm_cache_t > 60.0:
            self.sm_cache, self.sm_cache_t = self.sm_compute(), time.time()
        groups = []
        for key, paths in self.sm_cache:
            name, sub = self.sm_texts(key)
            groups.append({"id": "sm:" + key, "kind": "mix", "name": name, "sub": sub, "paths": list(paths)})
        return groups

    def sm_items(self):
        """The rows of the Mix tab."""
        T = self.T
        gs = [g for g in self.extra_groups if g["id"].startswith("sm:")]
        if not gs:
            return [self.header_item(T("sm_intro")), self.header_item(T("sm_empty"))]
        return [self.header_item(T("sm_intro"))] + [self.group_item(g) for g in gs]

    def sm_refresh(self, force=False):
        """Recomputes the mixes; when they changed the groups are rebuilt (and the Mix tab redrawn when it is the page in view and nobody is searching)."""
        if getattr(self, "_rebuilding", False):
            return
        new = self.sm_compute()
        sig = [(k, tuple(p)) for k, p in new]
        old = [(k, tuple(p)) for k, p in (self.sm_cache or [])]
        self.sm_cache, self.sm_cache_t = new, time.time()
        if sig == old and not force:
            return
        try:
            self.rebuild_groups()
            if self.view == "library" and self.chip == CHIP and not self.group and not self.query():
                self.apply_filter()
        except Exception as e:
            log("mixes refresh: %r" % (e,))

    def sm_poll(self):
        if time.time() < self.sm_next:
            return
        self.sm_next = time.time() + REFRESH_S
        self.sm_ready = True
        self.sm_refresh()


def register(app):
    app.sm_cache, app.sm_cache_t, app.sm_next, app.sm_ready = None, 0.0, time.time() + 25.0, False
    app.add_texts(**TEXTS)
    app.add_group_provider(lambda a: a.sm_groups())
    app.add_chip(35, CHIP, "smartmix_chip", lambda a: a.sm_items())
    app.add_poll(lambda a: a.sm_poll())
    app.add_build(lambda a: a.root.after(1500, lambda: setattr(a, "sm_ready", True)))     # a language change renames the mixes once the window has settled
    app.add_relabel(lambda a: a.sm_refresh(force=True) if a.sm_ready else None)      # the names follow a language change
    app.add_menu("sm_refresh", lambda a: a.sm_refresh(force=True))


# END-OF-FILE rofpalys_gui_mixes.py
