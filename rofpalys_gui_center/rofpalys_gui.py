#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - the GUI window (classic brown & black theme, Spotify-style layout) + the loader of the GUI feature files
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""This file is only the window: sidebar, now-playing bar, library pages, Now Playing, visualizer, settings.
The look (Classic / Modern / Cyberpunk, see rofpalys_theme.py) decides colours, SHAPES and fonts; switching it builds the window again (rebuild_ui).
Everything else is a FEATURE FILE next to it:  rofpalys_gui_<name>.py  (playlists, queue, stats, effects, sleep, lyrics ...).
To add a feature: copy rofpalys_gui_template.py to rofpalys_gui_<yourname>.py, fill it in, run  python ~/rofpalys.py install.
Nothing in this file has to change. Shared colours, icons and widgets live in rofpalys_gui_base.py."""
import importlib
import os
import re
import sys

from rofpalys_gui_base import *   # noqa: F401,F403  (colours, texts, icons, RowList, the engine modules E, M, L, ...)


class CoreApp:
    def __init__(self, root, paths=()):
        os.makedirs(CFG, exist_ok=True)
        self.root = root
        root.report_callback_exception = lambda et, ev, tb: log("tk callback: %r" % (ev,))   # a bug in one button never kills the window
        self.init_registries()
        self.feature_errors = list(FEATURE_ERRORS)
        for mod in FEATURE_MODS:                           # every rofpalys_gui_<name>.py plugs itself in here
            try:
                mod.register(self)
                self.features_loaded.append(mod.__name__)
            except Exception as e:
                log("feature %s: %r" % (mod.__name__, e))
                self.feature_errors.append((mod.__name__, repr(e)))
        E.load_favorites()
        E.load_settings()
        E.on_library_changed = lambda: None             # the GUI builds its own lists (see _poll)
        self.cfg = self.load_cfg()
        ST.load(self.cfg.get("stats"), self.cfg.get("total_sec", 0))     # listening numbers live in stats.json (the engine keeps them, TUI too)
        self.cfg["stats"] = ST.stats
        for f in self.legacy_folders:
            if f not in E.extra_folders and os.path.isdir(f):
                E.extra_folders.append(f)
        ui = self.cfg["ui"]
        self.chip = ui.get("chip") if ui.get("chip") in self.chip_keys() else "home"
        self.group = ui.get("group") or ""
        self.cats, self.folders, self.artists, self.mixes, self.gmap, self._meta, self._fitc = [], [], [], [], {}, {}, {}
        self._lv = None
        self.tick, self.anim_idx, self.t_anim = 0, 0, time.time()
        self.seen, self._libver, self._mver, self._tver = None, -1, -1, -1
        self.lyr_lines, self.lyr_idx, self.rain, self.stars = (), -2, [], []
        self.lyr_tr, self.lyr_map, self.lyr_tmap = None, [], {}               # the translation rows under the lyric lines; text line of each lyric line
        self.lt_sig, self.lt_rows, self.lt_state, self.lt_next = None, None, "", 0.0
        self.last_poll, self.t_save = time.time(), time.time()
        self.vol_job, self.dragging, self.view, self.vis_job, self.media_job = None, None, "library", None, None
        self._rebuilding = False
        self._narrow, self._now_wide, self._imgs, self._thumb, self._big, self._big_src = None, None, {}, None, None, ""
        self.vstream = M.VideoStream()
        self._vseq, self._vsize, self._art_sig, self._tint = -1, (0, 0), None, BLK
        self.settings_win, self.video_broken, self._wiped, self._svars = None, False, False, []
        self._ph, self._ph_lock, self._qjob, self._geo_job, self._term, self._vol_seen = False, False, None, None, False, -1
        self.build()
        E.refresh_playlist()
        self.rebuild_groups()
        if paths:
            E.add_external(paths)
            self.rebuild_groups()
        self.apply_filter()
        if paths:
            E.play_song(paths[0])
        else:
            try:                                                                     # started by "7y" in the terminal: carry on with the same song at the same second
                import rofpalys_switch as SW
                if SW.resume(E, SW.take("GUI")):
                    self.msg(self.T("sw_back"))
            except Exception as e:
                log("hand-off: %r" % (e,))
        E.scan_library_async()
        CT.start(E, notify=E.notify_controls)             # control socket + notification buttons
        AL.start(E.alarm_fire)
        self.go(ui.get("view") if ui.get("view") in ("now", "visual") else "library")
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.after(200, self.poll)

    def load_cfg(self):
        cfg = json.loads(json.dumps(DEFAULT_CFG))
        self.legacy_folders = []
        try:
            with open(GUI_CFG, encoding="utf-8") as f:
                d = json.load(f)
            cfg.update({k: v for k, v in d.items() if k in cfg})
            self.legacy_folders = [x for x in d.get("folders", []) if isinstance(x, str)]
        except (OSError, ValueError):
            pass
        if not isinstance(cfg.get("ui"), dict):
            cfg["ui"] = dict(DEFAULT_CFG["ui"])
        return cfg

    def save_cfg(self):
        try:
            data = {k: v for k, v in self.cfg.items() if k not in ("stats", "total_sec")}      # the numbers live in stats.json now
            with open(GUI_CFG + ".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(GUI_CFG + ".tmp", GUI_CFG)
        except OSError as e:
            log("save_cfg: %s" % e)

    def T(self, k):
        return I18N.pick(TXT_, E.current_lang, k)

    def msg(self, text):
        E.info(text)

    def position(self):
        if E.is_playing:
            return E.current_time_seconds
        return float(self.cfg["last"].get("pos", 0)) if E.playing_song_name is None else 0.0

    def sel_path(self):
        it = self.rows.selected_item()
        return it["path"] if it and it["kind"] == "song" else ""

    def play(self, path, start=0.0):
        if path:
            E.play_song(path, start if start > 1 else 0.0)

    def toggle(self):
        if E.is_paused:
            E.resume()
        elif E.is_playing:
            if not E.pause():
                E.stop()
        else:
            path = E.playing_song_name or self.sel_path() or self.cfg["last"].get("song") or (E.songs[0] if E.songs else "")
            last = self.cfg["last"]
            self.play(path, last.get("pos", 0) if path == last.get("song") and not E.playing_song_name else 0)

    def seek(self, sec):
        E.seek(sec)

    def step(self, d):
        E.step(d)

    def cycle_mode(self):
        E.play_mode = (E.play_mode + 1) % 5
        E.save_settings()

    def toggle_fav(self, path=None):
        path = path if isinstance(path, str) else (E.playing_song_name or self.sel_path())
        if not path:
            return
        E.toggle_favorite(path)
        if self.chip == "favorites" and not self.group and not self.query():
            self.apply_filter()
        else:
            self.rows.redraw()

    def set_engine(self, i):
        E.ACTIVE_ENGINE_IDX = i
        if E.is_playing and E.playing_song_name:
            self.play(E.playing_song_name, self.position())

    def set_volume(self, v, apply=True):
        v = int(float(v))
        E.set_volume(v, apply=False)
        if not apply:
            return
        if self.vol_job:
            self.root.after_cancel(self.vol_job)
        self.vol_job = self.root.after(150, lambda: (E.set_volume(v), E.save_settings()))

    def rescan(self):
        E.scan_library_async()

    def add_folder(self):
        d = filedialog.askdirectory(parent=self.root, initialdir=HOME, title=self.T("add"))
        if d and d not in E.extra_folders:
            E.extra_folders.append(d)
            E.save_settings()
            self.rescan()

    def apply_filter(self):
        """Rebuild the visible page. E.songs becomes the play queue (so next/previous follow what you see)."""
        self._qjob = None
        hs = getattr(self, "home_sync", None)
        on = bool(hs and hs())                                       # the Home page of cards is shown instead of the list
        items = [] if on else self.page_items()
        seen, queue = set(), []
        for it in items:
            if it["kind"] == "song" and it["path"] not in seen:
                seen.add(it["path"])
                queue.append(it["path"])
        E.songs = queue if queue else list(E.songs_all)
        self.rows.set_items(items)
        self.update_head()
        self.style_chips()

    def refresh_line(self, path=None):
        self.rows.redraw()

    def cycle_sort(self):
        self.cfg["sort"] = SORTS[(SORTS.index(self.cfg["sort"]) + 1) % len(SORTS)]
        self.b_sort.configure(text={"name": "A-Z", "recent": "NEW", "plays": "PLAYS"}[self.cfg["sort"]])
        self.apply_filter()
        self.save_cfg()

    def download(self):
        url = simpledialog.askstring("yt-dlp", self.T("dlq"), parent=self.root)
        if url:
            threading.Thread(target=E.download_and_play_yt, args=(url.strip(),), daemon=True).start()

    def popup_text(self, title, text):
        top = tk.Toplevel(self.root)
        top.title(title)
        top.configure(bg=BLK)
        t = tk.Text(top, bg=PNL, fg=TXT, font=self.f_mono, bd=0, wrap="word", width=60, height=18, highlightthickness=0)
        t.insert("1.0", text)
        t.configure(state="disabled")
        t.pack(fill="both", expand=True, padx=8, pady=8)

    def backup(self):
        music = os.path.join(HOME, "Music")
        path = filedialog.asksaveasfilename(parent=self.root, initialdir=music if os.path.isdir(music) else HOME, initialfile="rofpalys-backup.json",
                                            defaultextension=".json")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": 2, "favorites": sorted(E.favorites), "gui": self.cfg, "folders": E.extra_folders,
                           "language": E.current_lang, "anim_enabled": E.anim_enabled}, f, indent=1)
            self.msg("Backup saved: " + os.path.basename(path))
        except OSError as e:
            self.msg("Backup failed: %s" % e)

    def restore(self):
        path = filedialog.askopenfilename(parent=self.root, initialdir=HOME, filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            E.favorites = set(d.get("favorites", []))
            E.save_favorites()
            self.cfg.update({k: v for k, v in d.get("gui", {}).items() if k in DEFAULT_CFG and k != "geometry"})
            for fld in d.get("folders", []) + d.get("gui", {}).get("folders", []):
                if isinstance(fld, str) and os.path.isdir(fld) and fld not in E.extra_folders:
                    E.extra_folders.append(fld)
            E.current_lang = d.get("language", E.current_lang)
            E.anim_enabled = bool(d.get("anim_enabled", E.anim_enabled))
            E.save_settings()
            self.save_cfg()
            self.rescan()
            self.relabel()
            self.msg("Backup restored")
        except Exception as e:
            self.msg("Restore failed: %s" % e)

    def deep_reset(self):
        if not messagebox.askyesno("Rofpalys", self.T("sure_all"), parent=self.root):
            return
        E.reset_everything()
        self._wiped = True                                  # the window closes WITHOUT saving, or it would write the old state back
        try:
            messagebox.showinfo("Rofpalys", self.T("reset_done"), parent=self.root)
        except Exception:
            pass
        self.quit()

    def cycle_lang(self):
        self.set_lang(I18N.cycle())

    def set_lang(self, code):
        """The language of EVERYTHING: the main window is built again (every page, every label), and the windows that were open next to it (settings, look, lyrics,
        remote) are opened again in the new language. The page, the search and the song that plays stay as they are."""
        code = I18N.norm(code)
        if not code or code == E.current_lang:
            return
        E.current_lang = code
        E.save_settings()
        keep = []                                                                   # (opener, closer) of the windows that are open now
        for attr, opener, closer in (("settings_win", "open_settings", "close_settings"), ("th_win", "th_open", "th_close"), ("lyr_win", "open_lyrics_dialog", "close_lyrics_dialog"),
                                     ("rm_win", "rm_dialog", "rm_close_dialog")):
            if getattr(self, attr, None) is not None and hasattr(self, opener):
                keep.append((opener, closer))
        for _opener, closer in keep:
            try:
                getattr(self, closer)()
            except Exception as e:
                log("close %s: %r" % (closer, e))
        for w in list(self.root.winfo_children()):                                  # shortcuts and other small windows: the old language would stay in them
            if w.winfo_class() == "Toplevel":
                try:
                    w.destroy()
                except Exception:
                    pass
        self.rebuild_ui()
        for opener, _closer in keep:
            try:
                getattr(self, opener)()
            except Exception as e:
                log("reopen %s: %r" % (opener, e))
        self.msg("%s: %s" % (self.T("lang"), I18N.NAMES.get(code, code)))

    # ------------------------------------------------------------------ GUI <-> CLI
    def mode_switch(self, parent, bg):
        """The two small buttons [GUI | CLI] under the name ROFPALYS: GUI is the screen you are in, CLI opens the terminal player and closes this window."""
        row = tk.Frame(parent, bg=bg)
        row.btns = []
        for label in ("GUI", "CLI"):
            on = label == "GUI"
            if STYLE["chip"] == "flat":
                b = tk.Label(row, text=label, bg=GOLD if on else PNL2, fg=BLK if on else TXT, font=self.f_small, padx=14, pady=3, cursor="hand2")
            else:
                b = ShapeLabel(row, text=label, bg=GOLD if on else PNL2, fg=BLK if on else TXT, font=self.f_small, padx=int(14 * STYLE["pad"]), pady=int(round(3 * STYLE["pad"])),
                               cursor="hand2", shape=STYLE["chip"])
            b.bind("<Button-1>", lambda e, m=label: self.switch_mode(m))
            row.btns.append(b)
        return row

    def switch_mode(self, mode):
        """GUI -> CLI: the song and the second are written to a small file, a terminal opens with the terminal player, this window closes (the sound goes with it, the terminal carries on)."""
        if mode != "CLI":
            return
        try:
            import rofpalys_switch as SW
        except ImportError:
            self.msg("rofpalys_switch.py missing")
            return
        snap = SW.snapshot(E)
        paused_here = bool(snap["playing"])
        if paused_here:
            E.toggle_play()                                                         # silent while the other screen starts: never two sounds at once
        ok, text = SW.start("CLI", snap)
        if not ok:
            if paused_here:
                E.toggle_play()
            self.msg("%s: %s" % (self.T("sw_fail"), text))
            return
        self.msg(self.T("sw_cli"))
        self.root.after(600, self.quit)

    def quit(self):
        AL.stop()
        CT.stop_server()
        if self._wiped:
            self.vstream.stop()
            E.shutdown(save=False)
            self.root.destroy()
            return
        try:
            self.cfg["geometry"] = self.root.geometry()
        except Exception:
            pass
        self.save_ui()
        self.vstream.stop()
        E.save_settings()
        E.shutdown()
        self.root.destroy()

    def btn(self, parent, text, cmd, **kw):
        if STYLE["btn"] == "flat":                                       # Classic: the plain Label button it always was
            b = tk.Label(parent, text=text, bg=kw.pop("bg", PNL2), fg=kw.pop("fg", TXT), font=kw.pop("font", self.f_ui), padx=kw.pop("padx", 12),
                         pady=kw.pop("pady", 5), cursor="hand2", **kw)
        else:                                                            # Modern / Cyberpunk: a drawn button (rounded / cut corners, neon outline, capitals)
            pad = STYLE["pad"]
            b = ShapeLabel(parent, text=text, bg=kw.pop("bg", PNL2), fg=kw.pop("fg", TXT), font=kw.pop("font", self.f_ui), padx=int(kw.pop("padx", 12) * pad),
                           pady=int(round(kw.pop("pady", 5) * pad)), cursor="hand2", shape=STYLE["btn"], **kw)
        b.bind("<Button-1>", lambda e: cmd())
        base = b.cget("bg")
        b.bind("<Enter>", lambda e: b.configure(bg=HOVER if base != BRN else BRN2))
        b.bind("<Leave>", lambda e: b.configure(bg=base))
        return b

    def nav_item(self, parent, key, label_key):
        """A sidebar button: icon + name in every look (Classic: a flat bar, Modern: a rounded plate, Cyberpunk: a cut plate with a neon bar). Closed sidebar: the icon alone, in the middle."""
        icon = next((ic for _o, k, _l, ic in self.nav_list() if k == key), None)
        flat = STYLE["nav"] == "bar"
        b = ShapeLabel(parent, text="", bg=SIDE, fg=DIM, font=self.f_nav, anchor="w", padx=16 if flat else 14, pady=int(round(9 * STYLE["pad"])), cursor="hand2",
                       shape="flat" if flat else STYLE["shape"], icon=icon, outline="")
        b.bind("<Button-1>", lambda e: self.nav_click(key))
        b.bind("<Enter>", lambda e: (b.configure(fg=TXT), None if self.side_open else self.tip_show(b, self.T(label_key))))
        b.bind("<Leave>", lambda e: (self.style_nav(), self.tip_hide()))
        b.label_key = label_key
        return b

    def nav_click(self, key):
        """A click on the sidebar. Home always opens the Home tab (not the tab you were on last)."""
        if key == "library":
            self.chip, self.group = "home", ""
            if self._ph is False and self.v_search.get():
                self._set_search("")
                self.ph_show()
        self.go(key)

    # ---- sidebar: open (icons + names) / closed (icons only); the features work the same
    def side_w(self):
        return 224 if self.side_open else 68

    def toggle_side(self, _e=None):
        self.side_open = not self.side_open
        self.side_apply()
        self.save_ui()

    def side_apply(self):
        """Pack the sidebar for its state. Open: [logo][menu button], [GUI|CLI], then icon + name. Closed: the menu button, the first letter, a small CLI button, icons."""
        op = self.side_open
        self.side.configure(width=self.side_w())
        for w in (self.b_side.cv, self.logo.cv):
            w.pack_forget()
        if op:
            self.b_side.cv.pack(side="right", padx=(0, 4))
            self.logo.set_mark(False)
            self.logo.pack(side="left", fill="x", expand=True)
        else:
            self.b_side.cv.pack(side="top", pady=(0, 2))
            self.logo.set_mark(True)
            self.logo.pack(side="top", fill="x")
        gui_b, cli_b = self.mode_row.btns
        gui_b.pack_forget()
        cli_b.pack_forget()
        if op:
            gui_b.pack(side="left", expand=True, fill="x", padx=(0, 3))
            cli_b.pack(side="left", expand=True, fill="x", padx=(3, 0))
            self.mode_row.pack_configure(padx=18)
        else:
            cli_b.pack(side="top", fill="x")
            self.mode_row.pack_configure(padx=10)
        self.relabel_nav()
        self.b_side.set(kind="menu")

    def relabel_nav(self):
        for k, b in self.navs.items():
            b.configure(text=self.T(b.label_key) if self.side_open else "", anchor="w" if self.side_open else "center")
            b.pack_configure(padx=(0 if STYLE["nav"] == "bar" else 8) if self.side_open else (0 if STYLE["nav"] == "bar" else 6))

    # a small hint under the pointer (the closed sidebar has no names)
    def tip_show(self, w, text):
        self.tip_hide()
        try:
            self._tip_job = self.root.after(380, lambda: self._tip_make(w, text))
        except Exception:
            pass

    def _tip_make(self, w, text):
        try:
            t = tk.Toplevel(self.root)
            t.wm_overrideredirect(True)
            t.configure(bg=GRID)
            tk.Label(t, text=text, bg=PNL2, fg=TXT, font=self.f_small, padx=9, pady=4).pack(padx=1, pady=1)
            t.wm_geometry("+%d+%d" % (w.winfo_rootx() + w.winfo_width() + 6, w.winfo_rooty() + max(0, (w.winfo_height() - 26) // 2)))
            self._tip_win = t
        except Exception:
            self._tip_win = None

    def tip_hide(self):
        j = getattr(self, "_tip_job", None)
        if j:
            try:
                self.root.after_cancel(j)
            except Exception:
                pass
            self._tip_job = None
        t = getattr(self, "_tip_win", None)
        if t is not None:
            try:
                t.destroy()
            except Exception:
                pass
            self._tip_win = None

    def style_nav(self):
        for k, b in self.navs.items():
            if k == "favorites":
                on = self.view == "library" and self.chip == "favorites" and not self.group
            elif k == "library":
                on = self.view == "library" and not (self.chip == "favorites" and not self.group)
            else:
                on = k == self.view
            if STYLE["nav"] == "bar":
                b.configure(fg=GOLD if on else DIM, bg=PNL if on else SIDE)
            else:                                                        # the page in use: a filled plate (Modern) / plate + neon bar at the left edge (Cyberpunk)
                b.configure(fg=GOLD if on else DIM, bg=HOVER if on else SIDE, accent=(BRN2 if STYLE["nav"] == "edge" else "") if on else "",
                            outline=(BRN2 if (on and STYLE["glow"]) else ""))
            tb = self.tnavs.get(k)
            if tb is not None:
                tb.set(color=GOLD if on else DIM)

    def build(self):
        root = self.root
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        fs = max(10, min(14, round(min(sw, 1400) / 110)))
        fn = look_fonts(root, fs)                                                  # the fonts of the look in use (Classic = DejaVu as always)
        self.f_ui, self.f_mono, self.f_nav = fn["ui"], fn["mono"], fn["nav"]
        self.f_big, self.f_title = fn["big"], fn["title"]
        self.f_small, self.f_head, self.f_ui_b = fn["small"], fn["head"], fn["ui_b"]
        self.f_disp = fn["display"]
        self.mf = {"ui": tkfont.Font(font=self.f_ui), "ui_b": tkfont.Font(font=self.f_ui_b), "small": tkfont.Font(font=self.f_small),
                   "title": tkfont.Font(font=self.f_title), "head": tkfont.Font(font=(self.f_disp, self.f_big[1], "bold"))}
        root.title("Rofpalys")
        root.configure(bg=BLK)
        if not self._rebuilding:                                                   # a rebuild (look switched) keeps the window where and how big it is
            root.minsize(min(360, sw - 20), min(460, sh - 60))
            m = re.match(r"^(\d+)x(\d+)", self.cfg.get("geometry") or "")
            w, h = (min(int(m.group(1)), sw - 10), min(int(m.group(2)), sh - 50)) if m else (min(sw - 10, 1100), min(sh - 50, 720))
            root.geometry("%dx%d+%d+%d" % (w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 3)))

        # ---- bottom first (so it always keeps its space): status line + now-playing bar
        self.status = tk.Label(root, text="", bg=SIDE, fg=DIM, font=self.f_small, anchor="w", padx=10)
        self.status.pack(side="bottom", fill="x")
        bar = tk.Frame(root, bg=SIDE, height=96)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        if STYLE["sep"]:                                                            # a thin line above the player bar (Modern: grey, Cyberpunk: neon)
            tk.Frame(root, bg=BRN2 if STYLE["glow"] else GRID, height=1).pack(side="bottom", fill="x")
        left = tk.Frame(bar, bg=SIDE, width=300)
        left.pack(side="left", fill="y", padx=(12, 0))
        left.pack_propagate(False)
        self.thumb = tk.Canvas(left, width=64, height=64, bg=SIDE, highlightthickness=0, cursor="hand2")
        self.thumb.pack(side="left", pady=16)
        self.thumb.bind("<Button-1>", lambda e: self.go("now"))
        txt = tk.Frame(left, bg=SIDE)
        txt.pack(side="left", fill="both", expand=True, padx=12)
        self.lbl_title = tk.Label(txt, text="", bg=SIDE, fg=TXT, font=self.f_title, anchor="w")
        self.lbl_title.pack(fill="x", pady=(26, 0))
        self.lbl_sub = tk.Label(txt, text="", bg=SIDE, fg=DIM, font=self.f_small, anchor="w")
        self.lbl_sub.pack(fill="x")
        right = tk.Frame(bar, bg=SIDE, width=230)
        right.pack(side="right", fill="y", padx=(0, 12))
        right.pack_propagate(False)
        self.b_fav = IconBtn(right, "heart", self.toggle_fav, size=20, color=DIM)
        self.b_fav.pack(side="left", pady=24)
        IconBtn(right, "volume", lambda: self.go("now"), size=20, color=DIM).pack(side="left", pady=24)
        self.volcv = tk.Canvas(right, width=100, height=20, bg=SIDE, highlightthickness=0, cursor="hand2")
        self.volcv.pack(side="left", pady=38)
        self.volcv.bind("<Button-1>", self.vol_event)
        self.volcv.bind("<B1-Motion>", self.vol_event)
        mid = tk.Frame(bar, bg=SIDE)
        mid.pack(side="left", fill="both", expand=True)
        ctl = tk.Frame(mid, bg=SIDE)
        ctl.pack(pady=(8, 0))
        self.b_mode = IconBtn(ctl, "arrow", self.cycle_mode, size=18, color=DIM)
        self.b_prev = IconBtn(ctl, "prev", lambda: self.step(-1), size=18, color=TXT)
        self.play_cv = tk.Canvas(ctl, width=44, height=44, bg=SIDE, highlightthickness=0, cursor="hand2")
        self.play_cv.bind("<Button-1>", lambda e: self.toggle())
        self.b_next = IconBtn(ctl, "next", lambda: self.step(1), size=18, color=TXT)
        self.b_now = IconBtn(ctl, "expand", lambda: self.go("now"), size=18, color=DIM)
        self.b_mode.pack(side="left")
        self.b_prev.pack(side="left")
        self.play_cv.pack(side="left", padx=6)
        self.b_next.pack(side="left")
        self.b_now.pack(side="left")
        prow = tk.Frame(mid, bg=SIDE)
        prow.pack(fill="x", padx=14)
        self.lbl_pos = tk.Label(prow, text="0:00", bg=SIDE, fg=DIM, font=self.f_small, width=6)
        self.lbl_pos.pack(side="left")
        self.lbl_dur = tk.Label(prow, text="0:00", bg=SIDE, fg=DIM, font=self.f_small, width=6)
        self.lbl_dur.pack(side="right")                         # packed before the bar: the time is never squeezed out
        self.bar = tk.Canvas(prow, height=16, width=10, bg=SIDE, highlightthickness=0, cursor="hand2")
        self.bar.pack(side="left", fill="x", expand=True)
        self.bar.bind("<Button-1>", self.bar_press)
        self.bar.bind("<B1-Motion>", self.bar_press)
        self.bar.bind("<ButtonRelease-1>", self.bar_release)

        # ---- sidebar (wide windows) / top navigation (narrow windows)
        self.side_open = (self.cfg.get("ui") or {}).get("side", "open") != "closed"
        self.side = tk.Frame(root, bg=SIDE, width=self.side_w())
        self.side.pack_propagate(False)
        if STYLE["sep"]:                                                            # a thin line between the sidebar and the pages
            tk.Frame(self.side, bg=BRN2 if STYLE["glow"] else GRID, width=1).pack(side="right", fill="y")
        shead = tk.Frame(self.side, bg=SIDE)
        shead.pack(fill="x", padx=6, pady=(12, 4))
        self.b_side = IconBtn(shead, "menu", self.toggle_side, size=18, color=DIM, bg=SIDE, pad=7)
        self.logo = Logo(shead, 56, SIDE)
        self.mode_row = self.mode_switch(self.side, SIDE)                                    # [ GUI | CLI ]
        self.mode_row.pack(fill="x", padx=18, pady=(0, 10))
        self.navs, self.tnavs = {}, {}
        for _order, key, label_key, _icon in self.nav_list():
            b = self.nav_item(self.side, key, label_key)
            b.pack(fill="x", pady=(0 if STYLE["nav"] == "bar" else 1, 0))
            self.navs[key] = b
        self.lbl_side = tk.Label(self.side, text="")                                        # (the engine / song count line is gone; the label stays so old code keeps working)
        self.side_apply()
        self.topnav = tk.Frame(root, bg=SIDE)
        self.logo2 = Logo(self.topnav, 44, SIDE, width=150)
        self.logo2.pack(side="left", padx=(6, 10))
        cb = tk.Label(self.topnav, text="CLI", bg=PNL2, fg=TXT, font=self.f_small, padx=9, pady=2, cursor="hand2")                # narrow window: just the CLI button
        cb.bind("<Button-1>", lambda e: self.switch_mode("CLI"))
        cb.pack(side="left", padx=(0, 8))
        for _order, key, _label_key, kind in self.nav_list():
            ib = IconBtn(self.topnav, kind, lambda k=key: self.nav_click(k), size=20, color=DIM, pad=10)
            ib.pack(side="left", expand=True)
            self.tnavs[key] = ib
        self.main = tk.Frame(root, bg=PNL)
        self.side.pack(side="left", fill="y")
        self.main.pack(side="left", fill="both", expand=True)

        # ---- library view: search, chips, page header, list
        lv = tk.Frame(self.main, bg=PNL)
        self.lv = lv
        top = tk.Frame(lv, bg=PNL)
        top.pack(fill="x", padx=18, pady=(14, 8))
        self.b_sort = self.btn(top, "A-Z", self.cycle_sort, fg=DIM)
        self.b_sort.pack(side="right", padx=6)
        self.v_search = tk.StringVar()
        if STYLE["shape"] == "flat":
            self.entry = tk.Entry(top, textvariable=self.v_search, bg=PNL2, fg=DIM, insertbackground=GOLD, bd=0, highlightthickness=1,
                                  highlightbackground=PNL2, highlightcolor=BRN2, font=self.f_ui, relief="flat")
            self.entry.pack(side="left", fill="x", expand=True, ipady=8)
        else:                                                                       # the field sits in a rounded / cut box that lights up when you type
            box = Box(top, fill=PNL2, shape=STYLE["btn"] if STYLE["btn"] != "pill" else "pill", padx=12, pady=3, left=22)
            box.icon = DIM
            box.pack(side="left", fill="x", expand=True)
            self.entry = tk.Entry(box.inner, textvariable=self.v_search, bg=PNL2, fg=DIM, insertbackground=GOLD, bd=0, highlightthickness=0, font=self.f_ui, relief="flat")
            self.entry.pack(side="left", fill="x", expand=True, ipady=7)
            box.focus_ring(self.entry, BRN2, "")
        self.entry.bind("<FocusIn>", self.ph_in)
        self.entry.bind("<FocusOut>", self.ph_out)
        chips = tk.Frame(lv, bg=PNL)
        chips.pack(fill="x", padx=18, pady=(0, 6))
        self.chip_row = chips
        chips.bind("<Configure>", lambda e: self.fit_chips())
        self.chip_btns = {}
        for key in self.chip_keys():
            if STYLE["chip"] == "flat":
                b = tk.Label(chips, text="", bg=PNL2, fg=TXT, font=self.f_ui, padx=14, pady=5, cursor="hand2")
            else:
                b = ShapeLabel(chips, text="", bg=PNL2, fg=TXT, font=self.f_ui, padx=int(14 * STYLE["pad"]), pady=int(round(5 * STYLE["pad"])), cursor="hand2", shape=STYLE["chip"],
                               icon=CHIP_ICONS.get(key) if STYLE["icons"] else None)
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, k=key: self.set_chip(k))
            self.chip_btns[key] = b
        head = tk.Frame(lv, bg=PNL)
        self.head_frame = head                                   # (the Home page of cards takes the place of this header + the list, see rofpalys_gui_home.py)
        head.pack(fill="x", padx=18, pady=(4, 4))
        self.head_back = IconBtn(head, "back", self.close_group, size=18, color=TXT, bg=PNL, pad=6)
        self.head_cover = tk.Canvas(head, width=104, height=104, bg=PNL, highlightthickness=0)
        self.htxt = tk.Frame(head, bg=PNL)
        self.lbl_head = tk.Label(self.htxt, text="", bg=PNL, fg=TXT, font=self.f_big, anchor="w")
        self.lbl_head.pack(fill="x")
        self.lbl_hsub = tk.Label(self.htxt, text="", bg=PNL, fg=DIM, font=self.f_small, anchor="w")
        self.lbl_hsub.pack(fill="x")
        self.head_btns = tk.Frame(head, bg=PNL)
        self.b_play_all = self.btn(self.head_btns, "", self.play_group, bg=GOLD, fg=BLK, padx=18, pady=7)
        self.b_shuffle = self.btn(self.head_btns, "", lambda: self.play_group(True), padx=18, pady=7)
        self.b_play_all.pack(side="left")
        self.b_shuffle.pack(side="left", padx=(8, 0))
        self.head_buttons = []                                # buttons that features add to the header of a group page
        for label_key, fn, kinds in self.head_button_defs:
            self.head_buttons.append((self.btn(self.head_btns, "", lambda f=fn: f(self)), label_key, kinds))
        self.rows = RowList(self, lv)
        self.rows.frame.pack(fill="both", expand=True, padx=(8, 4), pady=(0, 6))
        self.rows.on_activate = self.on_row_activate
        self.rows.on_heart = lambda it: self.toggle_fav(it["path"])
        self.rows.on_menu = self.row_menu
        self.v_search.trace_add("write", lambda *a: self.on_query())

        # ---- now playing view: cover art / video (+ captions) and the lyrics panel
        nv = tk.Frame(self.main, bg=PNL)
        self.build_now_bar(nv)
        self.now_media = tk.Frame(nv, bg=PNL)
        self.canvas = tk.Canvas(self.now_media, bg=PNL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", lambda e: self.toggle())
        self.now_lyr = tk.Frame(nv, bg=PNL)
        self.lyr = tk.Text(self.now_lyr, bg=PNL, fg=LYR, font=self.f_big, bd=0, wrap="word", highlightthickness=0, cursor="arrow", padx=18, pady=18,
                           width=26, height=10, spacing1=4, spacing3=8)
        self.lyr.tag_configure("c", justify="center")
        self.lyr.tag_configure("past", foreground=DIM)
        self.lyr.tag_configure("next", foreground=TXT)
        self.lyr.tag_configure("cur", foreground=GOLD, font=(self.f_big[0], self.f_big[1] + 3, "bold"))
        self.lyr.tag_configure("tr", foreground=lerp(DIM, TXT, 0.55), font=(self.f_big[0], max(8, self.f_big[1] - 3)))     # the translation rows under the lyric lines
        self.lyr.tag_configure("trpast", foreground=DIM)
        self.lyr.tag_configure("trcur", foreground=lerp(GOLD, TXT, 0.25))
        self.lyr.pack(fill="both", expand=True)
        self.lyr.bind("<Button-1>", self.lyric_click)
        nv.bind("<Configure>", lambda e: self.layout_now())
        self.nv = nv

        # ---- visualizer view
        vv = tk.Frame(self.main, bg=BLK)
        self.vis = tk.Canvas(vv, bg=BLK, highlightthickness=0)
        self.vis.pack(fill="both", expand=True)
        self.vis.bind("<Button-1>", lambda e: self.next_anim())
        self.frames = {"library": lv, "now": nv, "visual": vv}

        for key, fn in (("<space>", self.toggle), ("n", lambda: self.step(1)), ("p", lambda: self.step(-1)), ("m", self.cycle_mode), ("l", self.toggle_fav),
                        ("z", lambda: self.go("now" if self.view != "now" else "library")), ("c", lambda: self.go("visual" if self.view != "visual" else "library")),
                        ("<Right>", lambda: self.seek(self.position() + 10)), ("<Left>", lambda: self.seek(self.position() - 10)), ("a", self.next_anim), ("<question>", self.open_shortcuts), ("<F1>", self.open_shortcuts)):
            root.bind(key, lambda e, fn=fn: None if self.typing() else fn())
        root.bind("<Control-f>", lambda e: (self.go("library"), self.entry.focus_set()))
        root.bind("<Escape>", lambda e: root.focus_set())
        root.bind("<Configure>", self.on_resize)
        for key, builder in self.view_builders.items():       # pages that features bring (Queue, Statistics ...)
            try:
                self.frames[key] = builder(self)
            except Exception as e:
                log("view %s: %r" % (key, e))
        for fn in self.build_hooks:
            try:
                fn(self)
            except Exception as e:
                log("build hook: %r" % (e,))
        self.relabel()
        self.ph_show()
        self.draw_vol()
        self.on_resize()

    def typing(self):
        try:
            return isinstance(self.root.focus_get(), tk.Entry)
        except KeyError:
            return False

    def relabel(self):
        T = self.T
        self.relabel_nav()
        labels = dict(self.chip_labels())
        for k, b in self.chip_btns.items():
            b.configure(text=T(labels.get(k, k)))
        self.fit_chips()
        self.b_play_all.configure(text="▶  " + T("play"))
        self.b_shuffle.configure(text=T("shuffle"))
        for b, label_key, _kinds in self.head_buttons:
            b.configure(text=T(label_key))
        self.b_sort.configure(text={"name": "A-Z", "recent": "NEW", "plays": "PLAYS"}[self.cfg["sort"]])
        if self._ph:
            self._set_search(T("search_ph"))
        self.update_modes()
        self.update_head()
        self.style_toolbar()
        for fn in self.relabel_hooks:
            try:
                fn(self)
            except Exception as e:
                log("relabel hook: %r" % (e,))

    def on_resize(self, e=None):
        if e is not None and (e.widget is not self.root or self._rebuilding):
            return
        if self._geo_job:
            self.root.after_cancel(self._geo_job)
        self._geo_job = self.root.after(900, self.save_geo)
        w = self.root.winfo_width()
        if w < 50 or (w < 760) == self._narrow:
            return
        self._narrow = w < 760
        if self._narrow:
            self.side.pack_forget()
            self.topnav.pack(side="top", fill="x", before=self.main)
        else:
            self.topnav.pack_forget()
            self.side.pack(side="left", fill="y", before=self.main)
        self.style_nav()

    def go(self, view):
        if view == "favorites":
            self.chip, self.group, view = "favorites", "", "library"
        self.view = view
        for f in self.frames.values():
            f.pack_forget()
        self.frames[view].pack(fill="both", expand=True)
        for jobname in ("vis_job", "media_job"):
            j = getattr(self, jobname)
            if j:
                self.root.after_cancel(j)
                setattr(self, jobname, None)
        if view == "visual":
            self.draw_vis()
        elif view == "now":
            self._now_wide = None
            self._art_sig = None
            self.layout_now()
            self.media_loop()
        elif view in self.view_show:                          # a page from a feature file
            self.vstream.stop()
            self.view_show[view](self)
        else:
            self.vstream.stop()
            self.apply_filter()
        self.style_nav()
        self.save_ui()

    def update_modes(self):
        kind = ["arrow", "repeat1", "arrow2", "repeat", "shuffle"][E.play_mode]
        self.b_mode.set(kind=kind, color=GOLD if E.play_mode else DIM)

    def rebuild_ui(self):
        """The look (colours, shapes, fonts) was switched: build the whole window again in the new look and come back to the same page, with the same search.
        Nothing of the old look is left over. The window keeps its place and size; windows that are open next to it (settings, lyrics ...) stay open."""
        root = self.root
        view, q = self.view, self.query()
        for jobname in ("vis_job", "media_job", "_qjob", "_geo_job"):
            j = getattr(self, jobname, None)
            if j:
                try:
                    root.after_cancel(j)
                except Exception:
                    pass
                setattr(self, jobname, None)
        try:
            self.vstream.stop()
        except Exception:
            pass
        try:
            self.cfg["geometry"] = root.geometry()
        except Exception:
            pass
        for w in list(root.winfo_children()):
            if w.winfo_class() != "Toplevel":
                try:
                    w.destroy()
                except Exception:
                    pass
        self._rebuilding = True
        self._narrow = self._now_wide = self._art_sig = self._thumb = self._big = None
        self._big_src = ""
        self._vsize, self._fitc, self._vol_seen, self._mver = (0, 0), {}, -1, -1
        self.lyr_lines, self.lyr_idx, self.rain, self.stars = (), -2, [], []
        self.lyr_tr, self.lyr_map, self.lyr_tmap = None, [], {}
        self.lt_sig = None
        self._ph, self._ph_lock, self._tint = False, False, NOWBG
        self.tool_widgets, self.head_buttons = [], []
        try:
            self.build()
        finally:
            self._rebuilding = False
        if q:
            self._set_search(q)
            self._ph = False
            self.entry.configure(fg=TXT)
        self.apply_filter()
        self.go(view if view in self.frames else "library")
        root.update_idletasks()

    def seg(self, parent, title, options, getter, setter):
        """A Spotify-like segmented choice: [ A | B | C ]."""
        row = tk.Frame(parent, bg=PNL)
        row.pack(fill="x", padx=18, pady=(8, 0))
        tk.Label(row, text=title, bg=PNL, fg=TXT, font=self.f_title, anchor="w").pack(fill="x")
        box = tk.Frame(row, bg=PNL)
        box.pack(fill="x", pady=(4, 0))
        var = tk.StringVar(value=str(getter()))
        self._svars.append(var)
        if STYLE["btn"] != "flat":                                                  # drawn segments: the chosen one is filled
            chips = []

            def paint(*_a):
                for val, b in chips:
                    on = var.get() == val
                    b.configure(bg=BRN if on else PNL2, fg=BLK if on else TXT)

            def choose(val):
                var.set(val)
                setter(val)
                paint()
            for value, label in options:
                b = ShapeLabel(box, text=label, bg=PNL2, fg=TXT, font=self.f_ui, padx=int(12 * STYLE["pad"]), pady=int(round(6 * STYLE["pad"])), cursor="hand2", shape=STYLE["chip"])
                b.bind("<Button-1>", lambda e, v=str(value): choose(v))
                b.pack(side="left", padx=(0, 4))
                chips.append((str(value), b))
            paint()
            var.trace_add("write", paint)
            return var
        for value, label in options:
            tk.Radiobutton(box, text=label, variable=var, value=str(value), indicatoron=0, selectcolor=BRN, bg=PNL2, fg=TXT, activebackground=HOVER,
                           activeforeground=GOLD, bd=0, relief="flat", highlightthickness=0, padx=12, pady=6, font=self.f_ui,
                           command=lambda v=var: setter(v.get())).pack(side="left", padx=(0, 4))
        return var

    def open_settings(self, section=None):
        """Settings is a page of the window (the last item of the sidebar), not a pop-up any more."""
        if section:
            self.se_sec = section                            # (rofpalys_gui_settings.py scrolls to this section when the page opens)
        self.go("settings")

    def close_settings(self):
        try:
            if self.settings_win is not None:
                self.settings_win.destroy()
        except Exception:
            pass
        self.settings_win = None

    def update_cache_label(self):
        try:
            a, v = M.cache_info()
            self.lbl_cache.configure(text="%s:  %s %.1f MB  ·  %s %.1f MB   (%s)" % (self.T("used"), self.T("s_art"), a, self.T("s_video"), v, M.MEDIA_DIR))
        except Exception:
            pass

    def reset_song(self):
        n = M.reset_song()
        self.msg("%s (%d)" % (self.T("done"), n))
        self.update_cache_label()

    def refetch(self):
        M.refresh()
        self.msg(self.T("loading"))

    def reset_all(self):
        if messagebox.askyesno("Rofpalys", self.T("confirm_all"), parent=self.settings_win or self.root):
            M.reset_all()
            self.msg(self.T("done"))
            self.update_cache_label()

    def media_changed(self):
        self._art_sig = None
        self._vseq = -1
        self._now_wide = None
        self.vstream.stop()
        if self.view == "now":
            self.layout_now()

    def bar_press(self, e):
        self.dragging = max(0.0, min(1.0, e.x / float(max(1, self.bar.winfo_width()))))

    def bar_release(self, e):
        frac, self.dragging = self.dragging, None
        if frac is not None and E.duration_known:
            self.seek(frac * E.total_time_seconds)

    def draw_bar(self, pos, total):
        c, w = self.bar, max(20, self.bar.winfo_width())
        c.delete("all")
        x = int((w - 4) * (self.dragging if self.dragging is not None else min(1.0, pos / total))) + 2 if total > 0 else 2
        paint_track(c, 2, w - 2, 8, x, knob=total > 0)

    def draw_play(self, playing):
        c = self.play_cv
        c.delete("all")
        paint_play(c, playing)

    def lyric_click(self, e):
        ln = int(self.lyr.index("@%d,%d" % (e.x, e.y)).split(".")[0])
        i = self.lyr_tmap.get(ln)                                                    # a click on a translation row = its lyric line
        if i is None:
            i = self.lyr_map.index(ln) if ln in self.lyr_map else -1
        if E.is_synced_lyrics and 0 <= i < len(E.synced_lyrics):
            self.seek(E.synced_lyrics[i][0])

    def lyric_index(self, pos):
        idx = -1
        if E.is_synced_lyrics and E.is_playing:
            for i, (sec, _) in enumerate(E.synced_lyrics):
                if pos >= sec:
                    idx = i
                else:
                    break
        return idx

    def lt_update(self, lines):
        """The translation rows for the lyric lines (None = none to show). The translation module is asked only when the lyrics, the language or the switch changed,
        and once a second while it is still working; what happened is said once (a small message), never repeated."""
        now = time.time()
        sig = (lines, E.current_lang, E.lyric_translate)
        if sig == self.lt_sig and not (self.lt_state == "busy" and now >= self.lt_next):
            return self.lt_rows
        fresh, prev = sig != self.lt_sig, self.lt_state
        self.lt_sig = sig
        if not (E.lyric_translate and lines):
            self.lt_rows, self.lt_state = None, "off"
            return None
        rows, st = E.translation_rows(list(lines))
        self.lt_rows, self.lt_state, self.lt_next = rows, st, now + 1.0
        if st != prev or fresh:
            name = I18N.NAMES.get(E.current_lang, E.current_lang)
            note = {"busy": "lt_busy", "ready": "lt_ready", "same": "lt_same"}.get(st)
            if st in ("net", "quota"):
                self.msg(self.T("lt_none") % self.T("lt_why_net"))
            elif note and not (st == "ready" and prev != "busy"):
                self.msg(self.T(note) % name)
        return rows

    def set_lyric_translate(self, on):
        E.lyric_translate = bool(on)
        E.save_settings()
        try:
            import rofpalys_lyrictrans as LT
            if on:
                LT.MGR.forget()                                                      # a fresh try (an earlier failure is not remembered)
        except Exception:
            pass
        self.lt_sig = None
        self.msg(self.T("lt_on_msg" if on else "lt_off_msg"))

    def update_lyrics(self, pos, idx):
        lyr = self.lyr
        lines = tuple(E.current_lyrics)
        tr = self.lt_update(lines)
        trs = tuple(tr) if tr else None
        if lines != self.lyr_lines or trs != self.lyr_tr:
            self.lyr_lines, self.lyr_tr, self.lyr_idx = lines, trs, -2
            self.lyr_map, self.lyr_tmap = [], {}
            lyr.configure(state="normal")
            lyr.delete("1.0", "end")
            if lines:
                out = []
                for i, ln in enumerate(lines):                                       # a lyric line, and under it its translation (when there is one)
                    out.append(ln)
                    self.lyr_map.append(len(out))
                    t = trs[i] if (trs and i < len(trs)) else ""
                    if t:
                        out.append(t)
                        self.lyr_tmap[len(out)] = i
                lyr.insert("1.0", "\n".join(out))
            else:
                lyr.insert("1.0", self.T("lyr_none"))
            lyr.tag_add("c", "1.0", "end")
            for ln_no in self.lyr_tmap:
                lyr.tag_add("tr", "%d.0" % ln_no, "%d.end" % ln_no)
            lyr.configure(state="disabled")
        if idx != self.lyr_idx:
            self.lyr_idx = idx
            for tg in ("past", "cur", "next", "trpast", "trcur"):
                lyr.tag_remove(tg, "1.0", "end")
            if 0 <= idx < len(self.lyr_map):
                cl = self.lyr_map[idx]                                               # the text line of the lyric line that is sung now
                if cl > 1:
                    lyr.tag_add("past", "1.0", "%d.end" % (cl - 1))
                for ln_no, i in self.lyr_tmap.items():
                    if i < idx:
                        lyr.tag_add("trpast", "%d.0" % ln_no, "%d.end" % ln_no)
                    elif i == idx:
                        lyr.tag_add("trcur", "%d.0" % ln_no, "%d.end" % ln_no)
                lyr.tag_add("cur", "%d.0" % cl, "%d.end" % cl)
                if idx + 1 < len(self.lyr_map):
                    nx = self.lyr_map[idx + 1]
                    lyr.tag_add("next", "%d.0" % nx, "%d.end" % nx)
                if self.view == "now":
                    lyr.see("%d.0" % cl)

    def photo(self, path):
        """PhotoImage from a PNG path. Kept in a small LRU cache (Tk drops an image as soon as Python forgets it)."""
        if not path:
            return None
        img = self._imgs.pop(path, None)
        if img is None:
            try:
                img = tk.PhotoImage(file=path)
            except Exception as e:
                log("photo %s: %r" % (path, e))
                return None
            if len(self._imgs) > 260:
                self._imgs.pop(next(iter(self._imgs)))
        self._imgs[path] = img
        return img

    def layout_now(self):
        """Wide window: art/video on the left, lyrics on the right. Narrow window: art on top, lyrics below."""
        nv = self.nv
        w, h = nv.winfo_width(), nv.winfo_height()
        panel = E.media_lyrics in ("panel", "both")
        mode = (w >= 700, panel)
        if mode[0] and panel and w >= 50:                    # wide: the cover gets the bigger part (about 62 %), the lyrics a column of about 38 % beside it
            lw = max(300, int(w * 0.38))
            if int(self.now_lyr.cget("width") or 0) != lw:
                self.now_lyr.configure(width=lw)
                self._art_sig = None
        if mode == self._now_wide or w < 50:
            return
        self._now_wide = mode
        self.now_media.pack_forget()
        self.now_lyr.pack_forget()
        self.now_lyr.pack_propagate(not (mode[0] and panel))
        if mode[0]:
            self.now_media.pack(side="left", fill="both", expand=True, padx=(18, 8), pady=18)
            if panel:
                self.now_lyr.pack(side="right", fill="y", expand=False, padx=(8, 18), pady=18)
        else:
            self.now_media.pack(side="top", fill="both", expand=True, padx=14, pady=(12, 4))
            if panel:
                self.now_lyr.pack(side="top", fill="both", expand=True, padx=14, pady=(4, 12))
        self._art_sig = None

    def media_loop(self):
        if self.view != "now":
            return
        try:
            self.draw_media()
        except Exception as e:
            log("draw_media: %r" % (e,))
        self.media_job = self.root.after(80, self.media_loop)

    def tint(self, t):
        """Background colour: the classic brown, nudged toward the cover's colour (still brown-black overall)."""
        base = NOWBG
        return lerp(base, t.avg, 0.18) if t and t.avg else base

    def draw_media(self):
        cv, t = self.canvas, M.current()
        cw, ch = cv.winfo_width(), cv.winfo_height()
        if cw < 60 or ch < 60:
            return
        bg = self.tint(t)
        if bg != self._tint:
            self._tint = bg
            for wdg in [self.nv, self.now_media, self.now_lyr, cv, self.lyr, self.now_bar, self.lbl_vmode, self.b_vcover.cv, self.b_vvideo.cv] + self.tool_widgets:
                wdg.configure(bg=bg)
        # --- what to show: video > cover art > placeholder
        use_video = bool(t and t.video_state == "ready" and t.video and E.media_video != "off" and E.media_prefer_video and not self.video_broken)
        seq, frame = self.vstream.latest() if use_video else (-1, None)
        idx = self.lyric_index(E.current_time_seconds)
        caption = ""
        if E.media_lyrics in ("caption", "both") and 0 <= idx < len(E.synced_lyrics):
            caption = E.synced_lyrics[idx][1]
            if caption == LY.NOTE:                           # nobody sings here (drums, instruments): animated notes, like Spotify
                caption = ("♪ " * (1 + int(time.time() * 2) % 3)).strip()
        note = t.note if t else ""
        if not note and not frame and E.media_prefer_video and t and t.video_state in ("missing", "off"):
            note = self.T("no_video")
        art, art_src = "", ""
        if not frame and t and t.art_state == "ready" and t.art:
            # the cover is always a SQUARE (a wide picture is cut from the middle) and as big as the area allows, in steps of 32 pixels
            side = max(ART_MIN, min(ART_MAX, ((min(cw, ch) - 8) // 32) * 32))
            art, art_src = M.get_scaled(t.art, side, True), t.art
        sig = ("v", seq, caption, note, cw, ch) if frame else ("a", art, t.art_state if t else "", caption, note, cw, ch)
        if sig == self._art_sig:
            return
        self._art_sig = sig
        cv.delete("all")
        img = None
        if frame:
            try:
                img = tk.PhotoImage(data=frame[2], format="PPM")
            except Exception as e:                              # this Tk cannot read PPM from memory: fall back to the cover art for good
                log("video frame: %r" % (e,))
                self.video_broken = True
                self.vstream.stop()
                self._art_sig = None
                return
        else:
            img = self.photo(art)
            if img is None and art_src and art_src == self._big_src and self._big is not None:
                img = self._big                                 # the new size is still being made: the old picture stays instead of a flash of the placeholder
        if img is not None:
            self._big = img                                     # keep a reference or Tk shows nothing
            if art_src:
                self._big_src = art_src
            cv.create_image(cw // 2, ch // 2, image=img)
        else:
            self.draw_placeholder(cv, cw, ch, t)
        if caption:                                             # karaoke caption on top of the picture / video
            cv.create_rectangle(0, ch - 86, cw, ch, fill="#000000", stipple="gray50", outline="")
            cv.create_text(cw // 2 + 1, ch - 42 + 1, text=caption, fill="#000000", font=self.f_big, width=cw - 30, justify="center")
            cv.create_text(cw // 2, ch - 42, text=caption, fill=GOLD, font=self.f_big, width=cw - 30, justify="center")
        if note:
            cv.create_text(10, 10, text=note, fill=TXT, font=self.f_small, anchor="nw")

    def draw_placeholder(self, cv, cw, ch, t):
        s = max(120, min(cw, ch) - 40)
        x0, y0 = (cw - s) // 2, (ch - s) // 2
        for i in range(12):                                     # gradient square (brown in Classic, the colours of the look otherwise)
            cv.create_rectangle(x0, y0 + s * i // 12, x0 + s, y0 + s * (i + 1) // 12 + 1, fill=lerp(PH1, PH2, i / 11.0), outline="")
        if STYLE["glow"]:
            neon(cv, x0, y0, x0 + s, y0 + s, BRN2, NOWBG, shape="cut", r=STYLE["r"] * 2)
        letter = ((t.title or t.artist or "♪")[:1]).upper() if t else "♪"
        cv.create_text(cw // 2, ch // 2, text=letter, fill=GOLD, font=(self.f_disp, max(30, s // 4), "bold"))
        cv.create_text(cw // 2, y0 + s - 18, text=self.T("loading") if t and t.art_state == "loading" else self.T("noart"), fill=TXT, font=self.f_small)

    def sync_video(self, t, pos):
        vs = self.vstream
        want = bool(self.view == "now" and not self.video_broken and t and t.video_state == "ready" and t.video and E.media_video != "off" and E.media_prefer_video
                    and E.is_playing and not E.is_paused and shutil.which("ffmpeg"))
        if not want:
            if vs.running:
                vs.stop()
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        size = (min(max(cw, 160), 640), min(max(ch, 90), 400))
        moved = abs(vs.size[0] - size[0]) > 120 or abs(vs.size[1] - size[1]) > 90
        if vs.src != t.video or (not vs.running and not vs.finished) or moved or (vs.running and abs(vs.expected_pos() - pos) > 3.0):
            vs.start(t.video, pos, size[0], size[1])

    def amp(self, i):
        lv = self._lv
        if lv:                                              # the bars follow the real song
            v = lv[i % len(lv)]
            return min(1.0, v * 1.5 if E.x3_vis else v)
        t = self.tick
        if not E.is_playing or E.is_paused:
            return 0.05 + 0.03 * math.sin(t * 0.05 + i)
        v = (math.sin(t * 0.3 + i * 0.2) + math.cos(t * 0.15 - i * 0.4) + 2) / 4 + random.random() * 0.3 * (math.sin(t * 0.6) + 1) + (math.sin(t * 0.4) * 0.3 if i % 4 == 0 else 0)
        return min(1.0, v * 1.5 if E.x3_vis else v)

    def vcol(self, t, i=0):
        return PALETTE[(i + self.tick // 3) % len(PALETTE)] if E.aura_mode else lerp(BRN, GOLD, t)

    def next_anim(self):
        self.anim_idx, self.t_anim = (self.anim_idx + 1) % len(ANIMS), time.time()
        self.msg("Animation: " + ANIMS[self.anim_idx])

    def draw_vis(self):
        if self.view != "visual":
            return
        cv = self.vis
        w, h = cv.winfo_width(), cv.winfo_height()
        cv.delete("all")
        self.tick += 1
        self._lv = E.get_levels(64)                       # real levels of the playing song (None: the simulation is used)
        if w > 60 and h > 60:
            idx = self.anim_idx if E.is_playing else 4
            n = max(12, min(64, w // 14))
            if not E.anim_enabled:
                cv.create_text(w // 2, h // 2, text="~  animations off  ~", fill=DIM, font=self.f_big)
            elif idx in (0, 1):
                bw = w / float(n)
                for i in range(n):
                    v = self.amp(i)
                    if idx == 0:
                        cv.create_rectangle(i * bw + 2, h - 8 - v * (h - 24), (i + 1) * bw - 2, h - 8, fill=self.vcol(v, i), outline="")
                    else:
                        cv.create_rectangle(i * bw + 2, h / 2 - v * h * 0.45, (i + 1) * bw - 2, h / 2 + v * h * 0.45, fill=self.vcol(v, i), outline="")
            elif idx == 2:
                for k in range(3):
                    pts = []
                    for x in range(0, w, 8):
                        pts += [x, h / 2 + math.sin(x * 0.02 * (k + 1) + self.tick * 0.12 * (k + 1)) * (h * 0.15 + self.amp(x // 8) * h * 0.25)]
                    cv.create_line(*pts, fill=PALETTE[1 + k * 2], width=2, smooth=True)
            elif idx == 3:
                lim = min(w, h) * 0.6
                for r in range(1, 8):
                    rad = ((self.tick * 3 + r * 40) % lim) * (1 + self.amp(r) * 0.4)
                    cv.create_oval(w / 2 - rad, h / 2 - rad, w / 2 + rad, h / 2 + rad, outline=PALETTE[r % 6], width=2)
            elif idx == 4:
                nc = max(8, w // 16)
                if len(self.rain) != nc:
                    self.rain = [random.randint(-h, 0) for _ in range(nc)]
                for i in range(nc):
                    self.rain[i] += 6 + (i % 3) * 3
                    if self.rain[i] > h + 90:
                        self.rain[i] = -random.randint(0, 200)
                    for k in range(5):
                        cv.create_text(i * 16 + 8, self.rain[i] - k * 16, text=random.choice("ABCDEF0123456789$#@*+=<>"),
                                       fill=TXT if k == 0 else PALETTE[max(0, 5 - k)], font=self.f_mono)
            else:
                while len(self.stars) < 70:
                    self.stars.append([random.random() * 6.283, random.random() * 20, 1 + random.random() * 3])
                for s in self.stars:
                    s[1] += s[2] * (1 + self.amp(int(s[0] * 5)) * 2)
                    if s[1] > max(w, h):
                        s[:] = [random.random() * 6.283, 0, 1 + random.random() * 3]
                    x, y, r = w / 2 + math.cos(s[0]) * s[1], h / 2 + math.sin(s[0]) * s[1] * 0.7, 1 + s[1] / 150
                    cv.create_oval(x - r, y - r, x + r, y + r, fill=PALETTE[int(s[2]) % 6], outline="")
        self.vis_job = self.root.after(70, self.draw_vis)

    def poll(self):
        try:
            if not self._rebuilding:                           # (never against a half-built window)
                self._poll()
        except Exception as e:
            log("poll: %r" % (e,))
        self.root.after(200, self.poll)

    def update_thumb(self, t):
        path = M.get_scaled(t.art, 64) if t and t.art_state == "ready" and t.art else ""
        img = self.photo(path)
        self._thumb = img
        cv = self.thumb
        cv.delete("all")
        if img is not None:
            cv.create_image(32, 32, image=img)
        else:
            self.draw_square(cv, 0, 0, 64, (t.title if t else "") or "", "song")

    def _poll(self):
        now = time.time()
        dt, self.last_poll = min(1.0, now - self.last_poll), now
        if self._term:
            self.quit()
            return
        if E.library_version != self._libver:             # a scan finished: rebuild groups and the page
            self._libver = E.library_version
            self.rebuild_groups()
            self.apply_filter()
        if M.thumb_version != self._tver:                 # new cover pictures were found: repaint
            self._tver = M.thumb_version
            self.rows.redraw()
            if self.group:
                self.draw_head_cover()
        name = E.playing_song_name
        if name != self.seen:
            self.seen = name
            self.rows.redraw()
            self.vstream.stop()
            self._art_sig, self._vseq = None, -1
            M.on_song(name)
        playing = E.is_playing and not E.is_paused
        pos, total = self.position(), (E.total_time_seconds if E.duration_known else 0)
        t = M.current()
        ver = (t.version, t.path) if t else (0, "")
        if ver != self._mver or (t and t.art_state == "ready" and self._thumb is None):
            self._mver = ver
            self.update_thumb(t)
            self._art_sig = None
        self.sync_video(t, pos)
        self.draw_play(playing)
        self.extra_poll()
        self.lbl_title.configure(text=self.fit(E.title_of(name), "title", 190) if name else self.T("nomusic"))
        sub = t.artist if (t and t.artist) else (os.path.basename(os.path.dirname(name)) if name else "")
        self.lbl_sub.configure(text=self.fit(sub, "small", 190))
        self.lbl_pos.configure(text=hms(pos))
        self.lbl_dur.configure(text=E.total_time_str if E.duration_known else "--:--")
        self.draw_bar(pos, total)
        fav = bool(name) and name in E.favorites
        self.b_fav.set(kind="heart_on" if fav else "heart", color=RED if fav else DIM)
        self.update_modes()
        if E.volume != self._vol_seen:
            self.draw_vol()
        self.lbl_side.configure(text="%s%s%s\n%d %s" % (E.engine_name(), "  [DJ]" if E.auto_dj else "", "  [AURA]" if E.aura_mode else "", len(E.songs_all), self.T("songs")))
        self.update_lyrics(pos, self.lyric_index(pos))
        if E.is_downloading:
            st, col = "⬇ yt-dlp  %s" % E.dl_progress_text, GOLD
        elif E.engine_status_msg and now - E.engine_status_time < 4:
            st, col = "⚠ " + E.engine_status_msg, RED
        elif E.info_msg and now - E.info_time < 2:
            st, col = E.info_msg, GOLD
        elif E.scanning:
            st, col = self.T("scanning"), GOLD
        elif t and t.note and (t.art_state == "loading" or t.video_state == "loading"):
            st, col = "⬇ " + t.note, GOLD
        else:
            st, col = "", DIM
        self.status.configure(text=st, fg=col)
        if E.is_playing and E.anim_enabled and self.cfg["anim_auto"] and now - self.t_anim > 8:
            self.anim_idx, self.t_anim = (self.anim_idx + 1) % len(ANIMS), now
        if name and E.is_playing and now - self.t_save > 5:
            self.cfg["last"], self.t_save = {"song": name, "pos": int(pos)}, now
            self.save_cfg()

    def save_ui(self):
        self.cfg["ui"] = {"view": self.view if self.view in ("library", "now", "visual") else "library", "chip": self.chip, "group": self.group,
                          "side": "open" if getattr(self, "side_open", True) else "closed"}
        self.save_cfg()

    def save_geo(self):
        self._geo_job = None
        try:
            self.cfg["geometry"] = self.root.geometry()
            self.save_cfg()
        except Exception:
            pass

    def tw(self, text, key="ui"):
        return self.mf[key].measure(text)

    def fit(self, text, key, maxw):
        """text cut with an ellipsis so that it fits maxw pixels."""
        if maxw < 24:
            return ""
        ck = (text, key, maxw)
        r = self._fitc.get(ck)
        if r is not None:
            return r
        f = self.mf[key]
        if f.measure(text) <= maxw:
            r = text
        else:
            lo, hi = 0, len(text)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if f.measure(text[:mid] + "…") <= maxw:
                    lo = mid
                else:
                    hi = mid - 1
            r = text[:lo].rstrip() + "…"
        if len(self._fitc) > 3000:
            self._fitc.clear()
        self._fitc[ck] = r
        return r

    def empty_text(self):
        if E.scanning and not E.songs_all:
            return self.T("scanning")
        if self.query():
            return self.T("no_results")
        for fn in self.empty_hooks:
            s = fn(self)
            if s:
                return s
        if self.chip == "favorites" and not self.group:
            return self.T("empty_fav")
        return self.T("empty")

    def thumb_image(self, path, size, square=False):
        p = M.thumb(path, size, square)
        return self.photo(p) if p else None

    def draw_square(self, cv, x, y, size, seed, kind):
        shade = COVER_SHADES[zlib.crc32(seed.encode("utf-8", "replace")) % len(COVER_SHADES)]
        if STYLE["shape"] == "flat":
            cv.create_rectangle(x, y, x + size, y + size, fill=shade, outline="")
            cv.create_rectangle(x, y + size * 2 // 3, x + size, y + size, fill=lerp(shade, BLK, 0.35), outline="")
        else:                                                   # rounded / cut cover tile
            rr_ = max(4, size // 8)
            draw_shape(cv, x, y, x + size, y + size, fill=shade, shape=STYLE["shape"], r=rr_)
            draw_shape(cv, x, y + size * 2 // 3, x + size, y + size, fill=lerp(shade, BLK, 0.35), shape=STYLE["shape"], r=rr_)
        if kind == "group":
            draw_icon(cv, "folder", x + size / 2.0, y + size / 2.0, size * 0.42, GOLD)
        else:
            letter = (seed.strip()[:1] or "").upper()
            if letter.isalnum():
                cv.create_text(x + size / 2.0, y + size / 2.0, text=letter, fill=GOLD, font=(self.f_disp, max(9, size // 2), "bold"))
            else:
                draw_icon(cv, "note", x + size / 2.0, y + size / 2.0, size * 0.42, GOLD)

    def group_cover(self, it, size):
        """('mosaic', 4 images) | ('single', 1 image) | ('none', [])  - up to 4 different covers from the group's first songs."""
        seen, picks = set(), []
        for p in it.get("cover", [])[:8]:
            a = M.art_of(p)
            if a and a not in seen:
                seen.add(a)
                picks.append(p)
            if len(picks) == 4:
                break
        if len(picks) == 4:
            imgs = [self.thumb_image(p, size // 2) for p in picks]
            if all(imgs):
                return "mosaic", imgs
        if picks:
            img = self.thumb_image(picks[0], size)
            if img is not None:
                return "single", [img]
        return "none", []

    def draw_cover(self, cv, x, y, size, it):
        if it["kind"] == "group":
            mode, imgs = self.group_cover(it, size)
            if mode == "mosaic":
                h = size // 2
                for k, img in enumerate(imgs):
                    cv.create_image(x + (k % 2) * h + h // 2, y + (k // 2) * h + h // 2, image=img)
                return
            if mode == "single":
                cv.create_image(x + size // 2, y + size // 2, image=imgs[0])
                return
            self.draw_square(cv, x, y, size, it["title"], "group")
            return
        img = self.thumb_image(it["path"], size)
        if img is not None:
            cv.create_image(x + size // 2, y + size // 2, image=img)
        else:
            self.draw_square(cv, x, y, size, it["title"], "song")

    def rebuild_groups(self):
        self.cats, self.folders = L.build_groups(E.songs_all)
        self.artists, self.mixes = L.build_extra_groups(E.songs_all)
        self.extra_groups = []
        for fn in self.group_providers:
            try:
                self.extra_groups += fn(self)
            except Exception as e:
                log("group provider: %r" % (e,))
        self.gmap = {g["id"]: g for g in self.cats + self.folders + self.artists + self.mixes + self.extra_groups}

    def query(self):
        return "" if self._ph else self.v_search.get().strip()

    def _set_search(self, text):
        self._ph_lock = True
        try:
            self.v_search.set(text)
        finally:
            self._ph_lock = False

    def ph_show(self):
        if not self.v_search.get().strip() or self._ph:
            self._ph = True
            self.entry.configure(fg=DIM)
            self._set_search(self.T("search_ph"))

    def ph_in(self, e=None):
        if self._ph:
            self._ph = False
            self.entry.configure(fg=TXT)
            self._set_search("")

    def ph_out(self, e=None):
        if not self._ph and not self.v_search.get().strip():
            self.ph_show()

    def on_query(self):
        if self._ph_lock:
            return
        if self._qjob:
            self.root.after_cancel(self._qjob)
        self._qjob = self.root.after(160, self.apply_filter)

    def sorted_paths(self, paths):
        mode = self.cfg["sort"]
        if mode == "recent":
            return sorted(paths, key=lambda p: -E.library_mtimes.get(p, 0))
        if mode == "plays":
            return sorted(paths, key=lambda p: -self.cfg["stats"].get(p, {}).get("plays", 0))
        return list(paths)

    def song_item(self, p):
        m = self._meta.get(p)
        if m is None:
            a, t = M.name_meta(p)
            m = self._meta[p] = (t or E.title_of(p), a or L.folder_label(os.path.dirname(p)))
        plays = self.cfg["stats"].get(p, {}).get("plays", 0)
        return {"kind": "song", "path": p, "title": m[0], "sub": m[1], "right": ("%dx" % plays) if plays else ""}

    def group_item(self, g):
        n = len(g["paths"])
        sub = "%s  •  %d %s" % (self.T(self.kind_labels.get(g["kind"], "folder")), n, self.T("songs"))
        if g["sub"]:
            sub += "  •  " + g["sub"]
        return {"kind": "group", "gid": g["id"], "title": g["name"], "sub": sub, "cover": g["paths"][:8], "paths": g["paths"], "path": "", "photo": g.get("photo", ""), "gkind": g["kind"]}

    def header_item(self, title):
        return {"kind": "header", "title": title}

    def search_items(self, q):
        T, items = self.T, []
        res = L.smart_search(q, E.songs_all, self.cfg["stats"], E.favorites, 40)
        groups = L.match_groups(q, self.cats + self.folders + self.artists + self.mixes + self.extra_groups)
        if res:
            items += [self.header_item(T("top_result")), self.song_item(res[0][0])]
            if len(res) > 1:
                items.append(self.header_item(T("songs_h")))
                items += [self.song_item(p) for p, _ in res[1:]]
            if groups:
                items.append(self.header_item(T("folders_h")))
                items += [self.group_item(g) for g in groups]
            sim = L.similar(res[0][0], E.songs_all, exclude=[p for p, _ in res], limit=8)
            if sim:
                a, t = M.name_meta(res[0][0])
                items.append(self.header_item(T("more_like") % (a or t or E.title_of(res[0][0]))))
                items += [self.song_item(p) for p in sim]
        else:
            if groups:
                items.append(self.header_item(T("folders_h")))
                items += [self.group_item(g) for g in groups]
            dym = L.did_you_mean(q, E.songs_all)
            if dym:
                items.append({"kind": "suggest", "title": T("did_you_mean") % dym, "query": dym})
        return items

    def home_items(self):
        T, items = self.T, []
        titles = {"recent": "recent", "mix": "mix", "favorites": "favorites_h", "top": "top", "new": "new", "discover": "discover"}
        secs = L.home_sections(E.songs_all, self.cfg["stats"], E.favorites, E.library_mtimes, self.cfg["last"].get("song"))
        for key, paths in secs:
            items.append(self.header_item(T(titles[key])))
            items += [self.song_item(p) for p in paths]
        if self.cats:
            items.append(self.header_item(T("categories")))
            items += [self.group_item(g) for g in self.cats]
        if self.folders:
            items.append(self.header_item(T("folders")))
            items += [self.group_item(g) for g in self.folders[:10]]
        return items

    def page_items(self):
        q = self.query()
        if q:
            return self.search_items(q)
        g = self.gmap.get(self.group) if self.group else None
        if g:
            return [self.song_item(p) for p in self.sorted_paths(g["paths"])]
        page = self.chip_pages.get(self.chip)
        if page:
            return page(self)
        if self.chip == "songs":
            return [self.song_item(p) for p in self.sorted_paths(E.songs_all)]
        if self.chip == "categories":
            items = [self.group_item(g) for g in self.cats]
            if self.mixes:
                items.append(self.header_item(self.T("mixes")))
                items += [self.group_item(g) for g in self.mixes]
            return items
        if self.chip == "folders":
            return [self.group_item(g) for g in self.folders]
        if self.chip == "artists":
            return [self.group_item(g) for g in self.artists]
        if self.chip == "favorites":
            return [self.song_item(p) for p in self.sorted_paths([p for p in E.songs_all if p in E.favorites])]
        return self.home_items()

    def update_head(self):
        T, q = self.T, self.query()
        g = self.gmap.get(self.group) if (self.group and not q) else None
        self.head_back.forget()
        for w in (self.head_cover, self.htxt, self.head_btns):
            w.pack_forget()
        for b, _lk, _kinds in self.head_buttons:
            b.pack_forget()
        if g:
            self.head_back.pack(side="left", padx=(0, 4))
            self.head_cover.pack(side="left", padx=(0, 14))
            self.htxt.pack(side="left", fill="x", expand=True)
            self.head_btns.pack(side="right")
            sub = "%s  •  %d %s" % (T(self.kind_labels.get(g["kind"], "folder")), len(g["paths"]), T("songs"))
            self.lbl_head.configure(text=self.fit(g["name"], "head", 380))
            self.lbl_hsub.configure(text=sub + (("  •  " + g["sub"]) if g["sub"] else ""))
            self.draw_head_cover()
            for b, _lk, kinds in self.head_buttons:
                if g["kind"] in kinds:
                    b.pack(side="left", padx=(8, 0))
        else:
            self.htxt.pack(side="left", fill="x", expand=True)
            self.lbl_head.configure(text=T("search_results") if q else T(dict(self.chip_labels()).get(self.chip, self.chip)))
            self.lbl_hsub.configure(text="%d %s" % (len(E.songs_all), T("songs")))

    def draw_head_cover(self):
        g = self.gmap.get(self.group)
        cv = self.head_cover
        cv.delete("all")
        if g:
            self.draw_cover(cv, 0, 0, 104, self.group_item(g))

    def fit_chips(self):
        """A language with long words (German, Russian) makes the row of chips wider than the window: the chips get less padding, down to 3 px, until the row fits."""
        if getattr(self, "_chip_fitting", False):
            return
        row, btns = getattr(self, "chip_row", None), list(getattr(self, "chip_btns", {}).values())
        if row is None or not btns:
            return
        self._chip_fitting = True
        try:
            avail = int(row.winfo_width())
            if avail < 100:
                return
            base = 14 if STYLE["chip"] == "flat" else int(14 * STYLE["pad"])
            icons = bool(STYLE["icons"]) and STYLE["chip"] != "flat"
            done = False
            for with_icon in ((True, False) if icons else (False,)):      # first with the icons; a phone-wide window drops them before it cuts a chip off
                if icons:
                    for k, b in self.chip_btns.items():
                        b.configure(icon=CHIP_ICONS.get(k) if with_icon else None)
                for pad in range(base, 2, -1):
                    for b in btns:
                        b.configure(padx=pad)
                    row.update_idletasks()
                    if sum(int(b.winfo_reqwidth()) for b in btns) + 6 * len(btns) <= avail:
                        done = True
                        break
                if done:
                    break
        except tk.TclError:
            pass
        finally:
            self._chip_fitting = False

    def style_chips(self):
        for k, b in self.chip_btns.items():
            on = k == self.chip
            b.configure(bg=GOLD if on else PNL2, fg=BLK if on else TXT)

    def set_chip(self, chip):
        self.chip, self.group = chip, ""
        if self._ph is False and self.v_search.get():
            self._set_search("")
            self.ph_show()
        if self.view != "library":
            self.go("library")
            return
        self.apply_filter()
        self.save_ui()

    def open_group(self, gid):
        if gid in self.gmap:
            self.group = gid
            if self.view != "library":
                self.go("library")
                return
            self.apply_filter()
            self.save_ui()

    def close_group(self):
        self.group = ""
        self.apply_filter()
        self.save_ui()

    def play_group(self, shuffle=False):
        g = self.gmap.get(self.group)
        if not g or not g["paths"]:
            return
        paths = self.sorted_paths(g["paths"])
        if shuffle:
            E.play_mode = 4
            E.save_settings()
            self.update_modes()
        self.play(random.choice(paths) if shuffle else paths[0])

    def on_row_activate(self, it):
        if it["kind"] == "song":
            self.play(it["path"])
        elif it["kind"] == "group":
            self.open_group(it["gid"])
        elif it["kind"] == "action":
            h = self.action_handlers.get(it.get("action"))
            if h:
                h(self)
        elif it["kind"] == "suggest":
            self.ph_in()
            self._set_search(it["query"])
            self.apply_filter()

    def row_menu(self, it, e):
        T = self.T
        m = tk.Menu(self.root, tearoff=0, bg=PNL2, fg=TXT, activebackground=BRN, activeforeground=BLK, bd=0, font=self.f_ui)
        if it["kind"] == "song":
            p = it["path"]
            m.add_command(label=T("play"), command=lambda: self.play(p))
            for fn in self.row_menu_hooks:                 # play next, add to queue, add to playlist ... (from the feature files)
                try:
                    fn(self, m, it)
                except Exception as ex:
                    log("row menu hook: %r" % (ex,))
            m.add_command(label=T("favorites"), command=lambda: self.toggle_fav(p))
            d = "dir:" + os.path.dirname(p)
            if d in self.gmap:
                m.add_command(label=T("folder") + ":  " + self.gmap[d]["name"], command=lambda: self.open_group(d))
            m.add_command(label=L.short_path(p), command=lambda: messagebox.showinfo("Rofpalys", p, parent=self.root))
        else:
            gid = it["gid"]
            m.add_command(label=T("library"), command=lambda: self.open_group(gid))
            for fn in self.group_menu_hooks:
                try:
                    fn(self, m, it)
                except Exception as ex:
                    log("group menu hook: %r" % (ex,))
        m.tk_popup(e.x_root, e.y_root)

    def draw_vol(self):
        c = self.volcv
        w = max(40, int(c.winfo_width()))
        v = E.volume
        self._vol_seen = v
        c.delete("all")
        paint_track(c, 6, w - 6, 10, 6 + (w - 12) * v / 100.0)

    def vol_event(self, e):
        w = max(40, int(self.volcv.winfo_width()))
        self.set_volume(int(max(0, min(100, (e.x - 6) * 100.0 / (w - 12)))))
        self.draw_vol()

    def scrollable(self, parent):
        """A frame inside a scrollable canvas (mouse wheel works anywhere in the window). Pack your widgets into the returned frame."""
        cv = tk.Canvas(parent, bg=PNL, highlightthickness=0)
        sb = tk.Scrollbar(parent, command=cv.yview, bg=PNL2, troughcolor=PNL, bd=0, highlightthickness=0, width=10, activebackground=BRN)
        body = tk.Frame(cv, bg=PNL)
        win = cv.create_window(0, 0, window=body, anchor="nw")
        body.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        def wheel(e):
            num = e.num if isinstance(getattr(e, "num", 0), int) else 0
            cv.yview_scroll(-1 if (num == 4 or (getattr(e, "delta", 0) or 0) > 0) else 1, "units")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            parent.bind(seq, wheel)
        return body

    def popup(self, title, w, h):
        top = tk.Toplevel(self.root)
        top.title("Rofpalys - " + title)
        top.configure(bg=PNL)
        top.transient(self.root)
        top.geometry("%dx%d" % (w, min(h, max(380, self.root.winfo_screenheight() - 90))))
        return top

    def build_now_bar(self, nv):
        bar = tk.Frame(nv, bg=PNL)
        bar.pack(side="top", fill="x", padx=14, pady=(8, 0))
        self.now_bar = bar
        self.b_vcover = IconBtn(bar, "headphones", lambda: self.set_view_mode(False), size=20, bg=PNL, pad=7)
        self.b_vvideo = IconBtn(bar, "video", lambda: self.set_view_mode(True), size=20, bg=PNL, pad=7)
        self.b_vcover.pack(side="left")
        self.b_vvideo.pack(side="left")
        self.lbl_vmode = tk.Label(bar, text="", bg=PNL, fg=DIM, font=self.f_small)
        self.lbl_vmode.pack(side="left", padx=8)
        self.tool_widgets = []
        for order, fn in sorted(self.toolbar_builders, key=lambda x: x[0]):      # lowest order = rightmost
            try:
                self.tool_widgets += list(fn(self, bar) or [])
            except Exception as e:
                log("toolbar builder: %r" % (e,))
        self.style_toolbar()

    def style_toolbar(self):
        vid = bool(E.media_prefer_video)
        self.b_vvideo.set(color=GOLD if vid else DIM)
        self.b_vcover.set(color=DIM if vid else GOLD)
        self.lbl_vmode.configure(text=self.T("view_video") if vid else self.T("view_cover"))
        for fn in self.toolbar_styles:
            try:
                fn(self)
            except Exception as e:
                log("toolbar style: %r" % (e,))

    def set_view_mode(self, video):
        """🎧 = only the cover picture (+ lyrics)   ▶ = only the video (+ lyrics)."""
        E.media_prefer_video = bool(video)
        E.save_settings()
        self.style_toolbar()
        self.media_changed()
        M.refresh()

    def extra_poll(self):
        self.style_toolbar()
        for fn in self.poll_hooks:
            try:
                fn(self)
            except Exception as e:
                log("poll hook: %r" % (e,))

    def init_registries(self):
        self.nav_entries = [(10, "library", "home", "home"), (20, "favorites", "favorites", "heart"), (30, "visual", "visual", "wave"), (50, "now", "now", "note"),
                            (90, "settings", "settings", "gear")]
        self.chip_defs = [(10, "home", "home"), (20, "songs", "songs_chip"), (50, "artists", "artists"), (90, "favorites", "favorites")]
        self.chip_pages, self.view_builders, self.view_show, self.action_handlers = {}, {}, {}, {}
        self.row_menu_hooks, self.group_menu_hooks, self.menu_hooks, self.toolbar_builders, self.toolbar_styles = [], [], [], [], []
        self.poll_hooks, self.group_providers, self.head_button_defs, self.relabel_hooks, self.build_hooks, self.empty_hooks = [], [], [], [], [], []
        self.kind_labels = {"category": "category", "folder": "folder", "artist": "artist", "mix": "mix_kind"}
        self.tool_widgets, self.head_buttons, self.extra_groups, self.features_loaded = [], [], [], []

    def add_texts(self, **langs):
        """add_texts(en={"key": "text"}, id={"key": "teks"}) - texts of your feature (any language that is missing falls back to English)."""
        for lang, d in langs.items():
            TXT_.setdefault(lang, {}).update(d)

    def add_nav(self, order, key, label_key, icon):
        self.nav_entries.append((order, key, label_key, icon))

    def add_view(self, key, builder, show=None):
        """A whole page. builder(app) returns a Frame (its parent is app.main); show(app) is called every time the page is opened."""
        self.view_builders[key] = builder
        if show:
            self.view_show[key] = show

    def add_chip(self, order, key, label_key, page_fn):
        """A tab in the library (next to Home / Songs / ...). page_fn(app) returns the list of rows of the page."""
        self.chip_defs.append((order, key, label_key))
        self.chip_pages[key] = page_fn

    def add_row_menu(self, fn):
        self.row_menu_hooks.append(fn)              # fn(app, menu, item): items of the right-click menu of a SONG

    def add_group_menu(self, fn):
        self.group_menu_hooks.append(fn)            # fn(app, menu, item): right-click menu of a folder / artist / playlist row

    def add_menu(self, label_key, fn):
        self.menu_hooks.append((label_key, fn))     # entry in the ... menu: fn(app)

    def add_toolbar(self, order, builder, style=None):
        """Buttons in the Now Playing toolbar. builder(app, bar) packs its widgets (side='right') and returns them; style(app) is called often."""
        self.toolbar_builders.append((order, builder))
        if style:
            self.toolbar_styles.append(style)

    def add_poll(self, fn):
        self.poll_hooks.append(fn)                  # fn(app) every 0.2 s

    def add_group_provider(self, fn):
        self.group_providers.append(fn)             # fn(app) -> [{"id","kind","name","sub","paths"}]  (shown like folders)

    def add_head_button(self, label_key, fn, kinds):
        self.head_button_defs.append((label_key, fn, tuple(kinds)))   # button in the header of a group page, only for these group kinds

    def add_relabel(self, fn):
        self.relabel_hooks.append(fn)               # fn(app): re-set your texts after a language change

    def add_build(self, fn):
        self.build_hooks.append(fn)                 # fn(app) after the window exists

    def add_action(self, name, fn):
        self.action_handlers[name] = fn             # a row {"kind": "action", "action": name} was clicked

    def add_empty_text(self, fn):
        self.empty_hooks.append(fn)                 # fn(app) -> text or "" for an empty list

    def add_kind_label(self, kind, label_key):
        self.kind_labels[kind] = label_key

    def chip_keys(self):
        return [k for _, k, _ in sorted(self.chip_defs)]

    def nav_list(self):
        return sorted(self.nav_entries)

    def chip_labels(self):
        return [(k, lk) for _, k, lk in sorted(self.chip_defs)]

    def open_shortcuts(self):
        self.popup_text(self.T("shortcuts"), self.T("shortcuts_text") + "\n\n" + self.T("features") + ":\n  " + "\n  ".join(
            [m.split("rofpalys_gui_")[-1] for m in self.features_loaded] + ["! %s: %s (%s)" % (n, self.T("feat_failed"), why[:60]) for n, why in self.feature_errors]))


FEATURE_MODS, FEATURE_ERRORS = [], []


def _load_features():
    """Every rofpalys_gui_<name>.py next to this file is a feature: it is imported and plugs itself in (see register() in each file).
    A feature that fails to load is skipped - the window still opens (the error is listed under  ? > Features loaded)."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        names = sorted(os.listdir(here))
    except OSError:
        return
    found = []
    for f in names:
        m = re.match(r"^(rofpalys_gui_[a-z0-9_]+)\.py$", f)
        if not m or m.group(1) == "rofpalys_gui_base":
            continue
        try:
            mod = importlib.import_module(m.group(1))
        except Exception as e:
            FEATURE_ERRORS.append((m.group(1), repr(e)))
            log("feature %s: %r" % (m.group(1), e))
            continue
        meta = getattr(mod, "FEATURE", None)
        if isinstance(meta, dict) and meta.get("enabled", True) and callable(getattr(mod, "register", None)):
            found.append((meta.get("order", 100), m.group(1), mod))
    found.sort(key=lambda x: (x[0], x[1]))
    FEATURE_MODS.extend(mod for _, _, mod in found)


_load_features()


class App(*[m.Mixin for m in FEATURE_MODS if hasattr(m, "Mixin")], CoreApp):
    """The window = the core + the methods of every feature file (their Mixin classes)."""



def _alive(pid):
    if os.name == "nt":
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            return b"rofpalys" in f.read()
    except OSError:
        return True


def _running():
    """pid of another Rofpalys window that is still open (0 if none). Two windows would overwrite each other's saved settings."""
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0
    return pid if pid and pid != os.getpid() and _alive(pid) else 0


def _release():
    try:
        with open(PID_FILE) as f:
            if int(f.read().strip() or 0) == os.getpid():
                os.remove(PID_FILE)
    except (OSError, ValueError):
        pass


def _acquire():
    try:
        os.makedirs(lib.CACHE_DIR, exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        atexit.register(_release)
    except OSError:
        pass


def _detach(paths):
    """Started from a terminal: relaunch in the background so the terminal can be closed."""
    if "--fg" in sys.argv or os.environ.get("ROFX_CHILD") == "1" or not sys.stdout.isatty():
        return False
    try:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--fg"] + list(paths), start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ, ROFX_CHILD="1"))
        return True
    except OSError:
        return False


def main(paths=None):
    paths = list(paths or [])
    if tk is None:
        print("The GUI needs Tk.  Termux: pkg install python-tkinter     Debian/Ubuntu: sudo apt install python3-tk")
        return 1
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("The GUI needs a graphical display (DISPLAY is not set). Start your desktop/VNC first, or use the terminal UI:  rofpalys")
        return 1
    other = 0 if "--force" in sys.argv else _running()
    if other:
        print("Rofpalys is already open (pid %d). Close that window first, or run:  rofpalys gui --force" % other)
        return 0
    if _detach(paths):
        return 0
    _acquire()
    root = tk.Tk()
    try:
        app = App(root, paths)
    except Exception as e:
        log("start failed: %r" % (e,))
        messagebox.showerror("Rofpalys", "Could not start:\n%s" % e)
        return 1
    for name in ("SIGTERM", "SIGHUP", "SIGINT"):            # closed from outside (killed, session ended): still save everything
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), lambda *a: setattr(app, "_term", True))
            except (ValueError, OSError):
                pass
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(lib.resolve_inputs([a for a in sys.argv[1:] if a not in ("--fg", "--force")])[0]))

# END-OF-FILE rofpalys_gui.py
