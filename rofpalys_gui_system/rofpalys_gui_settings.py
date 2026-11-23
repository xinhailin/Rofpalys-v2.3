#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: the Settings page (a whole page of the window, as in Spotify)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""Settings is the last item of the sidebar. One calm page that scrolls, in sections, each setting a row with its name and a short line under it on the left and the
control (a switch, a choice, a button) on the right:

  Display          look and colours (Classic / Modern / Cyberpunk), layout of Home, sidebar, animations
  Playback         engine, Auto DJ, sound effects, notification buttons
  Library          music folders, only Termux, rescan, download (yt-dlp), playlists import
  Lyrics & media   cover art, video, lyrics (where they come from, translation), cache
  Language         the six languages
  Tools            what the other feature files bring (goals, remote, mixes ...)
  Data             backup, restore, shortcuts, reset
  About            version and who made it
Everything that was in the "..." menu and in the old Settings window is here; nothing of it is lost. The chips at the top jump to a section.
A feature file plugs into the window with register(app) and brings its methods in the Mixin class (see rofpalys_gui_template.py)."""
import os

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    import rofpalys_theme as TH
except Exception:
    TH = None
try:
    import rofpalys_gui_theme as GT
except Exception:
    GT = None

FEATURE = {"name": "settings", "title": "Settings page (display, playback, library, lyrics, language, data)", "version": "1.0", "order": 90, "enabled": True}
SECTIONS = ("display", "playback", "library", "lyrics", "language", "tools", "data", "about")
SKIP_TOOLS = ("sel_mode", "pl_save_page", "pl_import")           # pl_import has its own row in Library; the other two work on the list that is on screen
MAX_W = 820


def _t(text):
    return I18N.tr(text)


class Mixin:
    # ------------------------------------------------------------------ the controls
    def se_switch(self, parent, getter, setter):
        bg = parent.cget("bg")
        cv = tk.Canvas(parent, width=48, height=28, bg=bg, highlightthickness=0, cursor="hand2")

        def paint():
            on = bool(getter())
            cv.delete("all")
            pill = STYLE["btn"] == "pill"
            r = 12 if pill else 4
            draw_shape(cv, 2, 3, 46, 25, fill=GOLD if on else GRID, outline="" if on else DIM, shape=STYLE["btn"], r=r)
            kx = 35 if on else 13
            if pill:
                cv.create_oval(kx - 9, 5, kx + 9, 23, fill=BLK if on else TXT, outline="")
            else:
                cv.create_rectangle(kx - 8, 6, kx + 8, 22, fill=BLK if on else TXT, outline="")

        def click(_e=None):
            setter(not bool(getter()))
            paint()
        cv.bind("<Button-1>", click)
        paint()
        return cv

    def se_choice(self, parent, options, getter, setter, cols=None):
        """A segmented choice: [ A | B | C ]; the chosen one is filled. options = [(value, text)]."""
        bg = parent.cget("bg")
        box = tk.Frame(parent, bg=bg)
        chips = []
        n = cols or (len(options) if len(options) <= 4 else 3)

        def paint():
            cur = str(getter())
            for val, b in chips:
                on = val == cur
                b.configure(bg=GOLD if on else PNL2, fg=BLK if on else TXT)

        def choose(val, raw):
            setter(raw)
            paint()
        for i, (raw, label) in enumerate(options):
            if STYLE["chip"] == "flat":
                b = tk.Label(box, text=label, bg=PNL2, fg=TXT, font=self.f_ui, padx=14, pady=6, cursor="hand2")
            else:
                b = ShapeLabel(box, text=label, bg=PNL2, fg=TXT, font=self.f_ui, padx=int(14 * STYLE["pad"]), pady=int(round(6 * STYLE["pad"])), cursor="hand2", shape=STYLE["chip"], pbg=bg)
            b.grid(row=i // n, column=i % n, padx=(0, 6), pady=(0, 6), sticky="w")
            b.bind("<Button-1>", lambda e, v=str(raw), r=raw: choose(v, r))
            chips.append((str(raw), b))
        paint()
        return box

    def se_button(self, parent, text, cmd, danger=False, primary=False):
        return self.btn(parent, text, cmd, bg=GOLD if primary else PNL2, fg=BLK if primary else (RED if danger else TXT), padx=16, pady=6, font=self.f_ui_b if primary else self.f_ui)

    def se_heading(self, parent, key, text):
        fr = tk.Frame(parent, bg=PNL)
        fr.pack(fill="x", pady=(30, 4))
        tk.Frame(fr, bg=GRID, height=1).pack(fill="x", pady=(0, 18))
        tk.Label(fr, text=cap(text) if STYLE["caps"] else text, bg=PNL, fg=TXT, font=(self.f_disp, 18, "bold"), anchor="w").pack(fill="x")
        self.se_pos[key] = fr
        return fr

    def se_row(self, parent, title, desc="", build=None, stack=False):
        """A row: title + a line under it at the left, the control at the right (on a narrow window: under the text)."""
        row = tk.Frame(parent, bg=PNL)
        row.pack(fill="x", pady=7)
        left = tk.Frame(row, bg=PNL)
        tk.Label(left, text=title, bg=PNL, fg=TXT, font=self.f_ui_b, anchor="w", justify="left").pack(fill="x")
        dl = None
        if desc:
            dl = tk.Label(left, text=desc, bg=PNL, fg=DIM, font=self.f_small, anchor="w", justify="left")
            dl.pack(fill="x", pady=(2, 0))
        right = tk.Frame(row, bg=PNL)
        if build:
            build(right)
        st = {"mode": None}

        def reflow(e):
            narrow = stack or e.width < 560
            mode = "n" if narrow else "w"
            if dl is not None:
                dl.configure(wraplength=max(160, e.width - (24 if narrow else 330)))
            if mode == st["mode"]:
                return
            st["mode"] = mode
            left.grid_forget()
            right.grid_forget()
            if narrow:
                left.grid(row=0, column=0, sticky="we")
                right.grid(row=1, column=0, sticky="w", pady=(8, 0))
                row.columnconfigure(0, weight=1)
                row.columnconfigure(1, weight=0)
            else:
                left.grid(row=0, column=0, sticky="we")
                right.grid(row=0, column=1, sticky="e", padx=(20, 0))
                row.columnconfigure(0, weight=1)
                row.columnconfigure(1, weight=0)
        row.bind("<Configure>", reflow)
        return row

    def se_switch_row(self, parent, title, desc, getter, setter):
        return self.se_row(parent, title, desc, lambda r: self.se_switch(r, getter, setter).pack())

    def se_choice_row(self, parent, title, desc, options, getter, setter, cols=None, stack=False):
        return self.se_row(parent, title, desc, lambda r: self.se_choice(r, options, getter, setter, cols).pack(), stack=stack)

    def se_button_row(self, parent, title, desc, buttons):
        def build(r):
            for text, cmd, danger in buttons:
                self.se_button(r, text, cmd, danger).pack(side="left", padx=(0, 6))
        return self.se_row(parent, title, desc, build)

    # ------------------------------------------------------------------ the page
    def se_build(self, parent):
        fr = tk.Frame(parent, bg=PNL)
        self.se_frame = fr
        self.se_pos, self.se_jobs = {}, []
        return fr

    def se_show(self):
        """Every time the page opens it is built again, so that it shows what is true now (a folder added, a look switched, a language changed)."""
        fr = self.se_frame
        top = 0.0
        if getattr(self, "se_cv", None) is not None:
            try:
                top = self.se_cv.canvasy(0)
            except tk.TclError:
                top = 0.0
        for w in list(fr.winfo_children()):
            w.destroy()
        self.se_pos = {}
        T = self.T
        head = tk.Frame(fr, bg=PNL)
        head.pack(side="top", fill="x", padx=24, pady=(16, 6))
        tk.Label(head, text=T("settings"), bg=PNL, fg=TXT, font=(self.f_disp, 24, "bold"), anchor="w").pack(fill="x")
        chips = tk.Frame(fr, bg=PNL)
        chips.pack(side="top", fill="x", padx=24, pady=(4, 0))
        names = dict(display=_t("Display"), playback=_t("Playback"), library=_t("Library"), lyrics=_t("Lyrics & media"), language=T("lang"), tools=_t("Tools"), data=_t("Data"), about=_t("About"))
        tabs = []
        for i, key in enumerate(SECTIONS):
            if STYLE["chip"] == "flat":
                b = tk.Label(chips, text=names[key], bg=PNL2, fg=TXT, font=self.f_small, padx=12, pady=4, cursor="hand2")
            else:
                b = ShapeLabel(chips, text=names[key], bg=PNL2, fg=TXT, font=self.f_small, padx=int(12 * STYLE["pad"]), pady=int(round(4 * STYLE["pad"])), cursor="hand2", shape=STYLE["chip"], pbg=PNL)
            tabs.append(b)
            b.bind("<Button-1>", lambda e, k=key: self.se_jump(k))
        self.se_wrap(chips, tabs)
        area = tk.Frame(fr, bg=PNL)
        area.pack(side="top", fill="both", expand=True, pady=(8, 0))
        cv = tk.Canvas(area, bg=PNL, highlightthickness=0)
        sb = tk.Scrollbar(area, command=cv.yview, bg=PNL2, troughcolor=PNL, bd=0, highlightthickness=0, width=10, activebackground=BRN)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        self.se_cv = cv
        col = tk.Frame(cv, bg=PNL)
        win = cv.create_window(0, 0, window=col, anchor="n")

        def place(e=None):
            w = max(260, int(cv.winfo_width()))
            cw = min(MAX_W, w - 48)
            cv.itemconfigure(win, width=cw)
            cv.coords(win, w / 2.0, 0)
        cv.bind("<Configure>", place, add="+")
        col.bind("<Configure>", lambda e: cv.configure(scrollregion=(0, 0, max(1, int(cv.winfo_width())), col.winfo_reqheight() + 40)))
        try:
            self.se_fill(col)
        except Exception as e:
            log("settings page: %r" % (e,))
            tk.Label(col, text=repr(e), bg=PNL, fg=RED, font=self.f_small, anchor="w", justify="left", wraplength=480).pack(fill="x")
        self.se_wheel(fr, cv)
        place()
        self.root.after(60, lambda: cv.yview_moveto(top / float(max(1, col.winfo_reqheight() + 40))))
        sec = getattr(self, "se_sec", None)
        if sec:
            self.se_sec = None
            self.root.after(120, lambda: self.se_jump(sec))

    def se_wheel(self, widget, cv):
        def wheel(e):
            num = e.num if isinstance(getattr(e, "num", 0), int) else 0
            cv.yview_scroll((-1 if (num == 4 or (getattr(e, "delta", 0) or 0) > 0) else 1) * 3, "units")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, wheel, add="+")
        for c in widget.winfo_children():
            self.se_wheel(c, cv)

    def se_jump(self, key):
        fr, cv = self.se_pos.get(key), self.se_cv
        if fr is None:
            return
        self.root.update_idletasks()
        total = max(1, fr.master.winfo_reqheight() + 40)
        cv.yview_moveto(max(0.0, (fr.winfo_y() - 6) / float(total)))

    def se_fill(self, col):
        T = self.T
        # ---------------------------------------------------------------- Display
        self.se_heading(col, "display", _t("Display"))
        self.se_row(col, _t("Look and colours"), _t("The whole window changes at once and the choice is remembered."))
        self.se_looks(col)
        if hasattr(self, "hm_layout"):
            self.se_row(col, self.hm_t("hm_layout"), _t("How the Home page is arranged."))
            self.se_layouts(col)
        self.se_choice_row(col, _t("Sidebar"), _t("Open shows icons and names; Closed shows icons only. Every feature still works."),
                           [("open", _t("Open")), ("closed", _t("Closed"))], lambda: self.cfg["ui"].get("side", "open"), lambda v: self.se_side(v))
        for key, attr, desc in (("anim", "anim_enabled", _t("Moving pictures and effects while music plays.")), ("aura", "aura_mode", _t("A soft glow around the player that follows the music.")),
                                ("x3", "x3_vis", _t("A bigger, busier visualizer."))):
            self.se_switch_row(col, T(key), desc, lambda a=attr: getattr(E, a), lambda v, a=attr: (setattr(E, a, bool(v)), E.save_settings()))
        # ---------------------------------------------------------------- Playback
        self.se_heading(col, "playback", _t("Playback"))
        if E.AVAILABLE_ENGINES:
            self.se_choice_row(col, T("eng"), _t("The program that plays the sound."), [(i, e["name"]) for i, e in enumerate(E.AVAILABLE_ENGINES)],
                               lambda: E.ACTIVE_ENGINE_IDX, lambda v: self.set_engine(int(v)))
        self.se_switch_row(col, T("dj"), _t("When the queue ends, similar songs keep the music going."), lambda: E.auto_dj, lambda v: (setattr(E, "auto_dj", bool(v)), E.save_settings()))
        self.se_switch_row(col, T("notify"), _t("Play, pause and skip from the Android notification (Termux)."), lambda: E.notify_controls,
                           lambda v: (setattr(E, "notify_controls", bool(v)), E.save_settings()))
        if hasattr(self, "fx_open"):
            self.se_button_row(col, T("fx"), _t("Bass, treble, equalizer, voices and more for the song that plays."), [(_t("Open Sound Studio"), self.fx_open, False)])
        # ---------------------------------------------------------------- Library
        self.se_heading(col, "library", _t("Library"))
        self.se_switch_row(col, _t("Only music from Termux"), _t("Songs and lyrics of other Android apps are not scanned. Folders you add yourself are always used."),
                           lambda: E.termux_only, lambda v: (setattr(E, "termux_only", bool(v)), E.save_settings(), self.rescan()))
        self.se_switch_row(col, _t("Scan the Termux home folder"), _t("Music anywhere inside the Termux home folder is found."),
                           lambda: E.scan_home, lambda v: (setattr(E, "scan_home", bool(v)), E.save_settings(), self.rescan()))
        self.se_row(col, _t("Music folders"), _t("Extra folders that are scanned for music."), lambda r: self.se_button(r, T("add"), lambda: self.se_add_folder(), primary=True).pack())
        self.se_folders = tk.Frame(col, bg=PNL)
        self.se_folders.pack(fill="x")
        self.se_folder_rows()
        self.se_button_row(col, T("rescan"), _t("Look for new or removed songs now."), [(_t("Scan now"), self.rescan, False)])
        self.se_button_row(col, T("dl"), _t("Download a song from a link (yt-dlp)."), [(_t("Download"), self.download, False)])
        if hasattr(self, "pl_import"):
            self.se_button_row(col, T("pl_import"), _t("Make a playlist from an .m3u file."), [(_t("Import"), self.pl_import, False)])
        # ---------------------------------------------------------------- Lyrics & media
        self.se_heading(col, "lyrics", _t("Lyrics & media"))
        three = [("auto", T("auto")), ("local", T("local")), ("off", T("off"))]
        self.se_choice_row(col, T("s_art"), _t("Where cover pictures come from."), three, lambda: E.media_art, self.se_set("media_art"))
        self.se_choice_row(col, T("s_video"), _t("Where videos come from."), three, lambda: E.media_video, self.se_set("media_video"))
        self.se_choice_row(col, T("default_view"), _t("What Now Playing shows first."), [(True, T("v_video")), (False, T("v_cover"))], lambda: E.media_prefer_video,
                           lambda v: (setattr(E, "media_prefer_video", bool(v)), E.save_settings(), self.style_toolbar(), self.media_changed(), M.refresh()))
        self.se_choice_row(col, T("quality"), _t("Picture size of downloaded videos."), [(360, "360p"), (480, "480p"), (720, "720p")], lambda: E.video_quality, self.se_set("video_quality", int, False))
        self.se_choice_row(col, T("maxsize"), _t("The biggest video that is downloaded."), [(40, "40 MB"), (80, "80 MB"), (200, "200 MB")], lambda: E.video_max_mb, self.se_set("video_max_mb", int, False))
        self.se_choice_row(col, T("s_lyrics"), _t("Where the lyrics are shown."), [("both", T("both")), ("panel", T("panel")), ("caption", T("caption")), ("off", T("off"))],
                           lambda: E.media_lyrics, self.se_set("media_lyrics", str, False))
        self.se_choice_row(col, T("lyr_mode"), _t("Look for lyrics online too, or only use files and what is saved."), [("auto", T("lyr_online")), ("local", T("lyr_local"))],
                           lambda: E.lyrics_mode, lambda v: (setattr(E, "lyrics_mode", v), E.save_settings()))
        self.se_switch_row(col, T("lyr_yt_s"), _t("Use the captions of the video when no other lyrics are found."), lambda: E.lyrics_youtube, lambda v: (setattr(E, "lyrics_youtube", bool(v)), E.save_settings()))
        self.se_switch_row(col, T("lt_title"), T("lt_note"), lambda: E.lyric_translate, lambda v: self.set_lyric_translate(bool(v)))
        self.se_choice_row(col, T("limit"), _t("How much space covers and videos may use."), [(500, "500 MB"), (1500, "1.5 GB"), (5000, "5 GB")], lambda: E.media_cache_mb, self.se_set("media_cache_mb", int, False))
        self.lbl_cache = tk.Label(col, text="", bg=PNL, fg=DIM, font=self.f_small, anchor="w", wraplength=700, justify="left")
        self.lbl_cache.pack(fill="x", pady=(4, 2))
        self.update_cache_label()
        self.se_button_row(col, _t("Pictures and videos"), _t("Clean up what was downloaded."), [(T("reset_song"), self.reset_song, False), (T("refetch"), self.refetch, False), (T("reset_all"), self.reset_all, True)])
        # ---------------------------------------------------------------- Language
        self.se_heading(col, "language", T("lang"))
        self.se_choice_row(col, T("lang"), _t("The language of every page. It changes at once."), [(c, I18N.NAMES[c]) for c in I18N.CODES], lambda: E.current_lang,
                           lambda v: self.root.after(20, lambda: self.set_lang(v)), cols=3)
        # ---------------------------------------------------------------- Tools
        tools = [(k, fn) for k, fn in self.menu_hooks if k not in SKIP_TOOLS]
        self.se_heading(col, "tools", _t("Tools"))
        if tools:
            for label_key, fn in tools:
                self.se_button_row(col, T(label_key), "", [(_t("Open"), lambda f=fn: f(self), False)])
        else:
            tk.Label(col, text=_t("No more tools are installed."), bg=PNL, fg=DIM, font=self.f_ui, anchor="w").pack(fill="x", pady=8)
        # ---------------------------------------------------------------- Data
        self.se_heading(col, "data", _t("Data"))
        self.se_button_row(col, T("backup"), _t("Save favorites, folders and settings to a file."), [(T("backup"), self.backup, False), (T("restore"), self.restore, False)])
        self.se_button_row(col, T("shortcuts"), _t("Keys and the features that are loaded."), [(_t("Open"), self.open_shortcuts, False)])
        self.se_button_row(col, T("reset"), _t("Erase everything Rofpalys saved and start fresh. This cannot be undone."), [(T("reset"), self.deep_reset, True)])
        # ---------------------------------------------------------------- About
        self.se_heading(col, "about", _t("About"))
        ver = os.environ.get("ROFPALYS_VERSION", "")
        tk.Label(col, text="Rofpalys" + ((" " + ver) if ver else ""), bg=PNL, fg=TXT, font=(self.f_disp, 16, "bold"), anchor="w").pack(fill="x", pady=(8, 2))
        for line in ("Rofpalys by Anrofty", "Rofpalys was founded on November 1, 2026", "And now, Rofpalys has not been officially released to the public."):
            lb = tk.Label(col, text=line, bg=PNL, fg=DIM, font=self.f_small, anchor="w", justify="left", wraplength=340)
            lb.pack(fill="x")
            lb.bind("<Configure>", lambda e, w=lb: w.configure(wraplength=max(200, e.width - 4)))
        row = tk.Frame(col, bg=PNL)
        row.pack(fill="x", pady=(18, 40))
        self.se_button(row, T("quit"), self.quit, danger=True).pack(side="left")

    # ------------------------------------------------------------------ pieces
    def se_set(self, attr, cast=str, refresh=True):
        def f(v):
            setattr(E, attr, cast(v))
            E.save_settings()
            if refresh:
                M.refresh()
            self.media_changed()
        return f

    def se_side(self, v):
        if (v == "open") != bool(self.side_open):
            self.toggle_side()

    def se_add_folder(self):
        self.add_folder()
        self.se_folder_rows()

    def se_folder_rows(self):
        box = getattr(self, "se_folders", None)
        if box is None:
            return
        for w in list(box.winfo_children()):
            w.destroy()
        if not E.extra_folders:
            tk.Label(box, text=_t("No extra folders yet."), bg=PNL, fg=DIM, font=self.f_small, anchor="w").pack(fill="x", pady=(0, 4))
            return
        for d in list(E.extra_folders):
            row = tk.Frame(box, bg=CARD)
            row.pack(fill="x", pady=2)
            ic = tk.Canvas(row, width=34, height=34, bg=CARD, highlightthickness=0)
            ic.pack(side="left", padx=(6, 0))
            draw_icon(ic, "folder", 17, 17, 16, GOLD)
            tk.Label(row, text=self.fit(d, "ui", 520), bg=CARD, fg=TXT, font=self.f_ui, anchor="w").pack(side="left", fill="x", expand=True, padx=6)
            x = IconBtn(row, "close", lambda d=d: self.se_remove_folder(d), size=12, color=DIM, hover=RED, bg=CARD, pad=8)
            x.pack(side="right", padx=4)

    def se_remove_folder(self, d):
        if d in E.extra_folders:
            E.extra_folders.remove(d)
            E.save_settings()
            self.rescan()
        self.se_folder_rows()

    # ------------------------------------------------------------------ look cards
    def se_looks(self, col):
        if TH is None or GT is None:
            return
        box = tk.Frame(col, bg=PNL)
        box.pack(fill="x", pady=(2, 8))
        names = TH.names()
        cur = TH.current()
        lang = I18N.current()
        cw, ch = 244, 176
        cards = []
        for i, name in enumerate(names):
            cv = tk.Canvas(box, width=cw, height=ch, bg=PNL, highlightthickness=0, cursor="hand2")
            cards.append(cv)
            on = name == cur
            pal = TH.palette(name)
            draw_shape(cv, 1, 1, cw - 1, ch - 1, fill=PNL2, outline=GOLD if on else GRID, shape=STYLE["shape"], r=8, width=2 if on else 1)
            try:
                GT.preview(cv, pal, 10, 10, cw - 20, 108)
            except Exception as e:
                log("look preview: %r" % (e,))
            fam = pick_family(pal["STYLE"]["display"], self.root)
            lab = TH.label(name, lang)
            cv.create_text(14, 136, text=cap(lab) if pal["STYLE"]["caps"] else lab, fill=TXT, anchor="w", font=(fam, 12, "bold"))
            for k, key in enumerate(("BRN", "GOLD", "ACC2", "INFO", "OK")):
                cv.create_oval(14 + k * 20, 152, 28 + k * 20, 166, fill=pal[key], outline=pal["GRID"])
            if on:
                cv.create_text(cw - 12, 136, text="✓ " + _t("In use"), fill=GOLD, anchor="e", font=self.f_small)
            cv.bind("<Button-1>", lambda e, n=name: self.th_pick(n))
        self.se_flow(box, cards, cw)

    def se_wrap(self, box, widgets, gap=6):
        """Pills of different widths in a row; when the window is too narrow the last ones go to a second row (nothing is cut off)."""
        st = {"w": -1}

        def lay(_e=None):
            w = int(box.winfo_width())
            sig = (w, tuple(int(b.winfo_reqwidth()) for b in widgets))
            if w < 50 or sig == st["w"]:
                return
            st["w"] = sig
            x = y = rowh = 0
            for b in widgets:
                bw, bh = int(b.winfo_reqwidth()), int(b.winfo_reqheight())
                if x and x + bw > w:
                    x, y, rowh = 0, y + rowh + 6, 0
                b.place(x=x, y=y)
                x += bw + gap
                rowh = max(rowh, bh)
            box.configure(height=y + rowh + 4)
        box.bind("<Configure>", lay)
        box.update_idletasks()
        box.configure(height=max([int(b.winfo_reqheight()) for b in widgets] or [24]) + 4)
        box.pack_propagate(False)
        st["w"] = -1                                                        # a layout done above (before the height was set) must be done again
        for ms in (40, 250, 800):                                           # the pills know their real width only after they are drawn
            box.after(ms, lay)

    def se_flow(self, box, cards, cw):
        """Cards in a row; on a narrow window they wrap into more rows instead of running off the edge."""
        st = {"cols": 0}

        def regrid(_e=None):
            w = int(box.winfo_width())
            if w < 50:
                return
            cols = max(1, min(len(cards), (w + 12) // (cw + 12)))
            if cols == st["cols"]:
                return
            st["cols"] = cols
            for i, c in enumerate(cards):
                c.grid(row=i // cols, column=i % cols, padx=(0, 12), pady=(0, 10), sticky="w")
        box.bind("<Configure>", regrid)
        for i, c in enumerate(cards):
            c.grid(row=0, column=i, padx=(0, 12), pady=(0, 10), sticky="w")

    def se_layouts(self, col):
        box = tk.Frame(col, bg=PNL)
        box.pack(fill="x", pady=(2, 8))
        self.se_lay = {}
        cards = []
        for i, code in enumerate(("dash", "show", "list")):
            cv = tk.Canvas(box, width=204, height=132, bg=PNL, highlightthickness=0, cursor="hand2")
            cards.append(cv)
            cv.bind("<Button-1>", lambda e, c=code: self.se_pick_layout(c))
            self.se_lay[code] = cv
        self.se_flow(box, cards, 204)
        self.se_draw_layouts()

    def se_pick_layout(self, code):
        if hasattr(self, "set_layout"):
            self.set_layout(code)
            self.se_draw_layouts()

    def se_draw_layouts(self):
        """The three layout cards: a wireframe of the page in the colours and corner shapes of the look in use."""
        cur = self.hm_layout()
        r = 3 if STYLE["shape"] != "flat" else 0
        for code, cv in getattr(self, "se_lay", {}).items():
            try:
                cv.delete("all")
                on = code == cur
                draw_shape(cv, 1, 1, 203, 131, fill=PNL2, outline=GOLD if on else GRID, shape=STYLE["shape"], r=6, width=2 if on else 1)
                x0, y0 = 10, 10

                def box(a, b, c, d, fill=CARD, out=""):
                    draw_shape(cv, x0 + a, y0 + b, x0 + c, y0 + d, fill=fill, outline=out, shape=STYLE["shape"], r=r)

                def line(a, b, c, col=DIM):
                    cv.create_line(x0 + a, y0 + b, x0 + c, y0 + b, fill=col, width=2)
                if code == "dash":
                    box(0, 0, 124, 46, lerp(CARD, BLK, .4))
                    line(8, 14, 50, TXT)
                    line(8, 24, 70)
                    box(8, 32, 30, 40, GOLD)
                    box(130, 0, 184, 46)
                    for k in range(4):
                        box(k * 47, 52, k * 47 + 43, 70)
                    for k in range(3):
                        box(k * 48, 76, k * 48 + 44, 100)
                    for k in range(3):
                        cv.create_oval(x0 + 132 + k * 18, y0 + 78, x0 + 146 + k * 18, y0 + 92, fill=BRN, outline="")
                elif code == "show":
                    box(0, 0, 184, 54, lerp(CARD, BLK, .4))
                    line(10, 16, 60, TXT)
                    line(10, 28, 90)
                    box(10, 38, 38, 47, GOLD)
                    for k in range(5):
                        box(k * 38, 62, k * 38 + 34, 90)
                    box(0, 96, 56, 104)
                    box(62, 96, 118, 104)
                    box(124, 96, 180, 104)
                else:
                    for k in range(6):
                        box(0, k * 17, 184, k * 17 + 13, fill=HOVER if k == 1 else CARD)
                        cv.create_rectangle(x0 + 5, y0 + k * 17 + 4, x0 + 13, y0 + k * 17 + 9, fill=BRN, outline="")
                        line(20, k * 17 + 6, 70 + k * 10, TXT if k == 1 else DIM)
                lab = self.hm_t("hm_l_" + code)
                cv.create_text(12, 122, text=cap(lab) + ("   ✓" if on else ""), fill=GOLD if on else TXT, anchor="w", font=self.f_small)
            except Exception as e:
                log("layout card: %r" % (e,))


def build_view(app):
    return app.se_build(app.main)


def show_view(app):
    app.se_show()


def register(app):
    app.se_frame, app.se_cv, app.se_pos, app.se_sec, app.se_folders, app.se_lay = None, None, {}, None, None, {}
    app.add_view("settings", build_view, show_view)


# END-OF-FILE rofpalys_gui_settings.py
