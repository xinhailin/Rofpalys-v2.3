#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: dialogs and sheets in the look in use (a name box, a menu that rises from the bottom / opens at the pointer)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""Small building blocks for the other feature files; they draw nothing of their own on the main window.
  self.modal(title, width)                          a dialog window over the main window; returns (top, body). Call self.modal_show(top) when the body is filled.
  self.ask_name(title, initial, ok_text, hint)      "Name your playlist": a big text box, Cancel / Create. Returns the text, or None when cancelled.
  self.sheet_open(items, x_root, y_root, title)     a menu of rows (icon + text). items = [(icon, text, command)]. On a narrow window it rises from the bottom edge
                                                    over the full width (as on a phone); on a wide window it opens at the pointer.
A feature file plugs into the window with register(app) and brings its methods in the Mixin class (see rofpalys_gui_template.py)."""
from rofpalys_gui_base import *   # noqa: F401,F403

FEATURE = {"name": "dialogs", "title": "Dialogs and sheets (name box, menus that rise from the bottom)", "version": "1.0", "order": 12, "enabled": True}


def _t(text):
    return I18N.tr(text)


class Mixin:
    # ------------------------------------------------------------------ a dialog window
    def modal(self, title, width=420):
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title(title)
        top.configure(bg=BRN2 if STYLE["glow"] else GRID)
        try:
            top.transient(self.root)
        except tk.TclError:
            pass
        body = tk.Frame(top, bg=PNL2, padx=22, pady=18)
        body.pack(fill="both", expand=True, padx=1, pady=1)
        top._want_w = width
        top.bind("<Escape>", lambda e: top.destroy())
        return top, body

    def modal_show(self, top, height=None, focus=None, grab=True):
        """Centres the dialog on the main window and makes it the one that takes the keys and clicks (grab=False: a window that stays beside the player)."""
        top.update_idletasks()
        rw, rh = max(300, self.root.winfo_width()), max(300, self.root.winfo_height())
        w = min(top._want_w, max(280, rw - 24))
        h = height if height else top.winfo_reqheight()
        h = min(h, max(240, rh - 24))
        x = self.root.winfo_rootx() + (rw - w) // 2
        y = self.root.winfo_rooty() + max(8, (rh - h) // 3)
        top.geometry("%dx%d+%d+%d" % (w, h, x, y))
        top.deiconify()
        top.lift()
        if grab:
            try:
                top.grab_set()
            except tk.TclError:
                pass
        try:
            (focus or top).focus_force()
        except tk.TclError:
            pass

    def modal_title(self, body, text, sub=""):
        tk.Label(body, text=text, bg=PNL2, fg=TXT, font=self.f_head, anchor="w").pack(fill="x")
        if sub:
            tk.Label(body, text=sub, bg=PNL2, fg=DIM, font=self.f_small, anchor="w", justify="left", wraplength=360).pack(fill="x", pady=(2, 0))

    def modal_entry(self, body, initial="", hint="", big=False, justify="left"):
        """A text box with a line under it (the line turns to the accent colour while you type). Returns (entry, variable)."""
        v = tk.StringVar(value=initial)
        box = tk.Frame(body, bg=PNL2)
        box.pack(fill="x", pady=(14, 4))
        e = tk.Entry(box, textvariable=v, bg=CARD, fg=TXT, insertbackground=GOLD, relief="flat", bd=0, highlightthickness=0, justify=justify,
                     font=self.f_title if big else self.f_ui, selectbackground=BRN, selectforeground=BLK)
        e.pack(fill="x", ipady=9 if big else 7, padx=0)
        line = tk.Frame(box, bg=GRID, height=2)
        line.pack(fill="x")
        e.bind("<FocusIn>", lambda ev: line.configure(bg=GOLD))
        e.bind("<FocusOut>", lambda ev: line.configure(bg=GRID))
        if hint:
            tk.Label(box, text=hint, bg=PNL2, fg=DIM, font=self.f_small, anchor="w").pack(fill="x", pady=(4, 0))
        return e, v

    def modal_buttons(self, body, buttons):
        """buttons = [(text, command, primary)] shown at the right, the last one is the main action."""
        row = tk.Frame(body, bg=PNL2)
        row.pack(fill="x", pady=(16, 0))
        for text, cmd, primary in reversed(buttons):
            b = self.btn(row, text, cmd, bg=GOLD if primary else PNL2, fg=BLK if primary else TXT, padx=22, pady=7, font=self.f_ui_b)
            b.pack(side="right", padx=(8, 0))
        return row

    # ------------------------------------------------------------------ "Name your playlist"
    def ask_name(self, title, initial="", ok_text="Create", hint=""):
        top, body = self.modal(title, 400)
        self.modal_title(body, title)
        e, v = self.modal_entry(body, initial, hint, big=True, justify="center")
        res = {"v": None}

        def done(_e=None):
            res["v"] = v.get().strip()
            top.destroy()
        e.bind("<Return>", done)
        self.modal_buttons(body, [(_t("Cancel"), top.destroy, False), (_t(ok_text), done, True)])
        self.modal_show(top, focus=e)
        e.focus_set()
        e.select_range(0, "end")
        e.icursor("end")
        try:
            self.root.wait_window(top)
        except tk.TclError:
            pass
        return res["v"] if res["v"] else None

    # ------------------------------------------------------------------ the sheet (a menu with icons)
    def sheet_close(self):
        top = getattr(self, "_sheet", None)
        self._sheet = None
        if top is not None:
            try:
                top.grab_release()
            except tk.TclError:
                pass
            try:
                top.destroy()
            except tk.TclError:
                pass

    def sheet_open(self, items, x_root=None, y_root=None, title=None):
        self.sheet_close()
        root = self.root
        rw, rh = max(300, root.winfo_width()), max(300, root.winfo_height())
        narrow = rw < 700
        top = tk.Toplevel(root)
        top.withdraw()
        top.overrideredirect(True)
        top.configure(bg=BRN2 if STYLE["glow"] else GRID)
        box = tk.Frame(top, bg=PNL2)
        box.pack(fill="both", expand=True, padx=1, pady=1)
        self._sheet = top
        if narrow:                                                           # the handle of a sheet that rises from the bottom
            hd = tk.Frame(box, bg=PNL2, height=18)
            hd.pack(fill="x")
            tk.Frame(hd, bg=DIM, width=38, height=4).place(relx=0.5, rely=0.5, anchor="center")
        if title:
            tk.Label(box, text=title, bg=PNL2, fg=TXT, font=self.f_ui_b, anchor="w", padx=18, pady=10).pack(fill="x")
        rows = []
        pad = 12 if narrow else 8
        for icon, text, cmd in items:
            row = tk.Frame(box, bg=PNL2, cursor="hand2")
            row.pack(fill="x")
            ic = tk.Canvas(row, width=44, height=34 + pad, bg=PNL2, highlightthickness=0, cursor="hand2")
            ic.pack(side="left", padx=(10, 0))
            draw_icon(ic, icon, 22, (34 + pad) / 2.0, 18, TXT)
            lb = tk.Label(row, text=text, bg=PNL2, fg=TXT, font=self.f_ui, anchor="w", cursor="hand2")
            lb.pack(side="left", fill="x", expand=True, padx=(4, 18))
            parts = (row, ic, lb)
            rows.append(parts)

            def paint(on, parts=parts):
                for w in parts:
                    try:
                        w.configure(bg=HOVER if on else PNL2)
                    except tk.TclError:
                        pass
            for w in parts:
                w.bind("<Enter>", lambda e, p=paint: p(True))
                w.bind("<Leave>", lambda e, p=paint: p(False))
                w.bind("<ButtonRelease-1>", lambda e, c=cmd: self._sheet_pick(c))
        tk.Frame(box, bg=PNL2, height=8 if narrow else 4).pack(fill="x")
        top.update_idletasks()
        w = rw if narrow else max(250, min(340, top.winfo_reqwidth()))
        h = min(top.winfo_reqheight(), rh - 20)
        if narrow:
            x, y = root.winfo_rootx(), root.winfo_rooty() + rh - h
        else:
            px = x_root if x_root is not None else root.winfo_pointerx()
            py = y_root if y_root is not None else root.winfo_pointery()
            x = max(root.winfo_rootx() + 4, min(px, root.winfo_rootx() + rw - w - 4))
            y = max(root.winfo_rooty() + 4, min(py, root.winfo_rooty() + rh - h - 4))
        top.geometry("%dx%d+%d+%d" % (w, h, x, y))
        top.deiconify()
        top.lift()
        try:
            top.grab_set()
            top.focus_force()
        except tk.TclError:
            pass
        top.bind("<Escape>", lambda e: self.sheet_close())

        def outside(e):
            if not (x <= e.x_root <= x + w and y <= e.y_root <= y + h):
                self.sheet_close()
        top.bind("<ButtonPress-1>", outside)

    def _sheet_pick(self, cmd):
        self.sheet_close()
        self.root.after(30, cmd)


def register(app):
    app._sheet = None


# END-OF-FILE rofpalys_gui_dialogs.py
