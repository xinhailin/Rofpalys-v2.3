#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Sound Studio (sound effects, voice characters) + A-B repeat
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""Sound Studio: a window like the panel of a good audio app. Rotary knobs with a ring of lights for Bass, Treble and Gain; a five band equalizer; speed and pitch;
reverb, stereo width and 8D; the voice characters (robot, man, woman, child, monster, alien, ghost, radio, megaphone, underwater); presets on top; one switch to bypass
everything so you can hear the difference. The window stays open while the music plays (it is not modal). A knob or slider changes the number while you move it and the
song is restarted with the new sound once, when you let go. The sound itself is made by rofpalys_effects.py (ffmpeg filters in mpv / ffplay).
The toolbar button of Now Playing and Settings > Playback open it. The A-B repeat button is here too.
A feature file plugs into the window with register(app) and brings its methods in the Mixin class (see rofpalys_gui_template.py)."""
import math

from rofpalys_gui_base import *   # noqa: F401,F403

FEATURE = {"name": "effects", "title": "Sound Studio (effects, voices) + A-B repeat", "version": "2.0", "order": 20, "enabled": True}


def _t(text):
    return I18N.tr(text)


PRESET_NAMES = {"normal": "Normal", "bass": "Bass", "superbass": "Super bass", "vocal": "Vocal", "treble": "Treble", "lofi": "Lo-fi", "slowed": "Slowed + reverb",
                "nightcore": "Nightcore", "8d": "8D", "cinema": "Cinema", "club": "Club", "acoustic": "Acoustic"}
VOICE_NAMES = {"none": "Original", "robot": "Robot", "man": "Man", "woman": "Woman", "child": "Child", "monster": "Monster", "alien": "Alien", "ghost": "Ghost",
               "radio": "Radio", "megaphone": "Megaphone", "underwater": "Underwater"}
REVERB_NAMES = {"off": "Off", "light": "Light", "room": "Room", "hall": "Hall", "cave": "Cave"}
EQ_LABELS = ("60", "230", "910", "3.6k", "14k")


# ---------------------------------------------------------------------- the controls (drawn on canvases)
class Dial(tk.Canvas):
    """A rotary knob with a ring of lights. Drag up or right to turn it up, down or left to turn it down; a double click puts it back to 0."""
    N = 27

    def __init__(self, parent, label, lo, hi, get, put, fmt, done, size=124, bg=None, zero=0):
        bg = bg or PNL2
        super().__init__(parent, width=size, height=size + 24, bg=bg, highlightthickness=0, cursor="hand2")
        self.label, self.lo, self.hi, self.get, self.put, self.fmt, self.done, self.size, self.zero, self.bgc = label, lo, hi, get, put, fmt, done, size, zero, bg
        self._p = None
        self.bind("<ButtonPress-1>", self.press)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<ButtonRelease-1>", self.release)
        self.bind("<Double-Button-1>", self.reset)
        self.paint()

    def paint(self):
        self.delete("all")
        s, v = self.size, self.get()
        frac = (v - self.lo) / float(self.hi - self.lo)
        cx, cy = s / 2.0, s / 2.0 + 2
        ro, ri = s / 2.0 - 5, s / 2.0 - 17
        lit = int(round(frac * self.N))
        for i in range(self.N):
            a = math.radians(225 - 270.0 * i / (self.N - 1))
            on = i < lit or (i == 0 and v > self.lo)
            col = lerp(BRN, GOLD, i / float(self.N - 1)) if on else GRID
            self.create_line(cx + ri * math.cos(a), cy - ri * math.sin(a), cx + ro * math.cos(a), cy - ro * math.sin(a), fill=col, width=4, capstyle="round")
        rr = ri - 8
        self.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=CARD, outline=lerp(GRID, TXT, 0.25), width=1)
        if STYLE["glow"]:
            self.create_oval(cx - rr - 2, cy - rr - 2, cx + rr + 2, cy + rr + 2, outline=INFO, width=1)
        a = math.radians(225 - 270.0 * frac)
        self.create_line(cx + (rr - 14) * math.cos(a), cy - (rr - 14) * math.sin(a), cx + (rr - 3) * math.cos(a), cy - (rr - 3) * math.sin(a), fill=TXT, width=3, capstyle="round")
        self.create_text(cx, cy + 2, text=self.fmt(v), fill=TXT, font=(pick_family(STYLE["display"], self), max(9, int(s / 9)), "bold"))
        self.create_text(cx, s + 12, text=cap(self.label) if STYLE["caps"] else self.label, fill=DIM, font=(pick_family(STYLE["display"], self), 9))

    def press(self, e):
        self._p = (e.x, e.y, self.get())

    def drag(self, e):
        if not self._p:
            return
        x0, y0, v0 = self._p
        v = v0 + ((y0 - e.y) + (e.x - x0)) / 170.0 * (self.hi - self.lo)
        v = int(round(max(self.lo, min(self.hi, v))))
        if v != self.get():
            self.put(v)
            self.paint()

    def release(self, e):
        if self._p:
            self._p = None
            self.done()

    def reset(self, e=None):
        self._p = None
        self.put(self.zero)
        self.paint()
        self.done()


class Fader(tk.Canvas):
    """A slider (horizontal, or vertical for the equalizer). Click or drag; the number changes while you move, the sound when you let go."""

    def __init__(self, parent, lo, hi, get, put, fmt, done, vertical=False, length=200, thick=34, bg=None, zero=None, step=1, label=""):
        bg = bg or PNL2
        w, h = (thick + 20, length) if vertical else (length, thick)
        super().__init__(parent, width=w, height=h, bg=bg, highlightthickness=0, cursor="hand2")
        self.lo, self.hi, self.get, self.put, self.fmt, self.done, self.vertical, self.zero, self.step, self.label = lo, hi, get, put, fmt, done, vertical, zero, step, label
        self.bind("<Configure>", lambda e: self.paint())
        self.bind("<ButtonPress-1>", self.set_from)
        self.bind("<B1-Motion>", self.set_from)
        self.bind("<ButtonRelease-1>", lambda e: self.done())
        self.bind("<Double-Button-1>", self.reset)

    def pos(self):
        w, h = max(40, self.winfo_width()), max(40, self.winfo_height())
        if self.vertical:
            return w / 2.0, 14, h - 34
        return 14, h / 2.0, w - 14

    def paint(self):
        self.delete("all")
        v = self.get()
        frac = (v - self.lo) / float(self.hi - self.lo)
        a, b, c = self.pos()
        glow = STYLE["glow"]
        if self.vertical:
            x, y0, y1 = a, b, c
            self.create_line(x, y0, x, y1, fill=GRID, width=5, capstyle="round")
            ty = y1 - frac * (y1 - y0)
            zy = y1 - ((self.zero - self.lo) / float(self.hi - self.lo)) * (y1 - y0) if self.zero is not None else y1
            self.create_line(x, zy, x, ty, fill=GOLD, width=5, capstyle="round")
            if self.zero is not None:
                self.create_line(x - 9, zy, x + 9, zy, fill=DIM)
            self.create_oval(x - 9, ty - 9, x + 9, ty + 9, fill=TXT, outline=GOLD if glow else "")
            self.create_text(x, y1 + 12, text=self.fmt(v), fill=TXT, font=(pick_family(STYLE["display"], self), 9, "bold"))
            self.create_text(x, y1 + 26, text=self.label, fill=DIM, font=(pick_family(STYLE["display"], self), 8))
        else:
            y, x0, x1 = b, a, c
            self.create_line(x0, y, x1, y, fill=GRID, width=5, capstyle="round")
            tx = x0 + frac * (x1 - x0)
            zx = x0 + ((self.zero - self.lo) / float(self.hi - self.lo)) * (x1 - x0) if self.zero is not None else x0
            self.create_line(zx, y, tx, y, fill=GOLD, width=5, capstyle="round")
            if self.zero is not None:
                self.create_line(zx, y - 8, zx, y + 8, fill=DIM)
            self.create_oval(tx - 9, y - 9, tx + 9, y + 9, fill=TXT, outline=GOLD if glow else "")

    def set_from(self, e):
        a, b, c = self.pos()
        if self.vertical:
            frac = 1.0 - (e.y - b) / float(max(1, c - b))
        else:
            frac = (e.x - a) / float(max(1, c - a))
        frac = max(0.0, min(1.0, frac))
        v = self.lo + frac * (self.hi - self.lo)
        v = round(v / self.step) * self.step
        v = max(self.lo, min(self.hi, v))
        if abs(v - self.get()) > 1e-9:
            self.put(v)
            self.paint()

    def reset(self, e=None):
        self.put(self.zero if self.zero is not None else self.get())
        self.paint()
        self.done()


def voice_glyph(cv, kind, cx, cy, col, w=2):
    """A small line drawing for each voice character (no emoji: they do not draw the same everywhere)."""
    def oval(x1, y1, x2, y2, fill=""):
        cv.create_oval(cx + x1, cy + y1, cx + x2, cy + y2, outline=col, width=w, fill=fill)

    def line(*pts):
        cv.create_line([c + (cx if i % 2 == 0 else cy) for p in pts for i, c in enumerate(p)], fill=col, width=w, capstyle="round", joinstyle="round")

    def poly(*pts):
        cv.create_polygon([c + (cx if i % 2 == 0 else cy) for p in pts for i, c in enumerate(p)], outline=col, width=w, fill="", joinstyle="round")

    def arc(x1, y1, x2, y2, start, extent):
        cv.create_arc(cx + x1, cy + y1, cx + x2, cy + y2, start=start, extent=extent, style="arc", outline=col, width=w)
    if kind == "none":
        cv.create_rectangle(cx - 4, cy - 12, cx + 4, cy + 3, outline=col, width=w)
        arc(-9, -6, 9, 10, 180, 180)
        line((0, 10), (0, 14))
        line((-5, 14), (5, 14))
    elif kind == "robot":
        cv.create_rectangle(cx - 10, cy - 7, cx + 10, cy + 9, outline=col, width=w)
        oval(-6, -2, -2, 2, col)
        oval(2, -2, 6, 2, col)
        line((-5, 5), (5, 5))
        line((0, -7), (0, -12))
        oval(-2, -15, 2, -11)
    elif kind in ("man", "woman", "child"):
        r = 5 if kind == "child" else 6.5
        hy = -3 if kind != "child" else 0
        oval(-r, hy - r, r, hy + r)
        arc(-11 if kind != "child" else -8, hy + r + 2, 11 if kind != "child" else 8, hy + r + 20, 0, 180)
        if kind == "man":
            arc(-r - 1, hy - r - 1, r + 1, hy + r - 3, 0, 180)
        elif kind == "woman":
            line((-r - 1, hy - 1), (-r - 3, hy + 11))
            line((r + 1, hy - 1), (r + 3, hy + 11))
            arc(-r - 1, hy - r - 2, r + 1, hy + r - 2, 0, 180)
        else:
            oval(-r - 4, hy - 2, -r - 1, hy + 2)
            oval(r + 1, hy - 2, r + 4, hy + 2)
    elif kind == "monster":
        oval(-10, -8, 10, 11)
        poly((-9, -5), (-12, -13), (-4, -8))
        poly((9, -5), (12, -13), (4, -8))
        oval(-6, -3, -2, 1, col)
        oval(2, -3, 6, 1, col)
        line((-6, 6), (-3, 4), (0, 6), (3, 4), (6, 6))
    elif kind == "alien":
        oval(-8, -12, 8, 10)
        cv.create_polygon([cx - 6, cy - 3, cx - 1, cy - 1, cx - 3, cy + 3], fill=col, outline=col)
        cv.create_polygon([cx + 6, cy - 3, cx + 1, cy - 1, cx + 3, cy + 3], fill=col, outline=col)
        line((-2, 6), (2, 6))
    elif kind == "ghost":
        arc(-9, -13, 9, 5, 0, 180)
        line((-9, -4), (-9, 12), (-6, 9), (-3, 12), (0, 9), (3, 12), (6, 9), (9, 12), (9, -4))
        oval(-5, -5, -2, -2, col)
        oval(2, -5, 5, -2, col)
    elif kind == "radio":
        cv.create_rectangle(cx - 11, cy - 5, cx + 11, cy + 10, outline=col, width=w)
        line((5, -5), (9, -12))
        oval(-8, -1, 0, 7)
        line((3, 1), (8, 1))
        line((3, 5), (8, 5))
    elif kind == "megaphone":
        poly((-11, -3), (-4, -3), (9, -10), (9, 10), (-4, 3), (-11, 3))
        line((-6, 3), (-5, 11), (-1, 11))
    elif kind == "underwater":
        for k, yy in enumerate((-8, 0, 8)):
            line((-11, yy), (-7, yy - 3), (-3, yy), (1, yy - 3), (5, yy), (9, yy - 3), (12, yy))


class Mixin:
    # ------------------------------------------------------------------ opening and closing
    def open_effects(self):
        self.fx_open()

    def fx_open(self):
        if self.fx_win is not None:
            try:
                self.fx_win.lift()
                return
            except Exception:
                self.fx_win = None
        top, body = self.modal(_t("Sound Studio"), 780)
        self.fx_win = top
        top.protocol("WM_DELETE_WINDOW", self.close_effects)
        top.bind("<Escape>", lambda e: self.close_effects())
        self._fx_job, self._fx_vars = None, {}
        body.configure(padx=0, pady=0)
        # header: title, bypass switch, reset, close
        head = tk.Frame(body, bg=PNL2)
        head.pack(side="top", fill="x", padx=22, pady=(16, 6))
        titles = tk.Frame(head, bg=PNL2)
        titles.pack(side="left", fill="x", expand=True)
        tk.Label(titles, text=_t("Sound Studio"), bg=PNL2, fg=TXT, font=self.f_head, anchor="w").pack(fill="x")
        self.fx_status = tk.Label(titles, text="", bg=PNL2, fg=DIM, font=self.f_small, anchor="w")
        self.fx_status.pack(fill="x")
        x = IconBtn(head, "close", self.close_effects, size=16, color=DIM, hover=TXT, bg=PNL2, pad=8)
        x.pack(side="right")
        self.fx_sw = tk.Frame(head, bg=PNL2)
        self.fx_sw.pack(side="right", padx=(0, 14))
        area = tk.Frame(body, bg=PNL2)
        area.pack(side="top", fill="both", expand=True)
        cv = tk.Canvas(area, bg=PNL2, highlightthickness=0)
        sb = tk.Scrollbar(area, command=cv.yview, bg=PNL2, troughcolor=PNL2, bd=0, highlightthickness=0, width=10, activebackground=BRN)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        self.fx_cv = cv
        inner = tk.Frame(cv, bg=PNL2)
        win = cv.create_window(0, 0, window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=(0, 0, e.width, e.height + 12)))
        self.fx_inner = inner
        rw = self.root.winfo_width()
        self.fx_wide = min(780, rw - 24) >= 640
        self.fx_build()
        self.modal_show(top, height=max(380, self.root.winfo_height() - 40), grab=False)

    def close_effects(self):
        job = getattr(self, "_fx_job", None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
            self._fx_job = None
            E.fx_commit()
        try:
            if self.fx_win is not None:
                self.fx_win.destroy()
        except Exception:
            pass
        self.fx_win = None
        self.style_toolbar()

    # ------------------------------------------------------------------ changing the sound
    def fx_dirty(self):
        """The sound is restarted once, 0.45 s after the last change."""
        self.fx_note()
        self.style_toolbar()
        if self._fx_job:
            self.root.after_cancel(self._fx_job)
        self._fx_job = self.root.after(450, self.fx_flush)

    def fx_flush(self):
        self._fx_job = None
        E.fx_commit()
        self.fx_note()

    def fx_set(self, **kw):
        FX.update(**kw)

    def fx_now(self, **kw):
        """A choice that applies at once (a chip, a switch): set, restart, and draw the window again."""
        if "enabled" not in kw:
            kw["enabled"] = True
        E.fx_apply(**kw)
        self.style_toolbar()
        self.fx_build()

    def fx_note(self):
        try:
            if not FX.enabled:
                txt = _t("Bypassed: you hear the song as recorded")
            elif not FX.is_active():
                txt = _t("Original sound")
            else:
                txt = "%s  •  %s" % (_t("Now playing with"), FX.label())
            self.fx_status.configure(text=txt)
        except Exception:
            pass

    # ------------------------------------------------------------------ the window
    def fx_section(self, parent, title, pad_top=14):
        fr = tk.Frame(parent, bg=PNL2)
        fr.pack(fill="x", padx=22, pady=(pad_top, 0))
        tk.Frame(fr, bg=GRID, height=1).pack(fill="x", pady=(0, 10))
        tk.Label(fr, text=cap(title) if STYLE["caps"] else title, bg=PNL2, fg=DIM, font=(self.f_disp, 10, "bold"), anchor="w").pack(fill="x", pady=(0, 6))
        return fr

    def fx_chips(self, parent, items, current, cmd, cols):
        box = tk.Frame(parent, bg=PNL2)
        box.pack(fill="x")
        for i, (val, text) in enumerate(items):
            on = val == current
            if STYLE["chip"] == "flat":
                b = tk.Label(box, text=text, bg=GOLD if on else CARD, fg=BLK if on else TXT, font=self.f_ui, padx=12, pady=6, cursor="hand2")
            else:
                b = ShapeLabel(box, text=text, bg=GOLD if on else CARD, fg=BLK if on else TXT, font=self.f_ui, padx=int(12 * STYLE["pad"]), pady=int(round(6 * STYLE["pad"])),
                               cursor="hand2", shape=STYLE["chip"], pbg=PNL2)
            b.grid(row=i // cols, column=i % cols, padx=(0, 6), pady=(0, 6), sticky="we")
            b.bind("<Button-1>", lambda e, v=val: cmd(v))
        for c in range(cols):
            box.grid_columnconfigure(c, weight=1, uniform="chips")
        return box

    def fx_switch(self, parent, text, key, desc=""):
        row = tk.Frame(parent, bg=PNL2)
        row.pack(fill="x", pady=4)
        left = tk.Frame(row, bg=PNL2)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=text, bg=PNL2, fg=TXT, font=self.f_ui_b, anchor="w").pack(fill="x")
        if desc:
            tk.Label(left, text=desc, bg=PNL2, fg=DIM, font=self.f_small, anchor="w", justify="left", wraplength=420).pack(fill="x")
        sw = self.se_switch(row, lambda: getattr(FX, key), lambda v: self.fx_now(**{key: bool(v)}))
        sw.configure(bg=PNL2)
        sw.pack(side="right")

    def fx_build(self):
        inner = self.fx_inner
        top = self.fx_cv.canvasy(0) if self.fx_cv.winfo_exists() else 0
        for w in list(inner.winfo_children()):
            w.destroy()
        for w in list(self.fx_sw.winfo_children()):
            w.destroy()
        T = self.T
        wide = self.fx_wide
        done = self.fx_dirty
        # the bypass switch: ON = you hear the effects
        tk.Label(self.fx_sw, text=_t("Effects") + ("  ON" if FX.enabled else "  OFF"), bg=PNL2, fg=GOLD if FX.enabled else DIM, font=self.f_ui_b).pack(side="left", padx=(0, 8))
        sw = self.se_switch(self.fx_sw, lambda: FX.enabled, lambda v: self.fx_now(enabled=bool(v)))
        sw.configure(bg=PNL2)
        sw.pack(side="left")
        self.fx_note()
        if not FX.supported(E.engine_name()):
            tk.Label(inner, text=T("fx_note") % E.engine_name(), bg=PNL2, fg=RED, font=self.f_small, anchor="w", justify="left", wraplength=640).pack(fill="x", padx=22, pady=(6, 0))
        # ---- presets
        s = self.fx_section(inner, _t("Presets"), 4)
        self.fx_chips(s, [(k, _t(PRESET_NAMES[k])) for k in FX.PRESETS], FX.preset if (FX.preset != "normal" or not FX.is_active()) else "", lambda v: self.fx_now(preset=v), 4 if wide else 3)
        # ---- tone: three knobs, and the equalizer
        s = self.fx_section(inner, _t("Tone"))
        row = tk.Frame(s, bg=PNL2)
        row.pack(fill="x")
        size = 128 if wide else 100
        for key, label, lo, hi in (("bass", _t("Bass"), FX.LIMITS["bass"][0], FX.LIMITS["bass"][1]), ("treble", _t("Treble"), FX.LIMITS["treble"][0], FX.LIMITS["treble"][1]),
                                   ("gain", _t("Gain"), FX.LIMITS["gain"][0], FX.LIMITS["gain"][1])):
            d = Dial(row, label, lo, hi, lambda k=key: getattr(FX, k), lambda v, k=key: self.fx_set(**{k: v}), lambda v: "%+d dB" % v if v else "0 dB", done, size=size)
            d.pack(side="left", padx=(0, 10 if wide else 4))
        if wide:
            eqf = tk.Frame(row, bg=PNL2)
            eqf.pack(side="right")
            self.fx_eq(eqf, 150, done)
        else:
            e2 = self.fx_section(inner, _t("Equalizer"), 8)
            self.fx_eq(e2, 150, done)
        # ---- speed and pitch
        s = self.fx_section(inner, _t("Speed and pitch"))
        self.fx_slider(s, _t("Speed"), FX.LIMITS["speed"][0], FX.LIMITS["speed"][1], lambda: FX.speed, lambda v: self.fx_set(speed=v), lambda v: "%.2fx" % v, done, zero=1.0, step=0.05)
        self.fx_slider(s, _t("Pitch"), FX.LIMITS["pitch"][0], FX.LIMITS["pitch"][1], lambda: FX.pitch, lambda v: self.fx_set(pitch=v), lambda v: ("%+d st" % v) if v else "0 st", done, zero=0)
        self.fx_switch(s, _t("Tape mode"), "tape", _t("The pitch follows the speed, like a record that is slowed down or sped up (slowed + reverb, nightcore)."))
        # ---- space
        s = self.fx_section(inner, _t("Space"))
        tk.Label(s, text=_t("Reverb"), bg=PNL2, fg=TXT, font=self.f_ui_b, anchor="w").pack(fill="x", pady=(0, 4))
        self.fx_chips(s, [(k, _t(REVERB_NAMES[k])) for k in FX.REVERBS], FX.reverb, lambda v: self.fx_now(reverb=v), 5)
        self.fx_slider(s, _t("Reverb amount"), FX.LIMITS["reverb_mix"][0], FX.LIMITS["reverb_mix"][1], lambda: FX.reverb_mix, lambda v: self.fx_set(reverb_mix=v), lambda v: "%d%%" % v, done, step=1)
        self.fx_slider(s, _t("Stereo width"), 0, 200, lambda: FX.width, lambda v: self.fx_set(width=v), lambda v: ("%d%%" % v) if v != 0 else _t("Mono"), done, zero=100, step=5)
        self.fx_switch(s, _t("8D audio"), "eight_d", _t("The sound slowly walks around your head. Best with headphones."))
        # ---- voices
        s = self.fx_section(inner, _t("Voice"))
        self.fx_voices(s, 4 if wide else 3)
        # ---- extras
        s = self.fx_section(inner, _t("Extras"))
        self.fx_switch(s, _t("Lo-fi"), "lofi", _t("Warm, a little dusty: less highs and lows."))
        self.fx_switch(s, _t("Night mode"), "night", _t("Quiet parts louder, loud parts softer: good at low volume."))
        self.fx_switch(s, _t("Even out the volume"), "normalize", _t("Keeps every song at about the same loudness."))
        foot = tk.Frame(inner, bg=PNL2)
        foot.pack(fill="x", padx=22, pady=(18, 26))
        self.btn(foot, _t("Reset all"), lambda: (E.fx_reset(), self.style_toolbar(), self.fx_build()), bg=CARD, fg=RED, padx=18, pady=7).pack(side="left")
        self.btn(foot, T("close"), self.close_effects, bg=GOLD, fg=BLK, padx=22, pady=7, font=self.f_ui_b).pack(side="right")
        self.fx_wheel(inner)
        self.root.after(30, lambda: self.fx_cv.yview_moveto(top / float(max(1, inner.winfo_reqheight() + 12))))

    def fx_slider(self, parent, label, lo, hi, get, put, fmt, done, zero=None, step=1):
        row = tk.Frame(parent, bg=PNL2)
        row.pack(fill="x", pady=(2, 2))
        top = tk.Frame(row, bg=PNL2)
        top.pack(fill="x")
        tk.Label(top, text=label, bg=PNL2, fg=TXT, font=self.f_ui_b, anchor="w").pack(side="left")
        val = tk.Label(top, text=fmt(get()), bg=PNL2, fg=GOLD, font=self.f_ui_b)
        val.pack(side="right")

        def put2(v):
            put(v)
            val.configure(text=fmt(v))
        f = Fader(row, lo, hi, get, put2, fmt, done, length=300, zero=zero, step=step)
        f.pack(fill="x", expand=True)
        f.bind("<Configure>", lambda e, f=f: f.paint())

    def fx_eq(self, parent, height, done):
        box = tk.Frame(parent, bg=PNL2)
        box.pack()
        for i, hz in enumerate(FX.EQ_BANDS):
            def put(v, i=i):
                e = list(FX.eq)
                e[i] = int(round(v))
                self.fx_set(eq=e)
            f = Fader(box, -12, 12, lambda i=i: FX.eq[i], put, lambda v: ("%+d" % v) if v else "0", done, vertical=True, length=height, zero=0, label=EQ_LABELS[i], step=1)
            f.pack(side="left", padx=2)
            f.bind("<Configure>", lambda e, f=f: f.paint())

    def fx_voices(self, parent, cols):
        box = tk.Frame(parent, bg=PNL2)
        box.pack(fill="x")
        names = list(FX.VOICES)
        for i, v in enumerate(names):
            on = FX.voice == v
            cv = tk.Canvas(box, width=150, height=84, bg=PNL2, highlightthickness=0, cursor="hand2")
            cv.grid(row=i // cols, column=i % cols, padx=(0, 8), pady=(0, 8), sticky="we")
            box.grid_columnconfigure(i % cols, weight=1, uniform="voices")
            cv.bind("<Configure>", lambda e, cv=cv, v=v, on=on: self.fx_voice_card(cv, v, on))
            cv.bind("<Button-1>", lambda e, v=v: self.fx_now(voice=v))

    def fx_voice_card(self, cv, v, on):
        cv.delete("all")
        w = max(100, cv.winfo_width())
        draw_shape(cv, 1, 1, w - 1, 83, fill=lerp(CARD, GOLD, 0.16) if on else CARD, outline=GOLD if on else GRID, shape=STYLE["shape"], r=8, width=2 if on else 1)
        voice_glyph(cv, v, w / 2.0, 32, GOLD if on else TXT)
        cv.create_text(w / 2.0, 66, text=_t(VOICE_NAMES[v]), fill=GOLD if on else TXT, font=self.f_ui_b)

    def fx_wheel(self, widget):
        """The mouse wheel scrolls the window; dragging on empty space scrolls too (a finger on a phone). The knobs and faders keep their own drag."""
        cv = self.fx_cv

        def wheel(e):
            num = e.num if isinstance(getattr(e, "num", 0), int) else 0
            cv.yview_scroll((-1 if (num == 4 or (getattr(e, "delta", 0) or 0) > 0) else 1) * 3, "units")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, wheel, add="+")
        if isinstance(widget, (tk.Frame, tk.Label)) and not isinstance(widget, ShapeLabel):
            widget.bind("<ButtonPress-1>", lambda e: cv.scan_mark(0, e.y_root), add="+")
            widget.bind("<B1-Motion>", lambda e: cv.scan_dragto(0, e.y_root, gain=1), add="+")
        for c in widget.winfo_children():
            self.fx_wheel(c)

    def ab_click(self):
        E.ab_mark()
        self.style_toolbar()


def build_fx(app, bar):
    app.b_fx = IconBtn(bar, "equalizer", app.fx_open, size=20, bg=PNL, pad=7)
    app.b_fx.pack(side="right")
    return [app.b_fx.cv]


def build_ab(app, bar):
    app.b_ab = IconBtn(bar, "ab", app.ab_click, size=20, bg=PNL, pad=7)
    app.b_ab.pack(side="right")
    return [app.b_ab.cv]


def style(app):
    app.b_fx.set(color=GOLD if FX.is_active() else DIM)
    app.b_ab.set(color=GOLD if E.ab_a is not None else DIM)


def register(app):
    app.fx_win, app._fx_job, app.fx_cv, app.fx_inner, app.fx_sw, app.fx_status, app.fx_wide = None, None, None, None, None, None, True
    app.add_toolbar(20, build_fx, style)
    app.add_toolbar(30, build_ab)


# END-OF-FILE rofpalys_gui_effects.py
