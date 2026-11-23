#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Spotify-style pages - square cards (Songs, Mix, Artists, Playlists), playlist / artist / favorites pages
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""The pages of the library are drawn on the SAME canvas as the Home page (rofpalys_gui_home.py: scrolling, hover, clicks, the look in use):
  grid     Songs / Mix / Artists / Playlists: a grid of square cards (cover, title, subtitle); the play button shows on the card when the pointer is over it
  detail   a playlist, a mix, a folder or Favorites: a header with a big cover, the buttons (play, shuffle, add songs, more) and the numbered song list
  artist   the page of one artist: a banner with the name, Popular songs, all songs as cards and the playlists the artist appears in
Long pages are virtual: only the cards / rows that are on screen (plus a little more) exist as canvas items, so 5 000 songs scroll as smoothly as 50.
A feature file plugs into the window with register(app) and brings its methods in the Mixin class (see rofpalys_gui_template.py)."""
import bisect
import os
import random
import time
import zlib

from rofpalys_gui_base import *   # noqa: F401,F403

FEATURE = {"name": "browse", "title": "Spotify-style pages: square cards, playlist and artist pages", "version": "1.0", "order": 15, "enabled": True}
CARD_PAD = 12
ROW_H = 60


def _t(text):
    return I18N.tr(text)


class Mixin:
    # ------------------------------------------------------------------ which page is on
    def pg_kind(self):
        """'' = the list (search results, the 'List' layout of Home), else 'home' | 'grid' | 'detail' | 'artist'."""
        if self.view != "library" or self.query():
            return ""
        g = self.gmap.get(self.group) if self.group else None
        if g is not None:
            return "artist" if g["kind"] == "artist" else "detail"
        if self.chip == "home":
            return "home" if self.hm_layout() != "list" else ""
        if self.chip == "favorites":
            return "detail"
        return "grid"

    # ------------------------------------------------------------------ the virtual page: units are added where they belong, drawn when they come on screen
    def bw_reset(self):
        self.bw_units, self.bw_ys, self.bw_drawn, self.bw_maxh, self._bw_n = [], [], {}, 0, 0

    def bw_refresh(self):
        """Pictures arrived / the song changed / a heart was pressed: the units on screen are drawn again (the layout stays)."""
        cv = self.hm_cv
        for uid in list(self.bw_drawn):
            cv.delete("u%d" % uid)
        self.bw_drawn = {}
        self._hm_hover = -1
        cv.delete("hov")
        self.bw_visible()

    def bw_unit(self, x1, y1, x2, y2, draw, act=None, item=None, hover=None, **kw):
        self._bw_n += 1
        u = dict(id=self._bw_n, x1=x1, y1=y1, x2=x2, y2=y2, draw=draw, item=item, hover=hover, shape=STYLE["shape"], r=self.hm_rr(), tag="", pr=None)
        u.update(kw)
        u["act"] = (lambda x, y, u=u: act(u, x, y)) if act else None
        self.bw_units.append(u)
        return u

    def bw_finish(self, W, y, top):
        cv = self.hm_cv
        self.bw_units.sort(key=lambda u: u["y1"])
        self.bw_ys = [u["y1"] for u in self.bw_units]
        self.bw_maxh = max([u["y2"] - u["y1"] for u in self.bw_units] or [0])
        cv.configure(scrollregion=(0, 0, W, max(int(y), int(cv.winfo_height()))))
        cv.yview_moveto(max(0.0, top / float(max(1, y))))
        self._bw_run()

    def hm_yscroll(self, lo, hi):
        if getattr(self, "bw_units", None) and not self._bw_job:
            self._bw_job = self.root.after_idle(self._bw_run)

    def _bw_run(self):
        self._bw_job = None
        try:
            self.bw_visible()
        except Exception as e:
            log("browse visible: %r" % (e,))

    def bw_visible(self):
        cv = self.hm_cv
        if not self.bw_units or not self._hm_on:
            return
        top = cv.canvasy(0)
        bot = top + max(200, int(cv.winfo_height()))
        m = 420
        lo = bisect.bisect_left(self.bw_ys, top - m - self.bw_maxh)
        hi = bisect.bisect_right(self.bw_ys, bot + m)
        for u in self.bw_units[lo:hi]:
            if u["id"] not in self.bw_drawn and u["y2"] >= top - m and u["y1"] <= bot + m:
                a = cv.create_text(-50, -50, text="")
                try:
                    u["draw"](u)
                except Exception as e:
                    log("browse unit: %r" % (e,))
                b = cv.create_text(-50, -50, text="")
                tag = "u%d" % u["id"]
                for i in range(a, b + 1):
                    cv.addtag_withtag(tag, i)
                self.bw_drawn[u["id"]] = u
        for uid, u in list(self.bw_drawn.items()):
            if u["y2"] < top - 3 * m or u["y1"] > bot + 3 * m:
                cv.delete("u%d" % uid)
                del self.bw_drawn[uid]

    def bw_unit_at(self, x, y):
        if not getattr(self, "bw_units", None):
            return None
        i = bisect.bisect_right(self.bw_ys, y) - 1
        while i >= 0 and self.bw_ys[i] >= y - self.bw_maxh:
            u = self.bw_units[i]
            if u["x1"] <= x <= u["x2"] and u["y1"] <= y <= u["y2"]:
                return u
            i -= 1
        return None

    # ------------------------------------------------------------------ small helpers
    def bw_fit(self, text, font, maxw):
        if maxw < 24:
            return ""
        if font.measure(text) <= maxw:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= maxw:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"

    def bw_gradient(self, x1, y1, x2, y2, top, bottom, steps=16):
        cv = self.hm_cv
        h = (y2 - y1) / float(steps)
        for i in range(steps):
            cv.create_rectangle(x1, y1 + i * h, x2, y1 + (i + 1) * h + 1, fill=lerp(top, bottom, i / float(max(1, steps - 1))), outline="")

    def bw_tint(self, seed):
        """A colour for the banner of a page: one of the cover shades of the look in use, made a little brighter."""
        return lerp(PNL, COVER_SHADES[zlib.crc32((seed or "?").encode("utf-8", "replace")) % len(COVER_SHADES)], 0.9)

    def bw_circle_btn(self, cx, cy, r, icon, fill, fg, act, item=None, size=None):
        cv = self.hm_cv
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline="")
        if STYLE["glow"] and fill == GOLD:
            cv.create_oval(cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2, outline=INFO, width=1)
        draw_icon(cv, icon, cx + (1 if icon == "play" else 0), cy, size or int(r * 0.9), fg)
        self.hm_hit(cx - r, cy - r, cx + r, cy + r, act, item=item, shape="round", r=r)

    def bw_back(self, x, y):
        """The round back arrow at the top of a page."""
        self.bw_circle_btn(x + 18, y + 18, 18, "back", lerp(PNL, BLK, 0.45), TXT, lambda a, b: self.close_group(), size=16)

    # ------------------------------------------------------------------ covers
    def bw_cover(self, x, y, size, path, title, behind):
        """A song cover cut to a square (a wide video picture is cropped from the middle) with the corners of the look in use."""
        cv = self.hm_cv
        sz = max(16, (int(size) // 16) * 16)
        img = self.thumb_image(path, sz, square=True) if path else None
        if img is not None:
            ox = (size - sz) / 2.0
            cv.create_image(x + ox + sz / 2.0, y + ox + sz / 2.0, image=img)
            self.hm_mask(x + ox, y + ox, x + ox + sz, y + ox + sz, behind, STYLE["shape"], 8 if STYLE["shape"] != "flat" else 0)
        else:
            self.draw_square(cv, x, y, int(size), title or "?", "song")

    def bw_group_cover(self, x, y, size, it, behind):
        cv = self.hm_cv
        size = int(size)
        photo = it.get("photo") or ""
        if photo and os.path.isfile(photo):
            sz = max(16, (size // 16) * 16)
            p = M.get_scaled(photo, sz, True)
            img = self.photo(p) if p else None
            if img is not None:
                ox = (size - sz) / 2.0
                cv.create_image(x + ox + sz / 2.0, y + ox + sz / 2.0, image=img)
                self.hm_mask(x + ox, y + ox, x + ox + sz, y + ox + sz, behind, STYLE["shape"], 8 if STYLE["shape"] != "flat" else 0)
                return
        seen, picks = set(), []
        for p in it.get("cover", [])[:10]:
            a = M.art_of(p)
            if a and a not in seen:
                seen.add(a)
                picks.append(p)
            if len(picks) == 4:
                break
        rr = 8 if STYLE["shape"] != "flat" else 0
        if len(picks) == 4:
            h = max(32, ((size // 2) // 8) * 8)
            imgs = [self.thumb_image(p, h, square=True) for p in picks]
            if all(imgs):
                off = (size - 2 * h) / 2.0
                for k, img in enumerate(imgs):
                    cv.create_image(x + off + (k % 2) * h + h / 2.0, y + off + (k // 2) * h + h / 2.0, image=img)
                self.hm_mask(x + off, y + off, x + off + 2 * h, y + off + 2 * h, behind, STYLE["shape"], rr)
                return
        if picks:
            self.bw_cover(x, y, size, picks[0], it["title"], behind)
            return
        if it.get("gkind") == "playlist":                                   # a playlist without a picture: a tile with a note (the photo can be chosen)
            self.draw_square(cv, x, y, size, it["title"], "song")
            return
        self.draw_square(cv, x, y, size, it["title"], "group")

    # ------------------------------------------------------------------ a card
    def bw_card(self, u):
        cv, it = self.hm_cv, u["item"]
        x1, y1, x2, y2, cs = u["x1"], u["y1"], u["x2"], u["y2"], u["cs"]
        cw = x2 - x1
        self.hm_panel(x1, y1, x2, y2, CARD, glow=False)
        cx0, cy0 = x1 + (cw - cs) / 2.0, y1 + CARD_PAD
        kind = it["kind"]
        playing = kind == "song" and it["path"] == E.playing_song_name
        if kind == "song":
            self.bw_cover(cx0, cy0, cs, it["path"], it["title"], CARD)
        elif kind == "group":
            self.bw_group_cover(cx0, cy0, cs, it, CARD)
        else:                                                               # an action card (New playlist ...): a plus on a plain tile
            draw_shape(cv, cx0, cy0, cx0 + cs, cy0 + cs, fill=PNL2, shape=STYLE["shape"], r=8)
            draw_icon(cv, "plus", cx0 + cs / 2.0, cy0 + cs / 2.0, cs * 0.34, GOLD)
        ty = cy0 + cs + 22
        cv.create_text(cx0, ty, text=self.fit(it["title"], "ui_b", int(cs)), fill=GOLD if playing else TXT, font=self.f_ui_b, anchor="w")
        cv.create_text(cx0, ty + 21, text=self.fit(it.get("sub", ""), "small", int(cs)), fill=DIM, font=self.f_small, anchor="w")
        if playing:
            cv.create_oval(cx0 + 8, cy0 + cs - 34, cx0 + 34, cy0 + cs - 8, fill=GOLD, outline="")
            draw_icon(cv, "wave", cx0 + 21, cy0 + cs - 21, 13, BLK)
        u["pr"] = (cx0 + cs - 52, cy0 + cs - 52, cx0 + cs - 8, cy0 + cs - 8) if kind != "action" else None

    def bw_card_hover(self, u):
        cv = self.hm_cv
        col = INFO if STYLE["glow"] else GOLD
        draw_shape(cv, u["x1"], u["y1"], u["x2"], u["y2"], outline=col if STYLE["glow"] else lerp(PNL2, TXT, 0.25), shape=STYLE["shape"], r=self.hm_rr(), width=2, tags="hov")
        if u["pr"]:
            a, b, c, d = u["pr"]
            bx, by = (a + c) / 2.0, (b + d) / 2.0
            cv.create_oval(a, b, c, d, fill=GOLD, outline="", tags="hov")
            on = u["item"]["kind"] == "song" and u["item"]["path"] == E.playing_song_name and E.is_playing and not E.is_paused
            self.bw_icon_tag(bx + (0 if on else 1), by, "pause" if on else "play", 16, BLK)

    def bw_icon_tag(self, cx, cy, kind, size, color):
        """An icon that lives in the 'hov' layer (it goes away with the hover)."""
        cv = self.hm_cv
        a = cv.create_text(-50, -50, text="")
        draw_icon(cv, kind, cx, cy, size, color)
        b = cv.create_text(-50, -50, text="")
        for i in range(a, b + 1):
            cv.addtag_withtag("hov", i)

    def bw_card_click(self, u, x, y):
        it = u["item"]
        if u["pr"] and u["pr"][0] <= x <= u["pr"][2] and u["pr"][1] <= y <= u["pr"][3]:
            if it["kind"] == "song":
                if it["path"] == E.playing_song_name:
                    self.toggle()
                else:
                    self.play(it["path"])
            else:
                self.bw_play_paths(self.sorted_paths(it.get("paths", [])))
            return
        self.on_row_activate(it)

    def bw_play_paths(self, paths, start=0, shuffle=False):
        paths = [p for p in paths if p]
        if not paths:
            self.msg(self.T("pl_nothing"))
            return
        if shuffle:
            paths = random.sample(paths, len(paths))
            start = 0
        E.queue_clear()
        E.queue_add(paths[start + 1:])
        self.play(paths[start])

    # ------------------------------------------------------------------ a song row
    def bw_row(self, u):
        cv, it = self.hm_cv, u["item"]
        x1, y1, x2, y2 = u["x1"], u["y1"], u["x2"], u["y2"]
        p = it["path"]
        playing = p == E.playing_song_name
        mid = (y1 + y2) / 2.0
        wide = x2 - x1 >= 640
        num_x = x1 + 22
        if u.get("mode") == "add":
            num_x = None
        if num_x is not None:
            if playing:
                draw_icon(cv, "wave", num_x, mid, 14, GOLD)
            else:
                cv.create_text(num_x, mid, text=str(u["no"]), fill=DIM, font=self.f_ui)
            cx0 = x1 + 48
        else:
            cx0 = x1 + 10
        cs = 48
        self.bw_cover(cx0, mid - cs / 2.0, cs, p, it["title"], PNL)
        tx = cx0 + cs + 14
        right = x2 - (92 if u.get("mode") != "add" else 54)
        plays = it.get("right", "")
        if wide and plays and u.get("mode") != "add":
            cv.create_text(right - 14, mid, text=plays, fill=DIM, font=self.f_small, anchor="e")
            right -= 90
        tw = max(40, right - tx - 8)
        cv.create_text(tx, mid - 10, text=self.fit(it["title"], "ui_b", int(tw)), fill=GOLD if playing else TXT, font=self.f_ui_b, anchor="w")
        cv.create_text(tx, mid + 11, text=self.fit(it["sub"], "small", int(tw)), fill=DIM, font=self.f_small, anchor="w")
        if u.get("mode") == "add":
            have = p in u["have"]
            draw_icon(cv, "check_circle" if have else "plus_circle", x2 - 26, mid, 22, GOLD if have else DIM)
        else:
            fav = p in E.favorites
            draw_icon(cv, "heart_on" if fav else "heart", x2 - 70, mid, 16, RED if fav else DIM)
            draw_icon(cv, "dots", x2 - 26, mid, 18, DIM)

    def bw_row_hover(self, u):
        cv = self.hm_cv
        x1, y1, x2, y2 = u["x1"], u["y1"], u["x2"], u["y2"]
        plate = ROW_HOVER if not STYLE["glow"] else lerp(PNL, BRN2, 0.12)
        draw_shape(cv, x1, y1 + 2, x2, y2 - 2, fill=plate, outline=BRN2 if STYLE["glow"] else "", shape=STYLE["shape"], r=max(0, self.hm_rr() - 4), tags=("hov", "hp"))
        cv.tag_lower("hp")                                                      # the plate goes under the texts of the row
        if u.get("mode") != "add" and u["item"]["path"] != E.playing_song_name:
            mid = (y1 + y2) / 2.0
            cv.create_rectangle(x1 + 8, mid - 12, x1 + 38, mid + 12, fill=plate, outline="", tags="hov")
            self.bw_icon_tag(x1 + 23, mid, "play", 13, TXT)

    def bw_row_click(self, u, x, y):
        p = u["item"]["path"]
        if u.get("mode") == "add":
            if x >= u["x2"] - 56:
                self.bw_toggle_add(u)
            else:
                self.play(p)
            return
        if x >= u["x2"] - 46:
            self.sheet_song(p, x_root=self.hm_cv.winfo_rootx() + int(x - self.hm_cv.canvasx(0)), y_root=self.hm_cv.winfo_rooty() + int(y - self.hm_cv.canvasy(0)))
        elif x >= u["x2"] - 90:
            self.toggle_fav(p)
            self._hm_sig = None
        else:
            self.bw_play_paths(u["paths"], start=u["no"] - 1)

    def bw_toggle_add(self, u):
        pid = self.pl_id()
        p = u["item"]["path"]
        if not pid:
            return
        PL.add(pid, [p])
        self.msg(self.T("pl_added_n") % 1)
        self.pl_refresh()

    def bw_rows(self, x1, x2, y, paths, mode="", have=(), limit=None):
        """Song rows (virtual units). Returns the y below the last row."""
        no = 0
        for p in paths[:limit] if limit else paths:
            no += 1
            it = self.song_item(p)
            self.bw_unit(x1, y, x2, y + ROW_H, self.bw_row, act=self.bw_row_click, item=it, hover=self.bw_row_hover, no=no, paths=paths, mode=mode, have=set(have),
                         shape="flat", r=0, tag="row")
            y += ROW_H
        return y

    # ------------------------------------------------------------------ the page: draw
    def bw_draw(self, kind):
        cv = self.hm_cv
        W = int(cv.winfo_width())
        if W < 120:
            return
        key = (kind, self.chip, self.group)
        top = cv.canvasy(0) if key == getattr(self, "_bw_key", None) else 0
        self._bw_key = key
        cv.configure(bg=PNL, yscrollincrement=24)
        cv.delete("all")
        self.hm_hits, self._hm_hover, self._hm_np_box = [], -1, None
        self.bw_reset()
        pad = 24 if W >= 700 else 14
        fn = {"grid": self.bw_page_grid, "detail": self.bw_page_detail, "artist": self.bw_page_artist}[kind]
        y = fn(W, pad)
        self.bw_finish(W, y + pad + 24, top)
        self._hm_sig = self.hm_sig()
        self._hm_next = time.time() + 0.5

    def bw_metrics(self, W, pad):
        gap = 16 if W >= 700 else 10
        avail = W - 2 * pad
        minw = 178 if W >= 1000 else (160 if W >= 700 else 150)
        cols = max(2, int((avail + gap) // (minw + gap)))
        cw = (avail - gap * (cols - 1)) / float(cols)
        cs = max(64, (int(cw - 2 * CARD_PAD) // 16) * 16)
        return cols, cw, cs, gap

    def bw_cards(self, x1, y, items, W, pad):
        """The cards of `items` in a grid, from y down; returns the y below."""
        cols, cw, cs, gap = self.bw_metrics(W, pad)
        h = CARD_PAD + cs + 62
        for k, it in enumerate(items):
            col, row = k % cols, k // cols
            a = x1 + col * (cw + gap)
            b = y + row * (h + gap)
            self.bw_unit(a, b, a + cw, b + h, self.bw_card, act=self.bw_card_click, item=it, hover=self.bw_card_hover, cs=cs)
        rows = (len(items) + cols - 1) // cols
        return y + rows * (h + gap)

    def bw_heading(self, x, y, text, sub=""):
        cv = self.hm_cv
        cv.create_text(x, y + 14, text=cap(text) if STYLE["caps"] else text, fill=TXT, font=self.hm_font(-21), anchor="w")
        if sub:
            cv.create_text(x + self.hm_font(-21).measure(text) + 14, y + 16, text=sub, fill=DIM, font=self.f_small, anchor="w")
        return y + 38

    def bw_page_grid(self, W, pad):
        cv = self.hm_cv
        labels = dict(self.chip_labels())
        title = self.T(labels.get(self.chip, self.chip))
        items = self.page_items()
        cards = [it for it in items if it["kind"] in ("song", "group", "action")]
        n = len([it for it in cards if it["kind"] != "action"])
        what = {"songs": "songs", "artists": "artists", "playlists": "playlists"}.get(self.chip, "")
        y = pad - 4
        cv.create_text(pad, y + 22, text=cap(title) if STYLE["caps"] else title, fill=TXT, font=self.hm_font(-34), anchor="w")
        cv.create_text(pad, y + 54, text=("%d %s" % (n, self.T(what))) if what else ("%d" % n), fill=DIM, font=self.f_ui, anchor="w")
        y += 78
        if not [it for it in cards if it["kind"] != "action"]:                      # nothing yet: the texts of the page (or the plain "empty" text) and the action cards
            lines = [it["title"] for it in items if it["kind"] == "header"] or [self.empty_text()]
            for ln in lines:
                cv.create_text(pad, y + 14, text=ln, fill=DIM, font=self.f_ui, anchor="nw", width=max(120, W - 2 * pad))
                y += 30 + 18 * (len(ln) * 8 // max(120, W - 2 * pad))
            acts = [it for it in cards if it["kind"] == "action"]
            if acts:
                y = self.bw_cards(pad, y + 6, acts, W, pad)
            return y + 20
        run = []
        for it in items:
            if it["kind"] == "header":
                if run:
                    y = self.bw_cards(pad, y, run, W, pad)
                    run = []
                y = self.bw_heading(pad, y + 4, it["title"])
            elif it["kind"] in ("song", "group", "action"):
                run.append(it)
        if run:
            y = self.bw_cards(pad, y, run, W, pad)
        return y

    # ------------------------------------------------------------------ playlist / mix / folder / favorites page
    def bw_detail_info(self):
        """(title, kind label, paths, group dict or None, cover item) of the page."""
        g = self.gmap.get(self.group) if self.group else None
        if g is None:                                                           # Favorites
            paths = self.sorted_paths([p for p in E.songs_all if p in E.favorites])
            return self.T("favorites"), "", paths, None
        return g["name"], self.T(self.kind_labels.get(g["kind"], "folder")), self.sorted_paths(g["paths"]), g

    def bw_page_detail(self, W, pad):
        cv, T = self.hm_cv, self.T
        title, kind_lab, paths, g = self.bw_detail_info()
        is_pl = bool(g and g["kind"] == "playlist")
        st = self.cfg["stats"]
        plays = sum(st.get(p, {}).get("plays", 0) for p in paths)
        narrow = W < 640
        tint = self.bw_tint(title)
        cs = 120 if narrow else 208
        hh = (cs + 182) if narrow else cs + 92                              # narrow: cover, then kind label, title and numbers under it
        self.bw_gradient(0, 0, W, hh, tint, PNL)
        if g is not None:
            self.bw_back(pad, 12)
        cx0, cy0 = (W - cs) / 2.0 if narrow else pad, 58 if not narrow else 54
        it = self.group_item(g) if g is not None else {"title": title, "cover": paths[:8], "paths": paths, "kind": "group", "gkind": "favorites"}
        if g is None:                                                           # Favorites: a heart tile in the colours of the look
            self.bw_gradient(cx0, cy0, cx0 + cs, cy0 + cs, BRN, INFO if STYLE["glow"] else GOLD, 10)
            self.hm_heart(cx0 + cs / 2.0, cy0 + cs / 2.0 - 2, cs * 0.50, fill=BLK if not STYLE["glow"] else BLK)
            self.hm_mask(cx0, cy0, cx0 + cs, cy0 + cs, tint, STYLE["shape"], 8 if STYLE["shape"] != "flat" else 0)
        else:
            self.bw_group_cover(cx0, cy0, cs, it, tint)
            if is_pl:
                self.bw_photo_hint(cx0, cy0, cs, g)
        if narrow:
            tx, tw = pad, W - 2 * pad
        else:
            tx, tw = cx0 + cs + 26, W - (cx0 + cs + 26) - pad
        kl = kind_lab or (T("favorites") if g is None else "")
        size = 38 if narrow else 56
        f = self.hm_font(-size)
        room = tw - (90 if is_pl else 0)
        while f.measure(title) > room and size > 22:
            size -= 2
            f = self.hm_font(-size)
        block = 18 + 8 + int(size * 1.25) + 12 + 20                          # kind label, gap, title, gap, numbers
        ty0 = (cy0 + cs + 16) if narrow else (cy0 + cs - block)
        cv.create_text(tx, ty0 + 9, text=cap(_t("Playlist") if g is None else kl), fill=TXT, font=self.f_ui_b, anchor="w")
        tmid = ty0 + 26 + size * 0.62
        cv.create_text(tx, tmid, text=self.bw_fit(title, f, room), fill=TXT, font=f, anchor="w")
        if is_pl:
            bx = tx + min(f.measure(title), room) + 16
            self.hm_button(bx, tmid - 15, 62, 30, _t("Edit"), lambda x, y, gg=g: self.pl_edit_dialog(gg["pid"]), filled=False)
        meta = "%d %s" % (len(paths), T("songs")) + ("   •   %d %s" % (plays, _t("plays")) if plays else "")
        cv.create_text(tx, ty0 + 26 + size * 1.25 + 14, text=meta, fill=lerp(TXT, PNL, 0.3), font=self.f_ui, anchor="w")
        y = hh + 6
        # --- the buttons
        bx = pad
        on = bool(paths) and E.is_playing and not E.is_paused and E.playing_song_name in paths
        self.bw_circle_btn(bx + 28, y + 28, 28, "pause" if on else "play", GOLD, BLK,
                           lambda a, b, ps=paths: (self.toggle() if on else self.bw_play_paths(ps)), size=22)
        bx += 70
        self.bw_circle_btn(bx + 18, y + 28, 18, "shuffle", lerp(PNL, BLK, 0.0), GOLD if E.play_mode == 4 else TXT,
                           lambda a, b, ps=paths: self.bw_play_paths(ps, shuffle=True), size=18)
        bx += 52
        if is_pl:
            lab = _t("Add songs")
            wlab = self.mf["ui_b"].measure(lab) + 56
            self.hm_button(bx, y + 10, wlab, 36, lab, lambda a, b, gg=g: self.pl_add_songs_dialog(gg["pid"]), filled=False, icon="plus")
            bx += wlab + 12
        self.bw_circle_btn(bx + 18, y + 28, 18, "dots", lerp(PNL, BLK, 0.0), TXT, lambda a, b: self.bw_more_menu(a, b), size=18)
        y += 70
        if not paths:
            y = self.bw_empty_detail(W, pad, y, is_pl)
        else:
            if not narrow:
                cv.create_text(pad + 22, y + 12, text="#", fill=DIM, font=self.f_small, anchor="center")
                cv.create_text(pad + 48 + 54, y + 12, text=cap(_t("Title")), fill=DIM, font=self.f_small, anchor="w")
                if W - 2 * pad >= 640:
                    cv.create_text(W - pad - 104, y + 12, text=cap(_t("Plays")), fill=DIM, font=self.f_small, anchor="e")
                cv.create_line(pad, y + 26, W - pad, y + 26, fill=GRID)
                y += 32
            y = self.bw_rows(pad, W - pad, y, paths)
        if is_pl:                                                                   # "recommended songs": the ones that are not in the playlist yet
            y = self.bw_recommended(W, pad, y + 18, g, paths)
        return y

    def bw_photo_hint(self, x, y, s, g):
        """A pencil on the cover of a playlist (click = choose a photo); the whole cover is the button."""
        cv = self.hm_cv
        if not (g.get("photo") and os.path.isfile(g.get("photo"))) and not [p for p in g["paths"] if M.art_of(p)]:
            cv.create_oval(x + s / 2.0 - 24, y + s / 2.0 - 24, x + s / 2.0 + 24, y + s / 2.0 + 24, fill=PNL2, outline="")
            draw_icon(cv, "pencil", x + s / 2.0, y + s / 2.0, 22, TXT)
        self.hm_hit(x, y, x + s, y + s, lambda a, b, gg=g: self.pl_pick_photo(gg["pid"]), shape=STYLE["shape"], r=8)

    def bw_empty_detail(self, W, pad, y, is_pl):
        cv = self.hm_cv
        msg = _t("Let's find something for your playlist") if is_pl else self.empty_text()
        cv.create_text(pad, y + 18, text=msg, fill=TXT if is_pl else DIM, font=self.hm_font(-22) if is_pl else self.f_ui, anchor="w")
        return y + 48

    def recommend_for(self, paths, limit=8):
        """Songs of the library that are not in `paths` yet: first those of the artists already there, then the most played ones."""
        have = set(paths)
        st = self.cfg["stats"]
        arts = {self.song_item(p)["sub"] for p in paths}
        pool = [p for p in E.songs_all if p not in have]
        pool.sort(key=lambda p: (0 if self.song_item(p)["sub"] in arts else 1, -st.get(p, {}).get("plays", 0), p.lower()))
        return pool[:limit]

    def bw_recommended(self, W, pad, y, g, paths):
        """'Recommended songs' under a playlist: a + at the right adds a song at once."""
        rec = self.recommend_for(paths, 8)
        if not rec:
            return y
        y = self.bw_heading(pad, y, _t("Recommended songs"))
        self.hm_cv.create_text(pad, y - 4, text=_t("Based on what is in this playlist"), fill=DIM, font=self.f_small, anchor="w")
        y += 18
        y = self.bw_rows(pad, W - pad, y, rec, mode="add", have=set(paths))
        return y + 6

    def bw_more_menu(self, x, y):
        """The three dots of a page: what the page offers (rename, export ... for a playlist)."""
        g = self.gmap.get(self.group) if self.group else None
        items = []
        paths = list(g["paths"]) if g else [p for p in E.songs_all if p in E.favorites]
        items.append(("queue", _t("Add to Queue"), lambda: (E.queue_add(paths), self.msg(self.T("pl_added_n") % len(paths))) if paths else None))
        items.append(("plus_circle", _t("Add to playlist"), lambda: self.pl_pick_dialog(paths)))
        if g is not None:
            for label_key, cmd, kinds in self.head_button_defs:
                if g["kind"] in kinds and label_key != "add_to_pl":
                    items.append(("pencil" if label_key == "pl_rename" else "info", self.T(label_key), lambda c=cmd: c(self)))
        self.sheet_open(items, self.hm_cv.winfo_rootx() + int(x - self.hm_cv.canvasx(0)), self.hm_cv.winfo_rooty() + int(y - self.hm_cv.canvasy(0)))

    # ------------------------------------------------------------------ the page of an artist
    def bw_page_artist(self, W, pad):
        cv, T = self.hm_cv, self.T
        g = self.gmap.get(self.group)
        name, paths = g["name"], self.sorted_paths(g["paths"])
        st = self.cfg["stats"]
        plays = sum(st.get(p, {}).get("plays", 0) for p in paths)
        narrow = W < 640
        tint = self.bw_tint(name)
        hh = 250 if narrow else 300
        self.bw_gradient(0, 0, W, hh, lerp(tint, PNL, 0.0), PNL, 18)
        # the picture of the artist: a big cover on the right of a wide banner
        if not narrow:
            cs = 224
            cx0, cy0 = W - pad - cs - 10, 40
            self.bw_group_cover(cx0, cy0, cs, self.group_item(g), tint)
            if STYLE["glow"]:
                draw_shape(cv, cx0 - 2, cy0 - 2, cx0 + cs + 2, cy0 + cs + 2, outline=BRN2, shape=STYLE["shape"], r=8, width=1)
            tw = cx0 - pad - 30
        else:
            tw = W - 2 * pad
        self.bw_back(pad, 12)
        cv.create_text(pad, hh - 128, text=cap(self.T("artist")), fill=TXT, font=self.f_ui_b, anchor="w")
        size = 40 if narrow else 66
        f = self.hm_font(-size)
        while f.measure(name) > tw and size > 24:
            size -= 2
            f = self.hm_font(-size)
        cv.create_text(pad, hh - 84, text=self.bw_fit(name, f, tw), fill=TXT, font=f, anchor="w")
        meta = "%d %s" % (len(paths), T("songs")) + ("   •   %d %s" % (plays, _t("plays")) if plays else "")
        cv.create_text(pad, hh - 30, text=meta, fill=lerp(TXT, PNL, 0.25), font=self.f_ui, anchor="w")
        y = hh + 8
        on = bool(paths) and E.is_playing and not E.is_paused and E.playing_song_name in paths
        self.bw_circle_btn(pad + 28, y + 28, 28, "pause" if on else "play", GOLD, BLK, lambda a, b, ps=paths: (self.toggle() if on else self.bw_play_paths(ps)), size=22)
        self.bw_circle_btn(pad + 98, y + 28, 18, "shuffle", PNL, GOLD if E.play_mode == 4 else TXT, lambda a, b, ps=paths: self.bw_play_paths(ps, shuffle=True), size=18)
        self.bw_circle_btn(pad + 150, y + 28, 18, "dots", PNL, TXT, lambda a, b: self.bw_more_menu(a, b), size=18)
        y += 76
        # --- Popular: the most played songs of the artist (5; "Show more" opens 10)
        pop = sorted(paths, key=lambda p: (-st.get(p, {}).get("plays", 0), p.lower()))
        n = 10 if self.bw_more else 5
        y = self.bw_heading(pad, y, _t("Popular"))
        y = self.bw_rows(pad, W - pad, y, pop, limit=n)
        if len(pop) > 5:
            lab = _t("Show less") if self.bw_more else _t("Show more")
            cv.create_text(pad + 6, y + 18, text=lab, fill=DIM, font=self.f_ui_b, anchor="w")
            self.hm_hit(pad, y + 2, pad + self.mf["ui_b"].measure(lab) + 14, y + 34, lambda a, b: self.bw_toggle_more())
            y += 40
        # --- all songs as cards
        y = self.bw_heading(pad, y + 14, _t("Songs"))
        y = self.bw_cards(pad, y, [self.song_item(p) for p in paths], W, pad)
        # --- playlists / mixes that carry songs of this artist
        mine = set(paths)
        feat = [x for x in self.extra_groups if x.get("kind") in ("playlist", "mix") and mine & set(x["paths"])]
        if feat:
            y = self.bw_heading(pad, y + 10, _t("Appears in"))
            y = self.bw_cards(pad, y, [self.group_item(x) for x in feat[:12]], W, pad)
        return y

    def bw_toggle_more(self):
        self.bw_more = not self.bw_more
        self._hm_sig = None

    # ------------------------------------------------------------------ the song menu (three dots) and "open artist / album"
    def bw_artist_gids(self, p):
        """The artist pages that belong to a song: every name in front of the ' - ' of the file name ('A, B x C - Song' -> A, B, C) that has a page of its own."""
        out = []
        for nm in L.split_artists(p):
            gid = "artist:" + L.norm(nm)
            if gid in self.gmap and gid not in [o[1] for o in out]:
                out.append((nm, gid))
        return out

    def open_artist_of(self, p, x_root=None, y_root=None):
        found = self.bw_artist_gids(p)
        if not found:
            self.msg(_t("No artist page for this song"))
            return
        if len(found) == 1:
            self.open_group(found[0][1])
            return
        items = [("person", nm, lambda gid=gid: self.open_group(gid)) for nm, gid in found]
        self.sheet_open(items, x_root, y_root, title=_t("Artist"))

    def open_album_of(self, p):
        """'Album' = the folder the song lives in."""
        d = "dir:" + os.path.dirname(p)
        if d in self.gmap:
            self.open_group(d)
        else:
            self.msg(_t("No album page for this song"))

    def sheet_song(self, p, x_root=None, y_root=None):
        """The three-dot menu of a song: Add to playlist, Add to Queue, Open Queue, Open album, View artist (+ favorite, remove from this playlist)."""
        items = [("plus_circle", _t("Add to playlist"), lambda: self.pl_pick_dialog([p])),
                 ("queue", _t("Add to Queue"), lambda: (E.queue_add([p]), self.msg(_t("Added to the queue")))),
                 ("queue", _t("Open Queue"), lambda: self.go("queue")),
                 ("disc", _t("Open album"), lambda: self.open_album_of(p)),
                 ("person", _t("View artist"), lambda: self.open_artist_of(p, x_root, y_root))]
        fav = p in E.favorites
        items.append(("heart_on" if fav else "heart", _t("Remove from Favorites") if fav else _t("Add to Favorites"), lambda: self.toggle_fav(p)))
        if self.view == "library" and self.group.startswith("pl:") and not self.query():
            items.append(("close", _t("Remove from this playlist"), lambda: self.pl_remove(p)))
        self.sheet_open(items, x_root, y_root)

    def sheet_now(self):
        """The three dots of the Now Playing screen / the player bar."""
        p = E.playing_song_name
        if not p:
            self.msg(self.T("hm_nothing") if hasattr(self, "hm_nothing") else _t("Nothing playing"))
            return
        w = self.b_dots.cv if getattr(self, "b_dots", None) else self.root
        self.sheet_song(p, w.winfo_rootx(), w.winfo_rooty() + w.winfo_height() + 4)

    # ------------------------------------------------------------------ mouse (the canvas of the Home page calls these)
    def bw_hover(self, u):
        cv = self.hm_cv
        if u.get("hover"):
            u["hover"](u)
        else:
            draw_shape(cv, u["x1"], u["y1"], u["x2"], u["y2"], outline=INFO if STYLE["glow"] else GOLD, shape=u["shape"], r=u["r"], width=2, tags="hov")


def build_dots(app, bar):
    app.b_dots = IconBtn(bar, "dots", app.sheet_now, size=20, bg=PNL, pad=7)
    app.b_dots.pack(side="right")
    return [app.b_dots.cv]


def register(app):
    app.bw_units, app.bw_ys, app.bw_drawn, app.bw_maxh, app._bw_n, app._bw_job = [], [], {}, 0, 0, None
    app.bw_more, app._bw_key, app.b_dots = False, None, None
    app.add_toolbar(5, build_dots)                     # the three dots: the rightmost button of the Now Playing bar


# END-OF-FILE rofpalys_gui_browse.py
