#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: the Home page (banner, quick access, shelves of cards, playlists, top artists, footer) in three layouts; the canvas of all library pages
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""The Home tab of the library is a page of cards instead of a list. Three layouts (Settings > Display / key F8):
  dash   Dashboard: banner + Now Playing card, Quick Access tiles, Recently Played cards next to Top Artists
  show   Showcase : big banner, Recently Played cards, Your Playlists tiles
  list   List     : the plain list of the older versions (nothing here is drawn)
Colours, corner shapes (square / rounded / cut), neon lines and type come from the look in use (Classic / Modern / Cyberpunk), so a look switch changes this page too.
The page is ONE canvas (scrolls with the wheel or by dragging); the real data of the library is shown: recent songs, covers, artists, playlists, play counts.
The same canvas also carries the other pages of the library (Songs, Mix, Artists, Playlists as cards; the page of a playlist / artist / Favorites): they are drawn by
rofpalys_gui_browse.py, this file gives them the canvas, the scrolling, the hover and the clicks.
A feature file plugs into the window with register(app) and brings its methods in the Mixin class (see rofpalys_gui_template.py)."""
import math
import os
import random
import time
import zlib

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    from tkinter import font as tkfont
except Exception:
    tkfont = None

try:
    import rofpalys_theme as TH
except Exception:
    TH = None

FEATURE = {"name": "home", "title": "Home page: banner, quick access, recently played, playlists, artists (3 layouts)", "version": "1.0", "order": 14, "enabled": True}
LAYOUTS = ("dash", "show", "list")
COVER_BUCKETS = (96, 112, 136, 160, 184, 208)
_TXT = {
    "en": dict(hm_layout="Layout", hm_l_dash="Dashboard", hm_l_show="Showcase", hm_l_list="List",
               hm_d_dash="Banner, Now Playing card, quick access, recent songs and top artists",
               hm_d_show="A big banner, recent songs and your playlists", hm_d_list="The plain list of songs (the older look)",
               hm_welcome="Welcome to", hm_tagline="Enjoy your favorite music anytime, anywhere.", hm_play_now="Play Now", hm_quick="Quick Access",
               hm_q_play="Play Your Music", hm_q_play_s="Start listening now", hm_q_liked="Liked Songs", hm_q_liked_s="Your favorite tracks",
               hm_q_list="Your Playlist", hm_q_list_s="Create & manage", hm_q_top="Top Charts", hm_q_top_s="Most played",
               hm_see_all="See All", hm_playlists="Your Playlists", hm_artists="Top Artists", hm_empty="No songs yet. Put music in your Termux folders (for example ~/Music) or add a folder in Settings.",
               hm_nothing="Nothing playing", hm_layout_now="Layout: %s"),
    "id": dict(hm_layout="Tata letak", hm_l_dash="Dasbor", hm_l_show="Etalase", hm_l_list="Daftar",
               hm_d_dash="Banner, kartu Sedang Diputar, akses cepat, lagu terakhir dan artis teratas",
               hm_d_show="Banner besar, lagu terakhir dan playlist kamu", hm_d_list="Daftar lagu biasa (tampilan lama)",
               hm_welcome="Selamat datang di", hm_tagline="Nikmati musik favoritmu kapan saja, di mana saja.", hm_play_now="Putar Sekarang", hm_quick="Akses Cepat",
               hm_q_play="Putar Musikmu", hm_q_play_s="Mulai mendengarkan", hm_q_liked="Lagu Disukai", hm_q_liked_s="Lagu favoritmu",
               hm_q_list="Playlist Kamu", hm_q_list_s="Buat & kelola", hm_q_top="Tangga Lagu", hm_q_top_s="Paling sering diputar",
               hm_see_all="Lihat Semua", hm_playlists="Playlist Kamu", hm_artists="Artis Teratas", hm_empty="Belum ada lagu. Taruh musik di folder Termux (misalnya ~/Music) atau tambahkan folder di Pengaturan.",
               hm_nothing="Tidak ada yang diputar", hm_layout_now="Tata letak: %s"),
}


def _arc(cx, cy, r, a0, a1, step=12):
    """Points of an arc (degrees, y up) as screen coordinates."""
    pts, a = [], a0
    n = max(1, int(abs(a1 - a0) // step))
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / float(n)
        pts += [cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a))]
    return pts


class Mixin:
    # ------------------------------------------------------------------ state
    def hm_layout(self):
        v = self.cfg.get("layout", "dash")
        return v if v in LAYOUTS else "dash"

    def hm_t(self, k):
        return I18N.pick(_TXT, E.current_lang, k)

    def hm_active(self):
        return bool(getattr(self, "pg_kind", None) and self.pg_kind())

    def set_layout(self, name):
        if name not in LAYOUTS or name == self.hm_layout():
            return
        self.cfg["layout"] = name
        self.save_cfg()
        self.apply_filter()
        self.msg(self.hm_t("hm_layout_now") % self.hm_t("hm_l_" + name))

    def cycle_layout(self, _e=None):
        if self.typing():
            return
        self.set_layout(LAYOUTS[(LAYOUTS.index(self.hm_layout()) + 1) % len(LAYOUTS)])

    def home_sync(self):
        """apply_filter calls this: the page of cards takes the place of the list while it is on. True = the page is shown (the list stays empty)."""
        cv = getattr(self, "hm_cv", None)
        if cv is None:
            return False
        on = self.hm_active()
        if on and not self._hm_on:
            self.head_frame.pack_forget()
            self.rows.frame.pack_forget()
            cv.pack(fill="both", expand=True)
            self._hm_on = True
        elif not on and self._hm_on:
            cv.pack_forget()
            self.head_frame.pack(fill="x", padx=18, pady=(4, 4))
            self.rows.frame.pack(fill="both", expand=True, padx=(8, 4), pady=(0, 6))
            self._hm_on = False
        if on:
            self._hm_sig = None
            self.root.after_idle(self.hm_draw)
        return on

    # ------------------------------------------------------------------ data
    def hm_data(self):
        st = self.cfg["stats"]
        secs = dict(L.home_sections(E.songs_all, st, E.favorites, E.library_mtimes, self.cfg["last"].get("song")))
        for key in ("recent", "new", "discover"):
            if secs.get(key):
                recent, rkey = secs[key], key
                break
        else:
            recent, rkey = [], "recent"
        playlists = [g for g in self.extra_groups if g.get("kind") == "playlist"]

        def plays(g):
            return sum(st.get(p, {}).get("plays", 0) for p in g["paths"])
        artists = sorted(self.artists, key=lambda g: (-plays(g), -len(g["paths"]), g["name"].lower()))[:6]
        top = [st[p].get("plays", 0) for p in sorted((p for p in st if st[p].get("plays")), key=lambda p: -st[p].get("plays", 0))[:6]]
        shown = set(recent)
        sug = [p for p in secs.get("mix", []) if p not in shown]
        for p in secs.get("discover", []):
            if p not in shown and p not in sug:
                sug.append(p)
        mixes = [g for g in self.extra_groups if g.get("kind") == "mix"] + list(self.mixes)
        return {"recent": recent, "rkey": rkey, "playlists": playlists, "artists": artists, "top": top, "favs": len([p for p in E.songs_all if p in E.favorites]),
                "mixes": mixes, "suggest": sug, "most": secs.get("top", []), "added": secs.get("new", []) if rkey != "new" else []}

    # ------------------------------------------------------------------ small drawing helpers
    def hm_hit(self, x1, y1, x2, y2, act, item=None, shape=None, r=None, tag="", hover=None):
        self.hm_hits.append(dict(x1=x1, y1=y1, x2=x2, y2=y2, act=act, item=item, shape=shape or STYLE["shape"], r=r, tag=tag, hover=hover))

    def hm_heart(self, cx, cy, s, fill="", outline="", width=2):
        """A heart (the small icon of the window gets blobby when it is drawn big)."""
        pts = []
        for i in range(0, 360, 9):
            t = math.radians(i)
            pts += [cx + s * 0.032 * 16 * math.sin(t) ** 3, cy - s * 0.032 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) + s * 0.04]
        self.hm_cv.create_polygon(pts, smooth=True, fill=fill, outline=outline, width=width)

    def hm_arrow(self, cx, cy, size, color):
        self.hm_cv.create_line(cx - size, cy, cx + size, cy, fill=color, width=2, arrow="last", arrowshape=(7, 9, 4))

    def hm_font(self, size, bold=True, italic=False):
        key = (size, bold, italic)
        f = self._hm_fonts.get(key)
        if f is None:
            f = self._hm_fonts[key] = tkfont.Font(family=self.f_disp, size=size, weight="bold" if bold else "normal", slant="italic" if italic else "roman")
        return f

    def hm_rr(self, big=False):
        """Corner size for panels (big = the banner)."""
        if STYLE["shape"] == "flat":
            return 0
        return 16 if big else max(8, STYLE["r"] + 2)

    def hm_panel(self, x1, y1, x2, y2, fill, big=False, glow=True, outline=None):
        cv = self.hm_cv
        r = self.hm_rr(big)
        out = outline if outline is not None else (GRID if STYLE["sep"] and not STYLE["glow"] else "")
        draw_shape(cv, x1, y1, x2, y2, fill=fill, outline=out, shape=STYLE["shape"], r=r)
        if glow and STYLE["glow"]:
            neon(cv, x1, y1, x2, y2, BRN2, fill, shape=STYLE["shape"], r=r, level=STYLE["glow"], width=2)

    def hm_mask(self, x1, y1, x2, y2, color, shape, r, corners=("tl", "tr", "br", "bl")):
        """Square picture -> rounded / cut / round picture: the corners are covered with the colour behind it."""
        cv = self.hm_cv
        if shape == "round" and r >= 2:
            for c in corners:
                if c == "tl":
                    pts = [x1 - 1, y1 - 1] + _arc(x1 + r, y1 + r, r, 180, 90)
                elif c == "tr":
                    pts = [x2 + 1, y1 - 1] + _arc(x2 - r, y1 + r, r, 90, 0)
                elif c == "br":
                    pts = [x2 + 1, y2 + 1] + _arc(x2 - r, y2 - r, r, 0, -90)
                else:
                    pts = [x1 - 1, y2 + 1] + _arc(x1 + r, y2 - r, r, 270, 180)
                cv.create_polygon(pts, fill=color, outline=color)
        elif shape == "cut" and r >= 2:
            if "tl" in corners:
                cv.create_polygon(x1 - 1, y1 - 1, x1 + r, y1 - 1, x1 - 1, y1 + r, fill=color, outline=color)
            if "br" in corners:
                cv.create_polygon(x2 + 1, y2 + 1, x2 - r, y2 + 1, x2 + 1, y2 - r, fill=color, outline=color)
        elif shape == "circle":
            R = (x2 - x1) / 2.0 - 0.5
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            for pts in ([x1 - 1, y1 - 1] + _arc(cx, cy, R, 90, 180), [x2 + 1, y1 - 1] + _arc(cx, cy, R, 0, 90),
                        [x2 + 1, y2 + 1] + _arc(cx, cy, R, -90, 0), [x1 - 1, y2 + 1] + _arc(cx, cy, R, 180, 270)):
                cv.create_polygon(pts, fill=color, outline=color)

    def hm_cover(self, x, y, size, path, title, behind, rr=8):
        """A song cover (or the tile of the library when it has none) with the corners of the look in use."""
        cv = self.hm_cv
        img = self.thumb_image(path, size) if path else None
        if img is not None:
            cv.create_image(x + size / 2.0, y + size / 2.0, image=img)
            self.hm_mask(x, y, x + size, y + size, behind, STYLE["shape"], rr)
        else:
            self.draw_square(cv, x, y, size, title or "?", "song")

    def hm_button(self, x, y, w, h, text, act, filled=True, icon=None):
        cv = self.hm_cv
        shape, r = STYLE["btn"], (h / 2.0 if STYLE["btn"] == "pill" else 6)
        fg = BLK if filled else TXT
        draw_shape(cv, x, y, x + w, y + h, fill=GOLD if filled else "", outline="" if filled else (BRN2 if STYLE["glow"] else DIM), shape=shape, r=r, width=1)
        if STYLE["glow"] and filled:
            neon(cv, x, y, x + w, y + h, INFO, GOLD, shape=shape, r=r, level=1, width=1)
        tx = x + w / 2.0
        if icon:
            tx += 8
            draw_icon(cv, icon, x + 18, y + h / 2.0, 13, fg)
        cv.create_text(tx, y + h / 2.0, text=cap(text), fill=fg, font=self.f_ui_b)
        self.hm_hit(x, y, x + w, y + h, act, shape=shape, r=r)

    def hm_title(self, x1, x2, y, text, see=None):
        """Section title: accent bar + title, and a 'See All' link at the right. Returns the y below it."""
        cv = self.hm_cv
        cv.create_rectangle(x1, y + 2, x1 + 4, y + 22, fill=GOLD, outline="")
        cv.create_text(x1 + 14, y + 12, text=cap(text), fill=TXT, font=self.f_title, anchor="w")
        if see:
            lab = self.hm_t("hm_see_all")
            f = self.mf["small"]
            tw = f.measure(lab)
            col = BRN2 if not STYLE["glow"] else INFO
            cv.create_text(x2 - 24, y + 12, text=lab, fill=col, font=self.f_small, anchor="e")
            self.hm_arrow(x2 - 10, y + 12, 6, col)
            self.hm_hit(x2 - tw - 36, y, x2, y + 26, see)
        return y + 34

    # ------------------------------------------------------------------ the banner
    def hm_art(self, x1, y1, x2, y2, bg):
        """The picture of the banner, drawn (no file): flowing lines and a record. The colours are those of the look in use."""
        cv = self.hm_cv
        h, w = y2 - y1, x2 - x1
        wx = x1 + w * (0.46 if w >= 520 else 0.30)
        for k in range(4):                                                    # flowing lines behind (right of the text)
            col = lerp(bg, BRN2, 0.08 + 0.06 * k)
            pts = []
            for i in range(0, 9):
                px = wx + (x2 - wx) * i / 8.0
                py = y1 + h * (0.34 + 0.11 * k) + math.sin(i * 0.9 + k * 1.3) * h * 0.12
                pts += [px, py]
            cv.create_line(pts, smooth=True, fill=col, width=2 + (k % 2))
        if w < 430:
            return
        R = min(h * 0.43, w * 0.30)
        cx, cy = x2 - R - h * 0.12, (y1 + y2) / 2.0 + h * 0.02
        dark = lerp(BLK, bg, 0.35)
        if STYLE["glow"]:
            cv.create_oval(cx - R - 5, cy - R - 5, cx + R + 5, cy + R + 5, outline=lerp(INFO, bg, 0.65), width=2)
        cv.create_oval(cx - R, cy - R, cx + R, cy + R, fill=dark, outline=lerp(bg, BRN2, 0.55) if STYLE["shape"] != "flat" else lerp(bg, GOLD, 0.4), width=2)
        for i in range(1, 8):                                                 # the grooves
            rr = R * (0.97 - i * 0.085)
            cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline=lerp(dark, BRN2, 0.10 + (i % 2) * 0.10), width=1)
        for a in (28, 208):                                                   # the light on the vinyl
            cv.create_arc(cx - R * 0.8, cy - R * 0.8, cx + R * 0.8, cy + R * 0.8, start=a, extent=38, style="arc", outline=lerp(dark, TXT, 0.30), width=3)
        lr = R * 0.36
        cv.create_oval(cx - lr, cy - lr, cx + lr, cy + lr, fill=BRN, outline=GOLD if STYLE["shape"] != "flat" else lerp(BRN, GOLD, 0.5), width=2)
        cv.create_oval(cx - lr * 0.55, cy - lr * 0.55, cx + lr * 0.55, cy + lr * 0.55, outline=lerp(BRN, GOLD, 0.55), width=1)
        cv.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=bg, outline="")
        px, py = x2 - 26, y1 + 24                                             # the tone arm
        cv.create_line(px, py, px, py + h * 0.28, cx + R * 0.52, cy - R * 0.10, fill=lerp(bg, TXT, 0.45), width=4, smooth=False)
        cv.create_oval(px - 8, py - 8, px + 8, py + 8, fill=lerp(bg, TXT, 0.25), outline=lerp(bg, TXT, 0.5))

    def hm_hero(self, x1, y1, x2, y2, big):
        cv = self.hm_cv
        bg = lerp(CARD, BLK, 0.40)
        self.hm_panel(x1, y1, x2, y2, bg, big=True)
        self.hm_art(x1 + 2, y1 + 2, x2 - 2, y2 - 2, bg)
        h, w = y2 - y1, x2 - x1
        tx = x1 + (28 if w > 420 else 18)
        txt_w = int(min(w - (tx - x1) - 10, w * (0.56 if w >= 520 else 0.95)))
        ws = max(26, min(48, int(h * 0.20 + 4))) if big else max(24, min(40, int(h * 0.17 + 4)))
        fw = self.hm_font(-ws)
        word = "ROFPALYS" if STYLE["caps"] else "RofPalys"
        while fw.measure(word) > txt_w and ws > 18:
            ws -= 2
            fw = self.hm_font(-ws)
        cv.create_text(tx, y1 + h * 0.15, text=cap(self.hm_t("hm_welcome")), fill=lerp(TXT, bg, 0.30), font=self.f_small, anchor="w")
        cv.create_text(tx, y1 + h * 0.15 + ws * 0.75 + 8, text=word, fill=TXT, font=fw, anchor="w")
        cv.create_line(tx, y1 + h * 0.15 + ws * 1.45 + 8, tx + min(60, txt_w // 3), y1 + h * 0.15 + ws * 1.45 + 8, fill=GOLD, width=3)
        cv.create_text(tx, y1 + h * 0.15 + ws * 1.45 + 24, text=self.hm_t("hm_tagline"), fill=lerp(TXT, bg, 0.25), font=self.f_small, anchor="nw", width=txt_w)
        by = y2 - 24 - 36 * 1
        label = self.hm_t("hm_play_now")
        bw = int(self.mf["ui_b"].measure(cap(label))) + 62
        self.hm_button(tx, by, bw, 36, label, lambda x, y: self.hm_play_now(), True, "play")
        cb = 36
        cx0 = tx + bw + 10
        draw_shape(cv, cx0, by, cx0 + cb, by + cb, outline=BRN2 if STYLE["glow"] else DIM, shape="pill" if STYLE["btn"] == "pill" else STYLE["btn"], r=cb / 2.0 if STYLE["btn"] == "pill" else 6)
        self.hm_arrow(cx0 + cb / 2.0, by + cb / 2.0, 8, TXT)
        self.hm_hit(cx0, by, cx0 + cb, by + cb, lambda x, y: self.set_chip("songs"), shape="round", r=cb / 2.0)

    def hm_play_now(self):
        if not E.songs_all:
            self.add_folder()
            return
        last = (self.cfg.get("last") or {}).get("song") or ""
        if E.playing_song_name:
            if E.is_playing and not E.is_paused:
                self.go("now")
            else:
                self.toggle()
        elif last in E.songs_all:
            self.play(last, float(self.cfg["last"].get("pos", 0) or 0))
        else:
            self.play(random.choice(E.songs_all))

    def hm_play_any(self):
        if not E.songs_all:
            self.add_folder()
        else:
            self.play(random.choice(E.songs_all))

    # ------------------------------------------------------------------ Now Playing card
    def hm_np(self, x1, y1, x2, y2):
        cv = self.hm_cv
        before = set(cv.find_all())
        self.hm_hits = [h for h in self.hm_hits if h["tag"] != "np"]
        self.hm_panel(x1, y1, x2, y2, CARD, big=True)
        name = E.playing_song_name
        playing = E.is_playing and not E.is_paused
        draw_icon(cv, "wave", x1 + 24, y1 + 20, 15, GOLD)
        cv.create_text(x1 + 40, y1 + 20, text=cap(self.T("now")), fill=TXT, font=self.f_ui_b, anchor="w")
        fav = bool(name) and name in E.favorites
        draw_icon(cv, "heart_on" if fav else "heart", x2 - 28, y1 + 20, 16, RED if fav else DIM)
        self.hm_hit(x2 - 44, y1 + 6, x2 - 8, y1 + 34, lambda x, y: self.toggle_fav(), tag="np")
        cs = 96
        t = M.current()
        self.hm_cover(x1 + 18, y1 + 42, cs, name, E.title_of(name) if name else "RofPalys", CARD, 8)
        tx, tw = x1 + 18 + cs + 14, x2 - 16 - (x1 + 18 + cs + 14)
        title = E.title_of(name) if name else self.hm_t("hm_nothing")
        sub = (t.artist if (t and t.artist) else (os.path.basename(os.path.dirname(name)) if name else "RofPalys"))
        cv.create_text(tx, y1 + 66, text=self.fit(title, "title", tw), fill=TXT, font=self.f_title, anchor="w")
        cv.create_text(tx, y1 + 90, text=self.fit(sub, "small", tw), fill=DIM, font=self.f_small, anchor="w")
        pos, total = self.position(), (E.total_time_seconds if E.duration_known else 0)
        cv.create_text(tx, y1 + 118, text="%s / %s" % (hms(pos), E.total_time_str if E.duration_known else "--:--"), fill=DIM, font=self.f_small, anchor="w")
        by, b1, b2 = y1 + 160, x1 + 18, x2 - 18
        frac = (pos / total) if total else 0.0
        paint_track(cv, b1, b2, by, b1 + (b2 - b1) * max(0.0, min(1.0, frac)))
        self.hm_hit(b1 - 4, by - 10, b2 + 4, by + 10, lambda x, y: (self.seek(max(0.0, min(1.0, (x - b1) / float(b2 - b1))) * total) if total else None), tag="np")
        cy, mid = y1 + 190, (x1 + x2) / 2.0
        mode = ["arrow", "repeat1", "arrow2", "repeat", "shuffle"][E.play_mode]
        for dx, kind, col, act in ((-96, mode, GOLD if E.play_mode else DIM, self.cycle_mode), (-50, "prev", TXT, lambda: self.step(-1)),
                                   (50, "next", TXT, lambda: self.step(1)), (96, "expand", DIM, lambda: self.go("now"))):
            draw_icon(cv, kind, mid + dx, cy, 17, col)
            self.hm_hit(mid + dx - 16, cy - 16, mid + dx + 16, cy + 16, lambda x, y, a=act: a(), tag="np")
        pr = 17
        if STYLE["play"] == "hex":
            draw_shape(cv, mid - pr, cy - pr, mid + pr, cy + pr, fill=BLK, outline=GOLD, shape="cut", r=8, width=2)
            icol = GOLD
        else:
            cv.create_oval(mid - pr, cy - pr, mid + pr, cy + pr, fill=GOLD, outline="")
            icol = BLK
        draw_icon(cv, "pause" if playing else "play", mid + (0 if playing else 1), cy, 14, icol)
        self.hm_hit(mid - pr, cy - pr, mid + pr, cy + pr, lambda x, y: self.toggle(), shape="round", r=pr, tag="np")
        for i in set(cv.find_all()) - before:
            cv.addtag_withtag("np", i)
        self._hm_npsig = self.hm_np_sig()

    def hm_np_sig(self):
        return (E.playing_song_name, E.is_playing, E.is_paused, int(self.position()), E.play_mode, bool(E.playing_song_name) and E.playing_song_name in E.favorites)

    def hm_np_redraw(self):
        box = self._hm_np_box
        if not box:
            return
        self.hm_cv.delete("np")
        self.hm_np(*box)

    # ------------------------------------------------------------------ quick access
    def hm_quick(self, x1, x2, y, data):
        cv = self.hm_cv
        y = self.hm_title(x1, x2, y, self.hm_t("hm_quick"))
        inner, gap = x2 - x1, 14
        cols = 4 if inner >= 700 else 2
        tw, th = (inner - gap * (cols - 1)) / float(cols), 94
        tiles = [("play", "hm_q_play", "hm_q_play_s", lambda x, yy: self.hm_play_any()),
                 ("liked", "hm_q_liked", "hm_q_liked_s", lambda x, yy: self.set_chip("favorites")),
                 ("list", "hm_q_list", "hm_q_list_s", lambda x, yy: self.set_chip("playlists") if "playlists" in self.chip_keys() else self.go("queue")),
                 ("top", "hm_q_top", "hm_q_top_s", lambda x, yy: self.go("stats") if "stats" in self.frames else self.set_chip("songs"))]
        for k, (kind, tk_, sk, act) in enumerate(tiles):
            c, r_ = k % cols, k // cols
            a, b = x1 + c * (tw + gap), y + r_ * (th + gap)
            self.hm_panel(a, b, a + tw, b + th, CARD)
            icon = {"play": "headphones", "liked": "heart", "list": "queue", "top": "stats"}[kind]
            draw_icon(cv, icon, a + 26, b + 26, 18, GOLD)
            txtw = int(tw - 32 - (64 if tw >= 210 else 0))
            cv.create_text(a + 16, b + 52, text=self.fit(cap(self.hm_t(tk_)), "ui_b", txtw), fill=TXT, font=self.f_ui_b, anchor="w")
            sub = self.hm_t(sk)
            if kind == "liked":
                sub = "%d %s" % (data["favs"], self.T("songs"))
            cv.create_text(a + 16, b + 74, text=self.fit(sub, "small", txtw), fill=DIM, font=self.f_small, anchor="w")
            ax, ay = a + tw - 54, b + th / 2.0
            dim = lerp(CARD, BRN2, 0.50)
            if tw < 210:
                pass
            elif kind == "play":
                draw_icon(cv, "headphones", ax, ay, 58, lerp(CARD, BRN2, 0.42))
                cv.create_oval(a + tw - 36, b + th - 36, a + tw - 10, b + th - 10, fill=GOLD, outline="")
                draw_icon(cv, "play", a + tw - 22, b + th - 23, 11, BLK)
            elif kind == "liked":
                self.hm_heart(ax, ay, 40, fill=lerp(CARD, RED, 0.28), outline=lerp(CARD, RED, 0.6), width=2)
            elif kind == "list":
                for i, rr in enumerate((34, 24, 14)):
                    cv.create_oval(ax - rr, ay - rr, ax + rr, ay + rr, outline=lerp(CARD, BRN2, 0.25 + i * 0.2), width=2)
                cv.create_oval(ax - 4, ay - 4, ax + 4, ay + 4, fill=dim, outline="")
            else:
                vals = data["top"] or [3, 5, 4, 7, 9, 12]
                mx = float(max(vals)) or 1.0
                bw_ = 9
                for i, v in enumerate(vals[:6]):
                    bx = a + tw - 14 - (len(vals[:6]) - i) * (bw_ + 3)
                    bh = 10 + 38 * v / mx
                    cv.create_rectangle(bx, b + th - 14 - bh, bx + bw_, b + th - 14, fill=lerp(CARD, BRN2, 0.35 + 0.6 * v / mx), outline="")
            self.hm_hit(a, b, a + tw, b + th, act, shape=STYLE["shape"], r=self.hm_rr())
        rows = (len(tiles) + cols - 1) // cols
        return y + rows * th + (rows - 1) * gap + 24

    # ------------------------------------------------------------------ shelves of cards (the same cards as the pages of the library)
    def hm_shelf(self, x1, x2, y, title, items, see=None, max_slots=6):
        """One row of square cards under a title. items: song items or group items. Returns the y below it."""
        if not items or not hasattr(self, "bw_card"):
            return y
        y = self.hm_title(x1, x2, y, title, see=see)
        avail, gap = x2 - x1, 14
        slots = max(2, min(max_slots, int((avail + gap) // (158 + gap))))
        cw = (avail - gap * (slots - 1)) / float(slots)
        cs = max(64, (int(cw - 24) // 16) * 16)
        h = 12 + cs + 62
        for k, it in enumerate(items[:slots]):
            a = x1 + k * (cw + gap)
            u = dict(x1=a, y1=y, x2=a + cw, y2=y + h, item=it, cs=cs, pr=None, shape=STYLE["shape"], r=self.hm_rr())
            self.bw_card(u)
            self.hm_hit(a, y, a + cw, y + h, lambda x, yy, u=u: self.bw_card_click(u, x, yy), item=it, shape=STYLE["shape"], r=self.hm_rr(),
                        hover=lambda hh, u=u: self.bw_card_hover(u))
        return y + h + 26

    def hm_recent(self, x1, x2, y, data):
        T = self.T
        items = [self.song_item(p) for p in data["recent"]]
        if not items:
            y = self.hm_title(x1, x2, y, T({"recent": "recent", "new": "new", "discover": "discover"}[data["rkey"]]), see=lambda x, yy: self.set_chip("songs"))
            self.hm_cv.create_text(x1 + 4, y + 20, text=self.hm_t("hm_empty"), fill=DIM, font=self.f_ui, anchor="w", width=max(80, x2 - x1 - 10))
            return y + 60
        return self.hm_shelf(x1, x2, y, T({"recent": "recent", "new": "new", "discover": "discover"}[data["rkey"]]), items, see=lambda x, yy: self.set_chip("songs"))

    def hm_more(self, x1, x2, y, data, order):
        """The other shelves of the page, in the order given: mixes, suggested, most, added, playlists."""
        for key in order:
            if key == "mixes" and data["mixes"]:
                y = self.hm_shelf(x1, x2, y, I18N.tr("Made for you"), [self.group_item(g) for g in data["mixes"]], see=lambda x, yy: self.set_chip("smartmix") if "smartmix" in self.chip_keys() else None)
            elif key == "suggest" and data["suggest"]:
                y = self.hm_shelf(x1, x2, y, I18N.tr("Suggested for you"), [self.song_item(p) for p in data["suggest"]], see=lambda x, yy: self.set_chip("songs"))
            elif key == "most" and data["most"]:
                y = self.hm_shelf(x1, x2, y, I18N.tr("Most played"), [self.song_item(p) for p in data["most"]], see=lambda x, yy: self.go("stats") if "stats" in self.frames else self.set_chip("songs"))
            elif key == "added" and data["added"]:
                y = self.hm_shelf(x1, x2, y, I18N.tr("Recently added"), [self.song_item(p) for p in data["added"]], see=lambda x, yy: self.set_chip("songs"))
            elif key == "playlists" and data["playlists"]:
                y = self.hm_shelf(x1, x2, y, self.hm_t("hm_playlists"), [self.group_item(g) for g in data["playlists"]], see=lambda x, yy: self.set_chip("playlists"))
        return y

    def hm_footer(self, x1, x2, y, W):
        """The last thing on the Home page: who made Rofpalys. Centered, quiet, a hairline above it (the lines are the brand statement: not translated)."""
        cv = self.hm_cv
        y += 6
        cv.create_line(x1, y, x2, y, fill=GRID)
        mid, tw = W / 2.0, max(160, int(x2 - x1 - 20))
        y += 34
        cv.create_line(mid - 16, y, mid + 16, y, fill=GOLD, width=2)
        y += 20
        for text, font, col in (("Rofpalys by Anrofty", self.hm_font(13), TXT), ("Rofpalys was founded on November 1, 2026", self.f_small, DIM),
                                ("And now, Rofpalys has not been officially released to the public.", self.f_small, DIM)):
            i = cv.create_text(mid, y, text=text, fill=col, font=font, anchor="n", justify="center", width=tw)
            bb = cv.bbox(i)
            y += (bb[3] - bb[1] if bb else 18) + (8 if col == TXT else 4)
        return y + 34

    # ------------------------------------------------------------------ top artists
    def hm_artists(self, x1, x2, y, data):
        cv = self.hm_cv
        y = self.hm_title(x1, x2, y, self.hm_t("hm_artists"), see=lambda x, yy: self.set_chip("artists"))
        arts = data["artists"]
        avail = x2 - x1
        d = 76 if avail >= 330 else 64
        n = max(1, min(len(arts), int(avail // (d + 12))))
        cell = avail / float(n)
        for k, g in enumerate(arts[:n]):
            cx = x1 + cell * k + cell / 2.0
            a, b = cx - d / 2.0, y + 4
            path = next((p for p in g["paths"] if M.art_of(p)), "")
            img = self.thumb_image(path, d) if path else None
            if img is not None:
                cv.create_image(cx, b + d / 2.0, image=img)
                self.hm_mask(a, b, a + d, b + d, PNL, "circle", 0)
            else:
                shade = COVER_SHADES[zlib.crc32(g["name"].encode("utf-8", "replace")) % len(COVER_SHADES)]
                cv.create_oval(a, b, a + d, b + d, fill=shade, outline="")
                cv.create_text(cx, b + d / 2.0, text=(g["name"].strip()[:1] or "?").upper(), fill=GOLD, font=self.hm_font(-int(d * 0.42)))
            cv.create_oval(a - 1, b - 1, a + d + 1, b + d + 1, outline=BRN2, width=2)
            if STYLE["glow"] >= 2:
                cv.create_oval(a - 4, b - 4, a + d + 4, b + d + 4, outline=lerp(INFO, PNL, 0.6), width=1)
            cv.create_text(cx, b + d + 14, text=self.fit(g["name"], "small", int(cell - 6)), fill=TXT, font=self.f_small)
            cv.create_text(cx, b + d + 30, text="%d %s" % (len(g["paths"]), self.T("songs")), fill=DIM, font=self.f_small)
            self.hm_hit(cx - cell / 2.0, b - 4, cx + cell / 2.0, b + d + 40, lambda x, yy, gid=g["id"]: self.open_group(gid), shape="round", r=10)
        return y + d + 56

    # ------------------------------------------------------------------ your playlists
    def hm_playlists(self, x1, x2, y, data):
        cv = self.hm_cv
        y = self.hm_title(x1, x2, y, self.hm_t("hm_playlists"), see=lambda x, yy: self.set_chip("playlists") if "playlists" in self.chip_keys() else None)
        inner, gap = x2 - x1, 14
        n = max(1, min(4, int(inner // 220)))
        tw, th = (inner - gap * (n - 1)) / float(n), 66
        tiles = [("new", None), ("liked", None)] + [("pl", g) for g in data["playlists"]]
        tiles = tiles[:n * 2]
        for k, (kind, g) in enumerate(tiles):
            c, r_ = k % n, k // n
            a, b = x1 + c * (tw + gap), y + r_ * (th + 10)
            self.hm_panel(a, b, a + tw, b + th, CARD, glow=False)
            ix, iy, isz = a + 8, b + 8, th - 16
            if kind == "pl":
                it = self.group_item(g)
                sub = "%d %s" % (len(g["paths"]), self.T("songs"))
                mode, imgs = self.group_cover(it, isz)
                if mode == "single":
                    cv.create_image(ix + isz / 2.0, iy + isz / 2.0, image=imgs[0])
                    self.hm_mask(ix, iy, ix + isz, iy + isz, CARD, STYLE["shape"], 6)
                elif mode == "mosaic":
                    hh = isz // 2
                    for q, im in enumerate(imgs):
                        cv.create_image(ix + (q % 2) * hh + hh // 2, iy + (q // 2) * hh + hh // 2, image=im)
                else:
                    self.draw_square(cv, ix, iy, isz, g["name"], "group")
                title, col = g["name"], TXT
                act = lambda x, yy, gid=g["id"]: self.open_group(gid)
                item = it
            else:
                draw_shape(cv, ix, iy, ix + isz, iy + isz, fill=lerp(CARD, BRN2, 0.30), shape=STYLE["shape"], r=6)
                if kind == "new":
                    draw_icon(cv, "plus", ix + isz / 2.0, iy + isz / 2.0, 20, GOLD)
                    title, sub, col = self.T("new_playlist"), "", GOLD
                    act = lambda x, yy: self.pl_new() if hasattr(self, "pl_new") else None
                else:
                    self.hm_heart(ix + isz / 2.0, iy + isz / 2.0, 22, fill=RED, outline=RED, width=1)
                    title, sub, col = self.T("favorites"), "%d %s" % (data["favs"], self.T("songs")), TXT
                    act = lambda x, yy: self.set_chip("favorites")
                item = None
            tx = ix + isz + 12
            if sub:
                cv.create_text(tx, b + 24, text=self.fit(title, "ui_b", int(a + tw - tx - 8)), fill=col, font=self.f_ui_b, anchor="w")
                cv.create_text(tx, b + 45, text=self.fit(sub, "small", int(a + tw - tx - 8)), fill=DIM, font=self.f_small, anchor="w")
            else:
                cv.create_text(tx, b + th / 2.0, text=self.fit(title, "ui_b", int(a + tw - tx - 8)), fill=col, font=self.f_ui_b, anchor="w")
            self.hm_hit(a, b, a + tw, b + th, act, item=item, shape=STYLE["shape"], r=self.hm_rr())
        rows = (len(tiles) + n - 1) // n
        return y + rows * th + (rows - 1) * 10 + 24

    # ------------------------------------------------------------------ the whole page
    def hm_draw(self):
        cv = getattr(self, "hm_cv", None)
        if cv is None or not self._hm_on:
            return
        kind = self.pg_kind()
        if kind in ("grid", "detail", "artist"):
            try:
                self.bw_draw(kind)
            except Exception as e:
                log("library page: %r" % (e,))
            return
        try:
            W = int(cv.winfo_width())
            if W < 120:
                return
            top = cv.canvasy(0)
            cv.configure(bg=PNL)
            cv.delete("all")
            self.hm_hits, self._hm_hover, self._hm_np_box = [], -1, None
            if hasattr(self, "bw_reset"):
                self.bw_reset()
            data = self.hm_data()
            lay = self.hm_layout()
            pad = 22 if W >= 700 else 14
            gap = 14
            x1, x2 = pad, W - pad
            inner = x2 - x1
            y = pad - 6
            if lay == "dash":
                hh = 216 if inner >= 560 else 190
                npw = 330 if inner >= 900 else 0
                hx2 = x2 - (npw + gap if npw else 0)
                self.hm_hero(x1, y, hx2, y + hh, False)
                if npw:
                    self._hm_np_box = (hx2 + gap, y, x2, y + hh)
                    self.hm_np(*self._hm_np_box)
                y += hh + 24
                y = self.hm_quick(x1, x2, y, data)
                if data["artists"] and inner >= 980:
                    lw = int(inner * 0.63)
                    ya = self.hm_recent(x1, x1 + lw, y, data)
                    yb = self.hm_artists(x1 + lw + 26, x2, y, data)
                    y = max(ya, yb)
                else:
                    y = self.hm_recent(x1, x2, y, data)
                    if data["artists"]:
                        y = self.hm_artists(x1, x2, y, data)
                y = self.hm_more(x1, x2, y, data, ("mixes", "suggest", "most", "playlists", "added"))
            else:
                hh = 250 if inner >= 560 else 200
                self.hm_hero(x1, y, x2, y + hh, True)
                y += hh + 24
                y = self.hm_recent(x1, x2, y, data)
                y = self.hm_more(x1, x2, y, data, ("mixes", "suggest"))
                y = self.hm_playlists(x1, x2, y, data)
                if data["artists"]:
                    y = self.hm_artists(x1, x2, y, data)
                y = self.hm_more(x1, x2, y, data, ("most", "added"))
            y = self.hm_footer(x1, x2, y, W)
            y += pad
            cv.configure(scrollregion=(0, 0, W, max(y, int(cv.winfo_height()))))
            cv.yview_moveto(max(0.0, top / float(max(1, y))))
            self._hm_sig = self.hm_sig()
            self._hm_next = time.time() + 0.5
        except Exception as e:
            log("home page: %r" % (e,))

    def hm_sig(self):
        base = (E.library_version, E.current_lang, TH.current() if TH else "", self.hm_layout(), int(self.hm_cv.winfo_width()), len(self.cfg["stats"]), len(self.extra_groups),
                self.chip, self.group)
        kind = self.pg_kind() if hasattr(self, "pg_kind") else "home"
        if kind == "grid":
            return base
        if kind in ("detail", "artist"):
            return base + (E.playing_song_name, E.is_playing, E.is_paused, len(E.favorites), M.thumb_version)
        return base + (M.thumb_version, E.playing_song_name, len(E.favorites))

    def hm_poll(self):
        if not self._hm_on or not self.hm_cv.winfo_ismapped():
            return
        try:
            now = time.time()
            if self.hm_sig() != self._hm_sig:
                if now >= self._hm_next:
                    self.hm_draw()
                return
            if getattr(self, "bw_units", None):
                light = (M.thumb_version, E.playing_song_name, E.is_playing, E.is_paused, len(E.favorites))
                if light != self._bw_light:
                    self._bw_light = light
                    self.bw_refresh()
            if self._hm_np_box and self.hm_np_sig() != self._hm_npsig:
                self.hm_np_redraw()
        except Exception as e:
            log("home poll: %r" % (e,))

    # ------------------------------------------------------------------ mouse: hits, hover, scrolling
    def hm_find(self, e):
        x, y = self.hm_cv.canvasx(e.x), self.hm_cv.canvasy(e.y)
        for h in reversed(self.hm_hits):
            if h["x1"] <= x <= h["x2"] and h["y1"] <= y <= h["y2"]:
                return h, x, y
        u = self.bw_unit_at(x, y) if getattr(self, "bw_units", None) else None
        return u, x, y

    def hm_press(self, e):
        self._hm_moved, self._hm_y = False, e.y
        self.hm_cv.scan_mark(0, e.y)

    def hm_drag(self, e):
        if abs(e.y - self._hm_y) > 6:
            self._hm_moved = True
        if self._hm_moved:
            self.hm_cv.scan_dragto(0, e.y, gain=1)

    def hm_release(self, e):
        if self._hm_moved:
            return
        h, x, y = self.hm_find(e)
        if h is not None and h.get("act"):
            try:
                h["act"](x, y)
            except Exception as ex:
                log("home click: %r" % (ex,))

    def hm_menu(self, e):
        h, x, y = self.hm_find(e)
        if h is None or not h.get("item"):
            return
        it = h["item"]
        if it["kind"] == "song" and hasattr(self, "sheet_song"):
            self.sheet_song(it["path"], e.x_root, e.y_root)
        else:
            self.row_menu(it, e)

    def hm_motion(self, e):
        h, _x, _y = self.hm_find(e)
        idx = id(h) if h is not None else -1
        if idx == self._hm_hover:
            return
        self._hm_hover = idx
        cv = self.hm_cv
        cv.delete("hov")
        cv.configure(cursor="hand2" if h is not None else "")
        if h is not None and h.get("hover"):
            h["hover"](h)
        elif h is not None and h["shape"] != "x":
            col = INFO if STYLE["glow"] else GOLD
            if h["shape"] == "round" and h["r"] and h["r"] >= (h["y2"] - h["y1"]) / 2.0 - 1:
                cv.create_oval(h["x1"], h["y1"], h["x2"], h["y2"], outline=col, width=2, tags="hov")
            else:
                draw_shape(cv, h["x1"], h["y1"], h["x2"], h["y2"], outline=col, shape=h["shape"], r=h["r"], width=2, tags="hov")

    def hm_wheel(self, e):
        d = -1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1
        self.hm_cv.yview_scroll(d * 3, "units")

    def hm_resized(self, e=None):
        if not self._hm_on:
            return
        if self._hm_job:
            self.root.after_cancel(self._hm_job)
        self._hm_job = self.root.after(140, self.hm_draw)


def build_home(app):
    """After the window exists (and again after a look switch): the canvas of the pages."""
    app._hm_on, app._hm_sig, app._hm_next, app._hm_job, app._hm_hover, app._hm_np_box, app._hm_npsig = False, None, 0.0, None, -1, None, None
    app.hm_hits, app._hm_moved, app._hm_y, app._hm_fonts, app._bw_light = [], False, 0, {}, None
    cv = tk.Canvas(app.lv, bg=PNL, highlightthickness=0, yscrollincrement=24, yscrollcommand=getattr(app, "hm_yscroll", ""))
    app.hm_cv = cv
    cv.bind("<Configure>", app.hm_resized)
    cv.bind("<ButtonPress-1>", app.hm_press)
    cv.bind("<B1-Motion>", app.hm_drag)
    cv.bind("<ButtonRelease-1>", app.hm_release)
    cv.bind("<Button-3>", app.hm_menu)
    cv.bind("<Motion>", app.hm_motion)
    cv.bind("<Leave>", lambda e: (cv.delete("hov"), setattr(app, "_hm_hover", -1)))
    for seq in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
        cv.bind(seq, app.hm_wheel)


def relabel_home(app):
    if getattr(app, "_hm_on", False):
        app._hm_sig = None


def register(app):
    app.add_texts(**_TXT)
    app.add_build(build_home)
    app.add_relabel(relabel_home)
    app.add_poll(lambda a: a.hm_poll())
    try:
        app.root.bind_all("<F8>", app.cycle_layout)
    except Exception:
        pass


# END-OF-FILE rofpalys_gui_home.py
