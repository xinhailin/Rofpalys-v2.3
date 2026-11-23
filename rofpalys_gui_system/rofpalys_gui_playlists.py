#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: playlists = your own groups of songs
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""Playlists page (a tab in the library), "Add to playlist" everywhere, select many songs with check boxes, save a queue / search result /
folder as a playlist, rename / duplicate / export / delete. The storage and logic are in rofpalys_playlists.py; this file is only the screen part.
As on Spotify: you type the name of a new playlist in a box, a playlist can have its own photo (the pencil on its cover), "Add songs" opens a picker with search
and recommended songs, and "Save in" lists Favorites and your playlists with a tick for each."""
from rofpalys_gui_base import *   # noqa: F401,F403

FEATURE = {"name": "playlists", "title": "Playlists (your own groups of songs)", "version": "3.0", "order": 60, "enabled": True}
GROUP_KINDS = ("category", "folder", "artist", "mix")        # groups whose songs can be added to a playlist in one go
PICK_PAGE = 120                                               # rows the "Add songs" picker draws at once (more: type in the search box)


def _t(text):
    return I18N.tr(text)


class PickList:
    """A list drawn on a canvas for the dialogs (scrolls with the wheel or by dragging; a tap on a row calls on_click(row)).
    A row: {"key", "title", "sub", "cover": callable(cv, x, y, size) or None, "mark": "plus" | "check" | "on" | "off" | ""}."""

    def __init__(self, app, parent, height, on_click, row_h=58):
        self.app, self.on_click, self.row_h, self.rows, self.moved, self.y0 = app, on_click, row_h, [], False, 0
        self.cv = tk.Canvas(parent, bg=PNL2, highlightthickness=0, height=height, yscrollincrement=20)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.drag)
        self.cv.bind("<ButtonRelease-1>", self.release)
        for seq in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
            self.cv.bind(seq, self.wheel)

    def set(self, rows, keep_scroll=False):
        top = self.cv.canvasy(0) if keep_scroll else 0
        self.rows = rows
        self.draw()
        self.cv.yview_moveto(top / float(max(1, len(rows) * self.row_h)) if keep_scroll else 0)

    def draw(self):
        a, cv = self.app, self.cv
        cv.delete("all")
        w, rh = max(200, int(cv.winfo_width())), self.row_h
        for i, r in enumerate(self.rows):
            y = i * rh
            if r.get("cover"):
                r["cover"](cv, 4, y + (rh - 44) / 2.0, 44)
            tx = 4 + 44 + 14
            right = w - 56
            cv.create_text(tx, y + rh / 2.0 - 9, text=a.fit(r["title"], "ui_b", max(40, right - tx)), fill=GOLD if r.get("hot") else TXT, font=a.f_ui_b, anchor="w")
            if r.get("sub"):
                cv.create_text(tx, y + rh / 2.0 + 11, text=a.fit(r["sub"], "small", max(40, right - tx)), fill=DIM, font=a.f_small, anchor="w")
            mk, cx, cy = r.get("mark"), w - 26, y + rh / 2.0
            if mk == "plus":
                draw_icon(cv, "plus_circle", cx, cy, 24, DIM)
            elif mk == "check":
                draw_icon(cv, "check_circle", cx, cy, 24, GOLD)
            elif mk in ("on", "off"):
                cv.create_rectangle(cx - 11, cy - 11, cx + 11, cy + 11, fill=GOLD if mk == "on" else "", outline=GOLD if mk == "on" else DIM, width=2)
                if mk == "on":
                    draw_icon(cv, "check", cx, cy, 14, BLK)
        cv.configure(scrollregion=(0, 0, w, max(int(cv.winfo_height()), len(self.rows) * rh + 8)))

    def press(self, e):
        self.moved, self.y0 = False, e.y
        self.cv.scan_mark(0, e.y)

    def drag(self, e):
        if abs(e.y - self.y0) > 6:
            self.moved = True
        if self.moved:
            self.cv.scan_dragto(0, e.y, gain=1)

    def release(self, e):
        if self.moved:
            return
        i = int(self.cv.canvasy(e.y) // self.row_h)
        if 0 <= i < len(self.rows):
            self.on_click(self.rows[i])

    def wheel(self, e):
        self.cv.yview_scroll((-1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1) * 3, "units")


class Mixin:
    # ---- the groups shown in the library
    def refresh_playlists(self):
        out = []
        for p in PL.all_playlists():
            out.append({"id": "pl:" + p["id"], "kind": "playlist", "name": p["name"], "sub": "", "pid": p["id"], "paths": [x for x in p["paths"] if os.path.isfile(x)],
                        "photo": p.get("cover") or ""})
        self.pls = out
        return out

    def pl_id(self):
        return self.group[3:] if self.group.startswith("pl:") else ""

    def pl_refresh(self):
        self.rebuild_groups()
        self.apply_filter()

    # ---- create / fill
    def pl_ask_name(self, initial="", ok="Create", title="Name your playlist"):
        return self.ask_name(_t(title), initial or PL.suggest_name(), ok)

    def pl_save_paths(self, paths, default=""):
        """New playlist that starts with these songs (asks for the name). Returns its id or None."""
        paths = list(dict.fromkeys(p for p in paths if p))
        if not paths:
            self.msg(self.T("pl_nothing"))
            return None
        name = self.pl_ask_name(default)
        if not name:
            return None
        pid = PL.create_from(name, paths)
        self.msg(self.T("pl_made_n") % len(paths))
        self.pl_refresh()
        return pid

    def pl_new(self):
        pid = self.pl_save_paths_empty()
        if pid:
            self.open_group("pl:" + pid)

    def pl_save_paths_empty(self):
        name = self.pl_ask_name()
        if name:
            pid = PL.create(name)
            self.pl_refresh()
            return pid
        return None

    def pl_new_with(self, paths):
        return self.pl_save_paths(paths)

    def pl_add_paths(self, pid, paths):
        n = PL.add_group(pid, paths)
        self.msg(self.T("pl_added_n") % n)
        self.pl_refresh()

    def pl_add(self, pid, path):
        self.pl_add_paths(pid, [path])

    def pl_pick_menu(self, paths):
        self.pl_pick_dialog(paths)

    def pl_pick_dialog(self, paths):
        """"Save in": Favorites and every playlist with a tick; New playlist on top; Done applies. One song: a tick also removes it; many songs: ticks only add."""
        paths = list(dict.fromkeys(p for p in paths if p))
        if not paths:
            self.msg(self.T("pl_nothing"))
            return
        single = len(paths) == 1
        pls = PL.all_playlists()
        fav_has = all(p in E.favorites for p in paths)
        has = {pl["id"]: set(paths) <= set(pl["paths"]) for pl in pls}
        want = dict(has)
        st = {"fav": fav_has}
        top, body = self.modal(_t("Save in"), 420)
        self.modal_title(body, _t("Save in"))

        def new_pl():
            top.destroy()
            self.root.after(20, lambda: self.pl_save_paths(paths))
        nb = tk.Frame(body, bg=PNL2, cursor="hand2")
        nb.pack(fill="x", pady=(12, 4))
        nc = tk.Canvas(nb, width=44, height=44, bg=PNL2, highlightthickness=0, cursor="hand2")
        nc.pack(side="left")
        draw_shape(nc, 2, 2, 42, 42, fill=CARD, shape=STYLE["shape"], r=6)
        draw_icon(nc, "plus", 22, 22, 16, GOLD)
        nl = tk.Label(nb, text=_t("New playlist"), bg=PNL2, fg=TXT, font=self.f_ui_b, cursor="hand2")
        nl.pack(side="left", padx=14)
        for w in (nb, nc, nl):
            w.bind("<Button-1>", lambda e: new_pl())

        def fav_cover(cv, x, y, size):
            draw_shape(cv, x, y, x + size, y + size, fill=lerp(BRN, RED, 0.5), shape=STYLE["shape"], r=6)
            draw_icon(cv, "heart_on", x + size / 2.0, y + size / 2.0, size * 0.5, TXT)

        def rows():
            out = [{"key": "fav", "title": self.T("favorites"), "sub": "%d %s" % (len([p for p in E.songs_all if p in E.favorites]), self.T("songs")),
                    "cover": fav_cover, "mark": "on" if st["fav"] else "off"}]
            for pl in pls:
                g = {"kind": "group", "title": pl["name"], "cover": [x for x in pl["paths"]][:8], "paths": pl["paths"], "photo": pl.get("cover") or "", "gkind": "playlist"}
                out.append({"key": pl["id"], "title": pl["name"], "sub": "%d %s" % (len(pl["paths"]), self.T("songs")),
                            "cover": lambda cv, x, y, size, g=g: self.pk_group_cover(cv, x, y, size, g), "mark": "on" if want[pl["id"]] else "off"})
            return out

        def click(r):
            if r["key"] == "fav":
                st["fav"] = not st["fav"]
            else:
                want[r["key"]] = not want[r["key"]]
            lst.set(rows(), keep_scroll=True)
        h = min(60 * (len(pls) + 1), max(120, self.root.winfo_height() - 300))
        lst = PickList(self, body, h, click)
        lst.cv.pack(fill="both", expand=True, pady=(4, 0))
        lst.set(rows())

        def done():
            n = 0
            for pl in pls:
                if want[pl["id"]] and not has[pl["id"]]:
                    n += PL.add(pl["id"], paths)
                elif single and has[pl["id"]] and not want[pl["id"]]:
                    PL.remove(pl["id"], paths[0])
                    n += 1
            if st["fav"] != fav_has:
                for p in paths:
                    if (p in E.favorites) != st["fav"]:
                        E.toggle_favorite(p)
                n += 1
            top.destroy()
            if n:
                self.msg(_t("Saved"))
            self.pl_refresh()
        self.modal_buttons(body, [(_t("Done"), done, True)])
        self.modal_show(top)

    def pk_group_cover(self, cv, x, y, size, g):
        """The cover of a playlist (its own photo, else the covers of its songs, else a tile) on a plain canvas, for the dialogs."""
        photo = g.get("photo") or ""
        if photo and os.path.isfile(photo):
            p = M.get_scaled(photo, 48, True)
            img = self.photo(p) if p else None
            if img is not None:
                cv.create_image(x + size / 2.0, y + size / 2.0, image=img)
                return
        self.draw_cover(cv, int(x), int(y), size, g)

    # ---- the photo and the name of a playlist
    def pl_photo_dir(self):
        for d in (os.path.join(HOME, "storage", "pictures"), os.path.join(HOME, "Pictures"), os.path.join(HOME, "storage", "shared", "Pictures"), HOME):
            if os.path.isdir(d):
                return d
        return HOME

    def pl_choose_image(self, parent=None):
        """The file box for a picture. Returns a path or ''."""
        exts = " ".join("*" + e for e in PL.IMAGE_EXTS)
        try:
            return filedialog.askopenfilename(parent=parent or self.root, title=_t("Choose photo"), initialdir=self.pl_photo_dir(), filetypes=[(_t("Pictures"), exts), ("All", "*")]) or ""
        except Exception as e:
            log("choose image: %r" % (e,))
            return ""

    def pl_pick_photo(self, pid):
        src = self.pl_choose_image()
        if not src:
            return
        if PL.set_cover(pid, src):
            self.msg(_t("Photo changed"))
            self.pl_refresh()
        else:
            self.msg(_t("This picture could not be used"))

    def pl_edit_dialog(self, pid):
        """Edit details: the photo (tap it) and the name."""
        pl = PL.get(pid)
        if not pl:
            return
        st = {"new": "", "clear": False, "tries": 0}
        top, body = self.modal(_t("Edit details"), 400)
        self.modal_title(body, _t("Edit details"))
        S = 176
        cv = tk.Canvas(body, width=S + 12, height=S + 12, bg=PNL2, highlightthickness=0, cursor="hand2")
        cv.pack(pady=(14, 2))
        keep = []

        def paint():
            cv.delete("all")
            del keep[:]
            src = st["new"] or ("" if st["clear"] else (PL.cover_of(pid)))
            shown = False
            if src:
                p = M.get_scaled(src, S, True)
                img = self.photo(p) if p else None
                if img is not None:
                    keep.append(img)
                    cv.create_image(6 + S / 2.0, 6 + S / 2.0, image=img)
                    shown = True
                elif st["tries"] < 24:
                    st["tries"] += 1
                    top.after(250, paint)
            if not shown:
                g = {"kind": "group", "title": pl["name"], "cover": [x for x in pl["paths"]][:8], "paths": pl["paths"], "photo": "", "gkind": "playlist"}
                if st["clear"] or not [x for x in pl["paths"] if M.art_of(x)]:
                    self.draw_square(cv, 6, 6, S, pl["name"], "song")
                else:
                    self.draw_cover(cv, 6, 6, S, g)
            cv.create_oval(S - 30, S - 30, S + 6, S + 6, fill=PNL2, outline=GOLD if STYLE["glow"] else "")
            draw_icon(cv, "pencil", S - 12, S - 12, 18, TXT)

        def choose(_e=None):
            src = self.pl_choose_image(top)
            if src:
                st["new"], st["clear"], st["tries"] = src, False, 0
                paint()
            try:
                top.lift()
                top.grab_set()
            except tk.TclError:
                pass
        cv.bind("<Button-1>", choose)
        paint()
        row = tk.Frame(body, bg=PNL2)
        row.pack(fill="x")
        lab = tk.Label(row, text=_t("Choose photo"), bg=PNL2, fg=BRN2 if not STYLE["glow"] else INFO, font=self.f_ui_b, cursor="hand2")
        lab.pack(side="left", expand=True)
        lab.bind("<Button-1>", choose)
        if PL.cover_of(pid):
            rm = tk.Label(row, text=_t("Remove photo"), bg=PNL2, fg=DIM, font=self.f_ui, cursor="hand2")
            rm.pack(side="left", expand=True)
            rm.bind("<Button-1>", lambda e: (st.update(new="", clear=True, tries=0), paint()))
        e, v = self.modal_entry(body, pl["name"], _t("Name"), big=False)

        def save(_e=None):
            name = v.get().strip()
            if name and name != pl["name"]:
                PL.rename(pid, name)
            if st["new"]:
                PL.set_cover(pid, st["new"])
            elif st["clear"]:
                PL.clear_cover(pid)
            top.destroy()
            self.pl_refresh()
        e.bind("<Return>", save)
        self.modal_buttons(body, [(_t("Cancel"), top.destroy, False), (_t("Save"), save, True)])
        self.modal_show(top, focus=e)

    # ---- "Add songs to this playlist": search, tabs, a + for every song
    def pl_add_songs_dialog(self, pid):
        pl = PL.get(pid)
        if not pl:
            return
        have = set(pl["paths"])
        st = {"tab": "sug", "job": None, "added": 0}
        top, body = self.modal(_t("Add songs"), 520)
        self.modal_title(body, _t("Add songs to this playlist"), pl["name"])
        e, v = self.modal_entry(body, "", _t("Search songs"))
        tabs = tk.Frame(body, bg=PNL2)
        tabs.pack(fill="x", pady=(8, 6))
        btns = {}
        keep = []

        def pool():
            q = v.get().strip()
            if q:
                return [p for p, _s in L.smart_search(q, E.songs_all, self.cfg["stats"], E.favorites, PICK_PAGE)]
            t = st["tab"]
            if t == "sug":
                return self.recommend_for(list(have), PICK_PAGE)
            if t == "liked":
                return [p for p in self.sorted_paths(E.songs_all) if p in E.favorites][:PICK_PAGE]
            if t == "recent":
                stats = self.cfg["stats"]
                return [p for p in sorted((p for p in E.songs_all if stats.get(p, {}).get("ts")), key=lambda p: -stats[p]["ts"])][:PICK_PAGE]
            return self.sorted_paths(E.songs_all)[:PICK_PAGE]

        def cover(p):
            def draw(cv, x, y, size):
                img = self.thumb_image(p, 48, square=True)
                if img is not None:
                    keep.append(img)
                    cv.create_image(x + size / 2.0, y + size / 2.0, image=img)
                else:
                    self.draw_square(cv, int(x), int(y), size, self.song_item(p)["title"], "song")
            return draw

        def rows():
            del keep[:]
            out = []
            for p in pool():
                it = self.song_item(p)
                out.append({"key": p, "title": it["title"], "sub": it["sub"], "cover": cover(p), "mark": "check" if p in have else "plus"})
            return out

        def refresh(keep_scroll=False):
            for k, b in btns.items():
                on = k == st["tab"] and not v.get().strip()
                b.configure(bg=GOLD if on else PNL2, fg=BLK if on else TXT)
            lst.set(rows(), keep_scroll)
            if not lst.rows:
                lst.cv.create_text(20, 30, text=self.T("no_results"), fill=DIM, font=self.f_ui, anchor="w")

        def click(r):
            p = r["key"]
            if p in have:
                PL.remove(pid, p)
                have.discard(p)
            else:
                PL.add(pid, [p])
                have.add(p)
                st["added"] += 1
            r["mark"] = "check" if p in have else "plus"
            lst.draw()
        for k, label in (("sug", _t("Suggested")), ("all", self.T("songs_chip")), ("liked", self.T("favorites")), ("recent", _t("Recent"))):
            b = self.btn(tabs, label, lambda k=k: (st.update(tab=k), v.set(""), refresh()), bg=PNL2, padx=12, pady=4, font=self.f_small)
            b.pack(side="left", padx=(0, 6))
            btns[k] = b
        lst = PickList(self, body, 300, click)
        lst.cv.pack(fill="both", expand=True)

        def typed(_ev=None):
            if st["job"]:
                top.after_cancel(st["job"])
            st["job"] = top.after(180, refresh)
        e.bind("<KeyRelease>", typed)

        def done():
            top.destroy()
            self.pl_refresh()
        self.modal_buttons(body, [(_t("Done"), done, True)])
        refresh()
        self.modal_show(top, height=max(360, self.root.winfo_height() - 40), focus=e)
        top.protocol("WM_DELETE_WINDOW", done)

    def pl_save_page(self):
        """Whatever list is on screen (search results, a folder, favorites, Home ...) becomes a playlist."""
        paths = [it["path"] for it in self.rows.items if it["kind"] == "song"]
        self.pl_save_paths(paths, self.lbl_head.cget("text") if self.lbl_head.cget("text") else "")

    # ---- inside a playlist
    def pl_remove(self, path):
        if self.pl_id():
            PL.remove(self.pl_id(), path)
            self.pl_refresh()

    def pl_move(self, path, delta):
        if self.pl_id():
            PL.move(self.pl_id(), path, delta)
            self.pl_refresh()

    def pl_rename(self):
        g = self.gmap.get(self.group)
        if not g or g["kind"] != "playlist":
            return
        name = self.pl_ask_name(g["name"], "Save", "Rename playlist")
        if name:
            PL.rename(self.pl_id(), name)
            self.pl_refresh()

    def pl_dup(self):
        if self.pl_id():
            pid = PL.duplicate(self.pl_id())
            self.pl_refresh()
            if pid:
                self.open_group("pl:" + pid)

    def pl_delete(self):
        g = self.gmap.get(self.group)
        if g and g["kind"] == "playlist" and messagebox.askyesno("Rofpalys", "%s: %s ?" % (self.T("pl_delete"), g["name"]), parent=self.root):
            PL.delete(self.pl_id())
            self.group = ""
            self.pl_refresh()
            self.save_ui()

    def pl_export(self):
        g = self.gmap.get(self.group)
        if not g or g["kind"] != "playlist":
            return
        path = filedialog.asksaveasfilename(parent=self.root, initialdir=HOME, initialfile=g["name"] + ".m3u", defaultextension=".m3u")
        if path:
            self.msg("%s: %s" % (self.T("pl_export"), os.path.basename(path)) if PL.export_m3u(self.pl_id(), path) else "export failed")

    def pl_import(self):
        path = filedialog.askopenfilename(parent=self.root, initialdir=HOME, filetypes=[("M3U", "*.m3u *.m3u8"), ("All", "*")])
        if path:
            pid, n = PL.import_m3u(path)
            self.msg("%d %s" % (n, self.T("songs")) if pid else "nothing found in that file")
            self.pl_refresh()
            if pid:
                self.open_group("pl:" + pid)

    # ---- select many songs (check boxes) and do something with them
    def pl_select_toggle(self):
        on = not self.rows.select_mode
        self.rows.set_select_mode(on)
        if on:
            self.sel_bar.pack(before=self.rows.frame, fill="x", padx=18, pady=(0, 6))
            self.pl_select_update()
        else:
            self.sel_bar.pack_forget()

    def pl_selected_paths(self):
        """The songs that are ticked (a ticked folder / artist / playlist counts with all its songs)."""
        out = []
        for it in self.rows.items:
            k = RowList.key_of(it)
            if k and k in self.rows.checked:
                out += [it["path"]] if it["kind"] == "song" else list(it.get("paths", []))
        return list(dict.fromkeys(out))

    def pl_select_update(self):
        self.lbl_sel.configure(text=self.T("sel_count") % len(self.pl_selected_paths()))

    def pl_sel_all(self):
        self.rows.check_all()
        self.pl_select_update()

    def pl_sel_to_playlist(self):
        self.pl_pick_menu(self.pl_selected_paths())

    def pl_sel_queue(self):
        paths = self.pl_selected_paths()
        if paths:
            E.queue_add(paths)
        else:
            self.msg(self.T("pl_nothing"))

    def pl_sel_play(self):
        paths = self.pl_selected_paths()
        if paths:
            E.queue_clear()
            E.queue_add(paths[1:])
            self.play(paths[0])
        else:
            self.msg(self.T("pl_nothing"))


# ------------------------------------------------------------------ plug-in parts
def page(app):
    return [{"kind": "action", "title": app.T("new_playlist"), "action": "new_playlist"}] + [app.group_item(g) for g in app.refresh_playlists()]


def provider(app):
    return app.refresh_playlists()


def row_menu(app, m, it):
    p = it["path"]
    sub = tk.Menu(m, tearoff=0, bg=PNL2, fg=TXT, activebackground=BRN, activeforeground=BLK, bd=0, font=app.f_ui)
    have = set(PL.containing(p))
    for pl in PL.all_playlists():
        sub.add_command(label=("✓ " if pl["id"] in have else "   ") + pl["name"], command=lambda pid=pl["id"]: app.pl_add(pid, p))
    sub.add_separator()
    sub.add_command(label=app.T("new_pl_with"), command=lambda: app.pl_save_paths([p]))
    m.add_cascade(label=app.T("add_to_pl"), menu=sub)
    if app.group.startswith("pl:") and not app.query():
        m.add_command(label=app.T("remove_from_pl"), command=lambda: app.pl_remove(p))
        m.add_command(label=app.T("move_up"), command=lambda: app.pl_move(p, -1))
        m.add_command(label=app.T("move_down"), command=lambda: app.pl_move(p, 1))
    m.add_command(label=app.T("sel_mode"), command=app.pl_select_toggle)


def group_menu(app, m, it):
    paths = list(it.get("paths", []))
    m.add_command(label=app.T("add_all_to_pl"), command=lambda: app.pl_pick_menu(paths))
    m.add_command(label=app.T("play_all"), command=lambda: (E.queue_clear(), E.queue_add(paths[1:]), app.play(paths[0])) if paths else None)


def build(app):
    bar = tk.Frame(app.lv, bg=PNL2)
    app.sel_bar = bar
    app.lbl_sel = tk.Label(bar, text="", bg=PNL2, fg=GOLD, font=app.f_ui, padx=10)
    app.lbl_sel.pack(side="left")
    app.sel_btns = []
    for key, cmd in (("sel_done", app.pl_select_toggle), ("play", app.pl_sel_play), ("add_queue", app.pl_sel_queue), ("add_to_pl", app.pl_sel_to_playlist), ("sel_all", app.pl_sel_all)):
        b = app.btn(bar, "", cmd, bg=PNL2, padx=10, pady=4)
        b.pack(side="right", padx=2, pady=3)
        app.sel_btns.append((b, key))
    app.rows.on_select = lambda it: app.pl_select_update()
    relabel(app)


def relabel(app):
    if hasattr(app, "sel_btns"):
        for b, key in app.sel_btns:
            b.configure(text=app.T(key))


def empty(app):
    return app.T("pl_empty") if app.group.startswith("pl:") else ""


def register(app):
    app.pls = []
    app.add_chip(60, "playlists", "playlists", page)
    app.add_action("new_playlist", lambda a: a.pl_new())
    app.add_group_provider(provider)
    app.add_kind_label("playlist", "playlist")
    app.add_row_menu(row_menu)
    app.add_group_menu(group_menu)
    for label_key, cmd, kinds in (("pl_rename", lambda a: a.pl_rename(), ("playlist",)), ("pl_dup", lambda a: a.pl_dup(), ("playlist",)),
                                  ("pl_export", lambda a: a.pl_export(), ("playlist",)), ("pl_delete", lambda a: a.pl_delete(), ("playlist",)),
                                  ("add_to_pl", lambda a: a.pl_pick_menu(a.gmap[a.group]["paths"]), GROUP_KINDS)):
        app.add_head_button(label_key, cmd, kinds)
    app.add_menu("pl_import", lambda a: a.pl_import())
    app.add_menu("sel_mode", lambda a: a.pl_select_toggle())
    app.add_menu("pl_save_page", lambda a: a.pl_save_page())
    app.add_empty_text(empty)
    app.add_relabel(relabel)
    app.add_build(build)


# END-OF-FILE rofpalys_gui_playlists.py

