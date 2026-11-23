#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Command Palette (Ctrl+K)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""One box that finds everything: songs, artists, folders, playlists, mixes, pages and actions. Press Ctrl+K (or use the "..." menu), type a few letters, press Enter.

  (nothing typed)  the pages and the most useful actions, plus what you played last
  letters          songs (the same smart search as the search field), artists / folders / mixes, pages and actions that match
  >                only actions and pages       (">next", ">theme", ">stat")
  @                only artists / folders / playlists / mixes
  Up / Down        choose        Enter  run        Esc  close        Ctrl+K again  close

It is drawn in the look in use (square / rounded / cut corners, the fonts and the neon of the theme) and follows a theme switch the next time it opens.
Actions: play / pause, next, previous, play mode, volume, seek, favourite, language, look (Classic / Modern / Cyberpunk), every Statistics tab, and every entry that
other feature files put into the "..." menu."""
import os
import time

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    import rofpalys_theme as TH2
except Exception:
    TH2 = None
try:
    import rofpalys_analytics as AN
except Exception:
    AN = None

FEATURE = {"name": "palette", "title": "Command palette (Ctrl+K): songs, artists, pages and actions in one box", "version": "1.0", "order": 20, "enabled": True}
ROWS = 9                                             # rows that show at once
ROW_H = 44

TEXTS = {
    "en": dict(palette_menu="Command palette  (Ctrl+K)", pal_ph="Search songs, artists, pages, actions ...", pal_hint="Up/Down choose   Enter run   Esc close   > actions   @ artists and folders",
               pal_songs="Songs", pal_groups="Artists, folders, mixes", pal_pages="Pages", pal_actions="Actions", pal_recent="Played lately", pal_none="Nothing matches. Try fewer letters.",
               pal_song="song", pal_group="open", pal_page="page", pal_action="action", pal_look="look",
               pal_a_toggle="Play / pause", pal_a_next="Next song", pal_a_prev="Previous song", pal_a_mode="Change play mode", pal_a_fav="Favourite: add / remove the playing song",
               pal_a_volup="Volume up", pal_a_voldn="Volume down", pal_a_fwd="Skip 10 seconds forward", pal_a_back="Back 10 seconds", pal_a_lang="Change language",
               pal_a_look="Look", pal_a_stats="Statistics", pal_a_search="Search in the library", pal_a_now="Now Playing", pal_a_vis="Visualizer",
               pal_vol="Volume %d%%", pal_fav_none="Nothing is playing", pal_fav_on="Added to favourites", pal_fav_off="Removed from favourites"),
    "id": dict(palette_menu="Palet perintah  (Ctrl+K)", pal_ph="Cari lagu, artis, halaman, aksi ...", pal_hint="Atas/Bawah pilih   Enter jalankan   Esc tutup   > aksi   @ artis dan folder",
               pal_songs="Lagu", pal_groups="Artis, folder, mix", pal_pages="Halaman", pal_actions="Aksi", pal_recent="Baru diputar", pal_none="Tidak ada yang cocok. Coba huruf lebih sedikit.",
               pal_song="lagu", pal_group="buka", pal_page="halaman", pal_action="aksi", pal_look="tampilan",
               pal_a_toggle="Putar / jeda", pal_a_next="Lagu berikutnya", pal_a_prev="Lagu sebelumnya", pal_a_mode="Ganti mode putar", pal_a_fav="Favorit: tambah / hapus lagu yang diputar",
               pal_a_volup="Volume naik", pal_a_voldn="Volume turun", pal_a_fwd="Maju 10 detik", pal_a_back="Mundur 10 detik", pal_a_lang="Ganti bahasa",
               pal_a_look="Tampilan", pal_a_stats="Statistik", pal_a_search="Cari di pustaka", pal_a_now="Sedang Diputar", pal_a_vis="Visualizer",
               pal_vol="Volume %d%%", pal_fav_none="Tidak ada lagu yang diputar", pal_fav_on="Masuk favorit", pal_fav_off="Dihapus dari favorit"),
}


def pal():
    if TH2 is not None:
        try:
            return TH2.palette()
        except Exception:
            pass
    g = globals()
    d = {k: g[k] for k in ("BLK", "SIDE", "PNL", "PNL2", "HOVER", "ROW_HOVER", "BRN", "BRN2", "GOLD", "TXT", "DIM", "RED", "OK", "WARN", "INFO", "ACC2", "GRID", "CARD", "CARD2")}
    d["STYLE"] = dict(STYLE)
    return d


def norm(s):
    return " ".join("".join(ch if ch.isalnum() else " " for ch in str(s).lower()).split())


def score(q, text, fuzzy=True):
    """0 = no match. Higher is better: a start of the text or of a word beats the middle; all letters in order (a fuzzy match, titles only) is the weakest."""
    t = norm(text)
    if not q:
        return 1
    if not t:
        return 0
    if t == q:
        return 100
    if t.startswith(q):
        return 80
    if (" " + q) in (" " + t):
        return 60
    words, tw = q.split(), t.split()
    if all(any(x.startswith(w) for x in tw) for w in words):
        return 45                                   # every typed word starts a word of the text
    if all(w in t for w in words):
        return 25
    i = 0
    for ch in t:
        if i < len(q) and ch == q[i]:
            i += 1
    return 12 if fuzzy and i == len(q) and len(q) >= 3 else 0


class Mixin:
    # ------------------------------------------------------------------ what can be found
    def pal_t(self, k):
        return self.T(k)

    def pal_words(self, key):
        """The text of a key in BOTH languages: a search finds "next" and "berikutnya" whatever language the window is in."""
        a = TXT_.get("en", {}).get(key, "")
        b = TXT_.get("id", {}).get(key, "")
        c = self.T(key)
        return (a + " " + b + " " + (c if c not in (a, b) else "")).strip()

    def pal_actions(self):
        """[(label, hint, fn, icon, search words)] - every action of the box; a fresh list each time so the texts follow the language and the look."""
        T, W = self.T, self.pal_words
        acts = (("pal_a_toggle", I18N.tr("Space"), self.toggle, "play"), ("pal_a_next", "N", lambda: self.step(1), "next"), ("pal_a_prev", "P", lambda: self.step(-1), "prev"),
                ("pal_a_mode", "M", self.cycle_mode, "shuffle"), ("pal_a_fav", "L", self.pal_fav, "heart"), ("pal_a_volup", "", lambda: self.pal_vol(10), "volume"),
                ("pal_a_voldn", "", lambda: self.pal_vol(-10), "volume"), ("pal_a_fwd", "→", lambda: self.seek(self.position() + 10), "arrow"),
                ("pal_a_back", "←", lambda: self.seek(self.position() - 10), "back"), ("pal_a_search", "Ctrl+F", lambda: (self.go("library"), self.entry.focus_set()), "search"),
                ("pal_a_lang", "", self.cycle_lang, "lyrics"))
        out = [(T(k), h, fn, ic, W(k)) for k, h, fn, ic in acts]
        if TH2 is not None:
            lg = I18N.current()
            for name in TH2.names():
                out.append(("%s: %s" % (T("pal_a_look"), TH2.label(name, lg)), T("pal_look"), (lambda n=name: self.pal_look(n)), "palette",
                            "theme tema look tampilan warna color %s %s" % (name, TH2.label(name, "en"))))
        for label_key, fn in list(getattr(self, "menu_hooks", ())):                  # what other features put in the ... menu
            if label_key != "palette_menu":
                out.append((T(label_key), "...", (lambda f=fn: f(self)), "gear", W(label_key)))
        try:
            import rofpalys_gui_stats as GS
            for tab in GS.all_tabs():
                out.append(("%s: %s" % (T("pal_a_stats"), GS.tab_label(I18N.current(), tab)), "", (lambda t=tab: self.st_open(t)), "stats",
                            "stats statistics statistik %s %s %s" % (GS.tab_label("en", tab), GS.tab_label("id", tab), GS.tab_label(I18N.current(), tab))))
        except Exception:
            pass
        return out

    def pal_pages(self):
        T, W, out = self.T, self.pal_words, []
        for _order, key, label_key, icon in self.nav_list():
            out.append((T(label_key), T("pal_page"), (lambda k=key: self.go(k)), icon, W(label_key)))
        for key, label_key in self.chip_labels():
            out.append((T("library") + ": " + T(label_key), T("pal_page"), (lambda k=key: self.set_chip(k)), "folder", W(label_key)))
        return out

    def pal_fav(self):
        p = E.playing_song_name
        if not p:
            self.msg(self.T("pal_fav_none"))
            return
        self.toggle_fav(p)
        self.msg(self.T("pal_fav_on") if p in E.favorites else self.T("pal_fav_off"))

    def pal_vol(self, d):
        v = max(0, min(100, int(E.volume) + d))
        try:
            self.set_volume(v)
        except Exception:
            E.set_volume(v)
        self.msg(self.T("pal_vol") % v)

    def pal_look(self, name):
        if hasattr(self, "th_pick"):
            self.th_pick(name)
        elif TH2 is not None:
            TH2.switch(self.root, name, save_choice=True, retint_main=False)
            if hasattr(self, "rebuild_ui"):
                self.rebuild_ui()

    def pal_find(self, q):
        """The rows for what was typed: [{"kind": "head"|"song"|"group"|"page"|"action", "title", "sub", "hint", "run"}]."""
        T = self.T
        raw = q.strip()
        mode = ""
        if raw[:1] in (">", "@"):
            mode, raw = raw[0], raw[1:].strip()
        qn = norm(raw)
        rows = []

        def add_head(key, items):
            if items:
                rows.append({"kind": "head", "title": T(key)})
                rows.extend(items)

        def act_rows(src, kind, limit):
            sc = [(max(score(qn, a[0]), score(qn, a[4], False) - 5 if a[4] else 0), i, a) for i, a in enumerate(src)]
            sc = [s for s in sc if s[0] > 0]
            sc.sort(key=lambda s: (-s[0], s[1]))
            return [{"kind": kind, "title": a[0], "sub": "", "hint": a[1], "run": a[2], "icon": a[3]} for _s, _i, a in sc[:limit]]

        groups_all = list(getattr(self, "cats", [])) + list(getattr(self, "folders", [])) + list(getattr(self, "artists", [])) + list(getattr(self, "mixes", [])) + list(getattr(self, "extra_groups", []))

        def group_rows(limit):
            try:
                gs = L.match_groups(raw, groups_all)[:limit] if raw else groups_all[:limit]
            except Exception:
                gs = [g for g in groups_all if qn in norm(g["name"])][:limit]
            return [{"kind": "group", "title": g["name"], "sub": "%s  •  %d %s" % (T(self.kind_labels.get(g["kind"], "folder")), len(g["paths"]), T("songs")), "hint": T("pal_group"),
                     "run": (lambda gid=g["id"]: self.open_group(gid))} for g in gs]

        def song_row(p):
            it = self.song_item(p)
            return {"kind": "song", "title": it["title"], "sub": it["sub"], "hint": T("pal_song"), "run": (lambda path=p: self.play(path))}

        if mode == ">":
            add_head("pal_actions", act_rows(self.pal_actions(), "action", 30))
            add_head("pal_pages", act_rows(self.pal_pages(), "page", 12))
        elif mode == "@":
            add_head("pal_groups", group_rows(40))
        elif not qn:
            acts = self.pal_actions()
            add_head("pal_pages", [{"kind": "page", "title": a[0], "sub": "", "hint": a[1], "run": a[2], "icon": a[3]} for a in self.pal_pages()[:6]])
            add_head("pal_actions", [{"kind": "action", "title": a[0], "sub": "", "hint": a[1], "run": a[2], "icon": a[3]} for a in acts[:6]])
            add_head("pal_recent", self.pal_recent(6))
        else:
            try:
                res = L.smart_search(raw, E.songs_all, self.cfg["stats"], E.favorites, 8)
            except Exception:
                res = []
            add_head("pal_songs", [song_row(p) for p, _s in res])
            add_head("pal_groups", group_rows(5))
            add_head("pal_actions", act_rows(self.pal_actions(), "action", 5))
            add_head("pal_pages", act_rows(self.pal_pages(), "page", 3))
        return rows

    def pal_recent(self, n):
        """The songs played last (from the activity log; with no log: the songs with the most plays)."""
        out, seen = [], set()
        try:
            rec = AN.recorder() if AN is not None else None
            v = rec.view() if (rec is not None and rec.state == "running") else (AN.View(None) if AN is not None else None)
            for r in reversed(v.plays(60) if v is not None else []):
                p = r[2]
                if p and p not in seen and p in set(E.songs_all):
                    seen.add(p)
                    out.append(p)
                    if len(out) >= n:
                        break
        except Exception:
            out = []
        if not out:
            st = self.cfg.get("stats", {})
            out = sorted((p for p in E.songs_all if st.get(p, {}).get("plays", 0)), key=lambda p: -st[p]["plays"])[:n]
        T = self.T
        rows = []
        for p in out:
            it = self.song_item(p)
            rows.append({"kind": "song", "title": it["title"], "sub": it["sub"], "hint": T("pal_song"), "run": (lambda path=p: self.play(path))})
        return rows

    # ------------------------------------------------------------------ the box
    def pal_visible(self):
        w = getattr(self, "pal_win", None)
        try:
            return w is not None and bool(w.winfo_exists())
        except Exception:
            return False

    def pal_toggle(self, _e=None):
        if self.pal_visible():
            self.pal_close()
        else:
            self.pal_open()
        return "break"

    def pal_open(self, text=""):
        if self.pal_visible():
            self.pal_close()
        if getattr(self, "_rebuilding", False):
            return
        P = pal()
        st = P["STYLE"]
        fonts = look_fonts(self.root, 10)
        self.pal_fonts = {k: font_obj(fonts[k]) for k in ("ui", "small", "title", "ui_b")}
        self.root.update_idletasks()
        rw, rh = max(self.root.winfo_width(), 420), max(self.root.winfo_height(), 360)
        W = min(640, rw - 40)
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.overrideredirect(True)
        top.configure(bg=P["BLK"])
        try:
            top.attributes("-topmost", True)
        except Exception:
            pass
        self.pal_win, self.pal_rows, self.pal_sel, self.pal_off, self.pal_W, self.pal_P = top, [], 0, 0, W, P
        frame = tk.Frame(top, bg=P["PNL"], highlightthickness=0, bd=0)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        self.pal_box = Box(frame, fill=P["PNL2"], outline=P["GRID"], padx=12, pady=8, left=22, pbg=P["PNL"])
        self.pal_box.icon = P["DIM"]
        self.pal_box.pack(fill="x", padx=12, pady=(12, 6))
        self.pal_var = tk.StringVar(value=text)
        self.pal_entry = tk.Entry(self.pal_box.inner, textvariable=self.pal_var, bg=P["PNL2"], fg=P["TXT"], insertbackground=P["GOLD"], relief="flat", bd=0, highlightthickness=0,
                                  font=fonts["ui"], selectbackground=P["HOVER"], selectforeground=P["TXT"])
        self.pal_entry.pack(fill="x", ipady=4)
        self.pal_hold = tk.Label(self.pal_box.inner, text=self.T("pal_ph"), bg=P["PNL2"], fg=P["DIM"], font=fonts["ui"], anchor="w", cursor="xterm")
        self.pal_hold.bind("<Button-1>", lambda ev: self.pal_entry.focus_force())
        self.pal_box.focus_ring(self.pal_entry, P["GOLD"], P["GRID"])
        self.pal_cv = tk.Canvas(frame, bg=P["PNL"], highlightthickness=0, bd=0, width=W - 4, height=ROWS * ROW_H)
        self.pal_cv.pack(fill="x", padx=0, pady=(0, 0))
        self.pal_foot = tk.Label(frame, text=cap(self.T("pal_hint")) if st.get("caps") else self.T("pal_hint"), bg=P["PNL"], fg=P["DIM"], font=fonts["small"], anchor="w")
        self.pal_foot.pack(fill="x", padx=16, pady=(4, 10))
        e = self.pal_entry
        e.bind("<Down>", lambda ev: self.pal_move(1) or "break")
        e.bind("<Up>", lambda ev: self.pal_move(-1) or "break")
        e.bind("<Next>", lambda ev: self.pal_move(ROWS) or "break")
        e.bind("<Prior>", lambda ev: self.pal_move(-ROWS) or "break")
        e.bind("<Return>", lambda ev: self.pal_run() or "break")
        e.bind("<KP_Enter>", lambda ev: self.pal_run() or "break")
        e.bind("<Escape>", lambda ev: self.pal_close() or "break")
        e.bind("<Control-k>", self.pal_toggle)
        e.bind("<Control-K>", self.pal_toggle)
        e.bind("<KeyRelease>", lambda ev: self.pal_later())
        self.pal_cv.bind("<Button-1>", self.pal_click)
        self.pal_cv.bind("<Motion>", self.pal_hover)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.pal_cv.bind(seq, self.pal_wheel)
            e.bind(seq, self.pal_wheel)
        top.bind("<FocusOut>", lambda ev: self.pal_lost())
        self.pal_job = None
        self.pal_refresh(keep=False)
        self.pal_xy = (self.root.winfo_rootx() + max(0, (rw - W) // 2), self.root.winfo_rooty() + max(20, int(rh * 0.12)))
        self.pal_size()
        top.deiconify()
        top.after(40, self.pal_size)                                    # the height again once the field and the list have their real size
        top.lift()
        try:
            top.focus_force()
            e.focus_force()
            e.icursor("end")
        except Exception:
            pass
        if AN is not None:
            AN.note("palette")

    def pal_size(self):
        if not self.pal_visible():
            return
        try:
            self.pal_win.update_idletasks()
            h = self.pal_win.winfo_reqheight()
            self.pal_win.geometry("%dx%d+%d+%d" % (self.pal_W, h, self.pal_xy[0], self.pal_xy[1]))
        except Exception:
            pass

    def pal_close(self, *_a):
        w = getattr(self, "pal_win", None)
        self.pal_win = None
        job = getattr(self, "pal_job", None)
        self.pal_job = None
        if w is not None:
            try:
                if job:
                    w.after_cancel(job)
                w.destroy()
            except Exception:
                pass
        try:
            self.root.focus_set()
        except Exception:
            pass

    def pal_lost(self):
        """Focus left the box (another window, a click outside): close it - after a moment, since focus passes through the entry when it opens."""
        w = getattr(self, "pal_win", None)
        if w is None:
            return

        def check():
            if not self.pal_visible():
                return
            try:
                f = self.root.focus_get()
                if f is not None and str(f).startswith(str(self.pal_win)):
                    return
            except Exception:
                pass
            self.pal_close()
        try:
            w.after(160, check)
        except Exception:
            pass

    def pal_later(self):
        if getattr(self, "pal_job", None) or not self.pal_visible():
            return
        self.pal_job = self.pal_win.after(70, self.pal_refresh)

    def pal_refresh(self, keep=True):
        self.pal_job = None
        if not self.pal_visible():
            return
        try:
            rows = self.pal_find(self.pal_var.get())
        except Exception as ex:
            log("palette find: %r" % (ex,))
            rows = []
        self.pal_rows = rows
        try:
            if self.pal_var.get():
                self.pal_hold.place_forget()
            else:
                self.pal_hold.place(in_=self.pal_entry, x=2, rely=0.5, anchor="w")
        except Exception:
            pass
        self.pal_sel = 0 if not keep else min(self.pal_sel, max(0, len(rows) - 1))
        self.pal_off = 0
        self.pal_pick_first()
        self.pal_draw()

    def pal_pick_first(self):
        """The selection never rests on a heading."""
        n = len(self.pal_rows)
        i = max(0, min(self.pal_sel, n - 1)) if n else 0
        while i < n and self.pal_rows[i]["kind"] == "head":
            i += 1
        self.pal_sel = min(i, n - 1) if n else 0

    def pal_move(self, d):
        n = len(self.pal_rows)
        if not n:
            return True
        step = 1 if d > 0 else -1
        i = self.pal_sel
        for _ in range(abs(d)):
            j = i + step
            while 0 <= j < n and self.pal_rows[j]["kind"] == "head":
                j += step
            if 0 <= j < n:
                i = j
        self.pal_sel = i
        self.pal_scroll_to(i)
        self.pal_draw()
        return True

    def pal_scroll_to(self, i):
        n = len(self.pal_rows)
        if i < self.pal_off:
            self.pal_off = i
            if self.pal_off > 0 and self.pal_rows[self.pal_off - 1]["kind"] == "head":      # the heading of the group stays in view
                self.pal_off -= 1
        elif i >= self.pal_off + ROWS:
            self.pal_off = i - ROWS + 1
        self.pal_off = max(0, min(self.pal_off, max(0, n - ROWS)))

    def pal_wheel(self, e):
        d = -1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1
        self.pal_off = max(0, min(self.pal_off + d * 2, max(0, len(self.pal_rows) - ROWS)))
        self.pal_draw()
        return "break"

    def pal_index_at(self, y):
        i = self.pal_off + int(y // ROW_H)
        return i if 0 <= i < len(self.pal_rows) else -1

    def pal_hover(self, e):
        i = self.pal_index_at(e.y)
        if i >= 0 and self.pal_rows[i]["kind"] != "head" and i != self.pal_sel:
            self.pal_sel = i
            self.pal_draw()

    def pal_click(self, e):
        i = self.pal_index_at(e.y)
        if i >= 0 and self.pal_rows[i]["kind"] != "head":
            self.pal_sel = i
            self.pal_run()

    def pal_run(self):
        if not self.pal_rows or not (0 <= self.pal_sel < len(self.pal_rows)):
            return True
        row = self.pal_rows[self.pal_sel]
        if row["kind"] == "head":
            return True
        kind, title = row["kind"], row["title"]
        self.pal_close()
        if AN is not None:
            AN.note("palette_run", {"kind": kind})
        try:
            self.root.after(30, row["run"])                      # after the box is gone, so that a page or a theme switch is not drawn under it
        except Exception as ex:
            log("palette run %s: %r" % (title, ex))
        return True

    # ------------------------------------------------------------------ drawing
    def pal_draw(self):
        cv = self.pal_cv
        if not self.pal_visible():
            return
        P, F, W = self.pal_P, self.pal_fonts, self.pal_W - 4
        st = P["STYLE"]
        cv.delete("all")
        cv.configure(bg=P["PNL"])
        rows = self.pal_rows
        if not rows:
            cv.create_text(W / 2.0, ROWS * ROW_H / 2.0 - 10, text=self.T("pal_none"), fill=P["DIM"], font=F["ui"])
            return
        for k in range(ROWS):
            i = self.pal_off + k
            if i >= len(rows):
                break
            r = rows[i]
            y0 = k * ROW_H
            if r["kind"] == "head":
                cv.create_text(18, y0 + ROW_H - 12, text=cap(r["title"]), fill=P["GOLD"], font=F["small"], anchor="w")
                cv.create_line(18 + F["small"].measure(r["title"]) + 30, y0 + ROW_H - 12, W - 18, y0 + ROW_H - 12, fill=P["GRID"])
                continue
            sel = i == self.pal_sel
            x1, x2, y1, y2 = 10, W - 10, y0 + 3, y0 + ROW_H - 3
            if sel:
                draw_shape(cv, x1, y1, x2, y2, fill=P["HOVER"], outline="", shape=st["btn"], r=st["r"])
                if st.get("glow"):
                    neon(cv, x1, y1, x2, y2, P["GOLD"], P["PNL"], shape=st["btn"], r=st["r"], level=1, width=1)
                else:
                    cv.create_rectangle(x1, y1 + 6, x1 + 3, y2 - 6, fill=P["GOLD"], outline="")
            ic = r.get("icon") or {"song": "note", "group": "folder", "page": "wave", "action": "gear"}.get(r["kind"], "note")
            try:
                draw_icon(cv, ic, 34, (y1 + y2) / 2.0, 16, P["GOLD"] if sel else P["DIM"])
            except Exception:
                cv.create_oval(28, (y1 + y2) / 2.0 - 4, 36, (y1 + y2) / 2.0 + 4, fill=P["DIM"], outline="")
            hint = str(r.get("hint") or "")
            hw = F["small"].measure(hint) + 16 if hint else 0
            tx = 54
            maxw = x2 - tx - hw - 12
            title = self.pal_fit(F["ui_b"] if sel else F["ui"], r["title"], maxw)
            if r.get("sub"):
                cv.create_text(tx, y1 + 11, text=title, fill=P["TXT"], font=F["ui_b"] if sel else F["ui"], anchor="w")
                cv.create_text(tx, y1 + 28, text=self.pal_fit(F["small"], r["sub"], maxw), fill=P["DIM"], font=F["small"], anchor="w")
            else:
                cv.create_text(tx, (y1 + y2) / 2.0, text=title, fill=P["TXT"], font=F["ui_b"] if sel else F["ui"], anchor="w")
            if hint:
                draw_shape(cv, x2 - hw - 6, (y1 + y2) / 2.0 - 11, x2 - 6, (y1 + y2) / 2.0 + 11, fill=P["PNL2"], outline=P["GRID"], shape=st["btn"], r=min(st["r"], 8))
                cv.create_text(x2 - 6 - hw / 2.0, (y1 + y2) / 2.0, text=hint, fill=P["DIM"], font=F["small"])
        n = len(rows)
        if n > ROWS:                                                  # a thin scroll bar at the right edge
            frac = ROWS / float(n)
            top = self.pal_off / float(n)
            cv.create_rectangle(W - 5, 4 + top * (ROWS * ROW_H - 8), W - 2, 4 + (top + frac) * (ROWS * ROW_H - 8), fill=P["GRID"], outline="")

    @staticmethod
    def pal_fit(font, s, maxw):
        s = str(s)
        if maxw <= 20 or font.measure(s) <= maxw:
            return s
        while s and font.measure(s + "…") > maxw:
            s = s[:-1]
        return s + "…"


def _bind_keys(app):
    """Ctrl+K opens / closes the box from anywhere in the window (a text field inside it too: its own 'delete to end of line' is replaced by this)."""
    for seq in ("<Control-k>", "<Control-K>"):
        try:
            app.root.bind_all(seq, app.pal_toggle)
            app.root.bind_class("Entry", seq, app.pal_toggle)
        except Exception as e:
            log("palette key: %r" % (e,))


def register(app):
    app.pal_win, app.pal_rows, app.pal_sel, app.pal_off, app.pal_job = None, [], 0, 0, None
    app.add_texts(**TEXTS)
    app.add_menu("palette_menu", lambda a: a.root.after(60, a.pal_open))
    app.add_build(_bind_keys)
    app.add_relabel(lambda a: a.pal_close() if a.pal_visible() else None)


# END-OF-FILE rofpalys_gui_palette.py
