#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Daily goal, goal streak and badges
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""A new tab "Goals" (Indonesian: "Target") in the Statistics page.

  Daily goal    choose how many minutes of music you want per day (15 / 30 / 45 / 60 / 90 / 120). A ring shows today, a message pops up the moment you reach it.
  Goal streak   how many days in a row you reached the goal (a day that is still open does not break the streak), and your best.
  Five weeks    a small calendar: every day is filled by how close you came to the goal.
  Badges        19 of them, from "first song" to "30 days in a row" and "6 hours in one day". Each shows how far you are; a badge that is won stays won and
                remembers its date. The first time, the badges your history has already earned are unlocked in one go (one message, not nineteen).

The goal and the badges are kept in <config folder>/goals.json. Every number comes from rofpalys_analytics.py (the history of your listening) - listening time is what you
actually heard, not how long the app was open. stats_from() and the helpers below have no window in them."""
import datetime as _dt
import json
import os
import tempfile
import time

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    import rofpalys_insight as IN
    import rofpalys_analytics_text as X
    import rofpalys_gui_stats as GS
    import rofpalys_gui_stats_charts as CH
except Exception:
    IN = X = GS = CH = None
try:
    import rofpalys_analytics as AN
except Exception:
    AN = None

FEATURE = {"name": "goals", "title": "Daily goal, goal streak and badges", "version": "1.0", "order": 50, "enabled": True}
M_, G_ = 18, 12
GOALS = (15, 30, 45, 60, 90, 120)
DEFAULT_GOAL = 30
CHECK_EVERY = 15.0

# key, the number it looks at, the target
CATALOG = (("first_steps", "first", 1), ("h10", "hours", 10), ("h50", "hours", 50), ("h100", "hours", 100), ("p100", "plays", 100), ("p1000", "plays", 1000),
           ("s25", "songs", 25), ("s100", "songs", 100), ("a10", "artists", 10), ("st3", "streak", 3), ("st7", "streak", 7), ("st30", "streak", 30),
           ("g1", "goal_days", 1), ("g7", "goal_streak", 7), ("night", "night_h", 2), ("early", "early_h", 2), ("marathon", "day_h", 6), ("curator", "favs", 25),
           ("finisher", "finish", 70))

BADGES = {   # key: (English name, Indonesian name, English text, Indonesian text)
    "first_steps": ("First song", "Lagu pertama", "Play your first song.", "Putar lagu pertamamu."),
    "h10": ("10 hours", "10 jam", "Listen for 10 hours in total.", "Dengarkan musik 10 jam secara total."),
    "h50": ("50 hours", "50 jam", "Listen for 50 hours in total.", "Dengarkan musik 50 jam secara total."),
    "h100": ("100 hours", "100 jam", "Listen for 100 hours in total.", "Dengarkan musik 100 jam secara total."),
    "p100": ("100 plays", "100 putaran", "Play 100 songs.", "Putar 100 lagu."),
    "p1000": ("1000 plays", "1000 putaran", "Play 1000 songs.", "Putar 1000 lagu."),
    "s25": ("Library walker", "Penjelajah pustaka", "Hear 25 different songs.", "Dengarkan 25 lagu berbeda."),
    "s100": ("Deep diver", "Penyelam dalam", "Hear 100 different songs.", "Dengarkan 100 lagu berbeda."),
    "a10": ("Collector", "Kolektor", "Hear 10 different artists.", "Dengarkan 10 artis berbeda."),
    "st3": ("Warming up", "Pemanasan", "Listen 3 days in a row.", "Dengarkan musik 3 hari berturut-turut."),
    "st7": ("Full week", "Seminggu penuh", "Listen 7 days in a row.", "Dengarkan musik 7 hari berturut-turut."),
    "st30": ("Habit", "Kebiasaan", "Listen 30 days in a row.", "Dengarkan musik 30 hari berturut-turut."),
    "g1": ("Goal reached", "Target tercapai", "Reach your daily goal once.", "Capai target hariannya sekali."),
    "g7": ("On target", "Tepat sasaran", "Reach your daily goal 7 days in a row.", "Capai target harian 7 hari berturut-turut."),
    "night": ("Night owl", "Burung hantu", "Listen for 2 hours between midnight and 5 AM.", "Dengarkan 2 jam antara tengah malam dan jam 5 pagi."),
    "early": ("Early bird", "Burung pagi", "Listen for 2 hours between 5 and 8 AM.", "Dengarkan 2 jam antara jam 5 dan 8 pagi."),
    "marathon": ("Marathon", "Maraton", "Listen for 6 hours in one day.", "Dengarkan 6 jam dalam satu hari."),
    "curator": ("Curator", "Kurator", "Have 25 favourite songs.", "Punya 25 lagu favorit."),
    "finisher": ("Finisher", "Penamat", "Finish 70% of the songs you start (at least 50 plays).", "Tamatkan 70% lagu yang kamu mulai (minimal 50 putaran)."),
}
TX = {
    "en": dict(goals="Goals", daily_goal="Daily goal", min="min", today="Today", reached="Goal reached", to_go="%s to go", streak_goal="Goal streak", best="best %s",
               streak_listen="Listening streak", this_week="This week", of_days="%d of 7 days", five_weeks="Last five weeks", mon="Mon", badges="Badges", unlocked="Unlocked %s",
               locked="%s of %s", days_n="%d days", goal_hit_msg="Daily goal reached: %d minutes. Nicely done.", badge_msg="Badge unlocked: %s", badges_hist="%d badges unlocked from your history",
               none="No listening history yet. Play some music and your goals start counting.", set_goal="Goal: %d minutes a day", menu="Goals and badges", less="less", more="more",
               total_badges="%d of %d unlocked", goal_days_n="You reached the goal on %d days in all"),
    "id": dict(goals="Target", daily_goal="Target harian", min="mnt", today="Hari ini", reached="Target tercapai", to_go="Kurang %s", streak_goal="Rangkaian target", best="terbaik %s",
               streak_listen="Rangkaian mendengarkan", this_week="Minggu ini", of_days="%d dari 7 hari", five_weeks="Lima minggu terakhir", mon="Sen", badges="Lencana", unlocked="Terbuka %s",
               locked="%s dari %s", days_n="%d hari", goal_hit_msg="Target harian tercapai: %d menit. Mantap.", badge_msg="Lencana terbuka: %s", badges_hist="%d lencana terbuka dari riwayatmu",
               none="Belum ada riwayat mendengarkan. Putar musik dulu, targetmu mulai dihitung.", set_goal="Target: %d menit per hari", menu="Target dan lencana", less="sedikit",
               more="banyak", total_badges="%d dari %d terbuka", goal_days_n="Kamu mencapai target di %d hari"),
}
MENU_TEXTS = {"en": dict(gl_menu="Goals and badges"), "id": dict(gl_menu="Target dan lencana")}


def tx(lg, k):
    return I18N.pick(TX, lg, k)


def badge_text(key, lg):
    b = BADGES[key]
    if lg == "id":
        return b[1], b[3]
    return (b[0], b[2]) if lg == "en" else (I18N.tr(b[0], lg), I18N.tr(b[2], lg))


# ---------------------------------------------------------------- the file
def path():
    return os.path.join(lib.CONFIG_DIR, "goals.json")


def load(p=None):
    d = {"daily_min": DEFAULT_GOAL, "badges": {}, "init": False}
    try:
        with open(p or path(), "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            if int(raw.get("daily_min", 0)) in range(5, 601):
                d["daily_min"] = int(raw["daily_min"])
            if isinstance(raw.get("badges"), dict):
                d["badges"] = {str(k): str(v) for k, v in raw["badges"].items() if k in BADGES}
            d["init"] = bool(raw.get("init"))
    except (OSError, ValueError, TypeError):
        pass
    return d


def save(d, p=None):
    p = p or path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".goals-", dir=os.path.dirname(p))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        os.replace(tmp, p)
        return True
    except OSError as e:
        log("goals save: %r" % (e,))
        return False


# ---------------------------------------------------------------- the numbers (no window)
def goal_runs(rows, goal_s):
    """{"cur", "best", "days"} of the days that reached goal_s. cur counts back from today; a day that is still open (today) does not break it."""
    best = run = days = 0
    for r in rows:
        if r["listen"] >= goal_s:
            run += 1
            days += 1
            best = max(best, run)
        else:
            run = 0
    i = len(rows) - 1
    if i >= 0 and rows[i]["listen"] < goal_s:
        i -= 1
    cur = 0
    while i >= 0 and rows[i]["listen"] >= goal_s:
        cur += 1
        i -= 1
    return {"cur": cur, "best": best, "days": days}


def stats_from(v, goal_s, favs_n=0):
    """Every number the page and the badges use; zeros when there is no history."""
    z = {"today_s": 0.0, "goal_s": float(goal_s), "rows": [], "hours": 0.0, "plays": 0, "songs": 0, "artists": 0, "streak": 0, "streak_cur": 0, "streak_listen_best": 0,
         "goal": {"cur": 0, "best": 0, "days": 0}, "night_h": 0.0, "early_h": 0.0, "day_h": 0.0, "favs": int(favs_n), "finish": 0.0, "first": 0, "goal_days": 0, "goal_streak": 0,
         "has_history": False}
    if v is None or IN is None:
        return z
    try:
        today = IN.today(v)
        first = IN.all_span(v)[0]
        rows = IN.listen_days(v, min(first, today), today)
        tot = IN.totals_days(v, min(first, today), today) or {}
        sk = IN.streaks_days(v) or {}
    except Exception:
        return z
    hours = list(tot.get("hours") or [0.0] * 24)
    starts = int(tot.get("starts", 0))
    g = goal_runs(rows, goal_s)
    z.update({"rows": rows, "today_s": float(rows[-1]["listen"]) if rows else 0.0, "hours": float(tot.get("listen", 0.0)) / 3600.0, "plays": int(tot.get("lastfm", 0)),
              "songs": int(tot.get("songs", 0)), "artists": int(tot.get("artists", 0)), "streak": int(sk.get("longest", 0)), "streak_cur": int(sk.get("current", 0)),
              "goal": g, "night_h": sum(hours[0:5]) / 3600.0, "early_h": sum(hours[5:8]) / 3600.0, "day_h": (max(r["listen"] for r in rows) / 3600.0) if rows else 0.0,
              "finish": (100.0 * float(tot.get("completed", 0)) / starts) if starts >= 50 else 0.0, "first": 1 if int(tot.get("lastfm", 0)) >= 1 or starts >= 1 else 0,
              "goal_days": g["days"], "goal_streak": g["best"], "has_history": bool(rows) and (float(tot.get("listen", 0.0)) > 0 or starts > 0)})
    return z


def progress(st):
    """[(key, value, target, fraction 0..1)] for every badge."""
    out = []
    for key, stat, target in CATALOG:
        val = float(st.get(stat, 0) or 0)
        out.append((key, val, target, max(0.0, min(1.0, val / float(target)))))
    return out


def week_grid(rows, goal_s, weeks=5):
    """weeks x 7 list (Monday first) of the fraction of the goal reached each day (None for days that have not come yet or are before the history)."""
    if not rows:
        return []
    last = rows[-1]
    by = {r["i"]: r for r in rows}
    start = last["i"] - last["wd"] - 7 * (weeks - 1)
    grid = []
    for w in range(weeks):
        line = []
        for d in range(7):
            i = start + w * 7 + d
            r = by.get(i)
            line.append(None if (r is None or i > last["i"]) else (r["listen"] / goal_s if goal_s > 0 else 0.0))
        grid.append(line)
    return grid


# ---------------------------------------------------------------- the page
def pg_goals(c):
    app, P, F, lg, v, cv = c.app, c.P, c.F, c.lg, c.v, c.cv
    t = lambda k: tx(lg, k)
    fit = GS.fit
    st = app.gl_stats(v)
    goal_s = app.gl_data["daily_min"] * 60.0
    y = 14
    c.text(M_, y + 14, t("daily_goal").upper(), fill=P["DIM"], font=F["xs"])
    y = c.pills(M_, y + 30, [(m, "%d %s" % (m, t("min"))) for m in GOALS], app.gl_data["daily_min"], app.gl_set_goal) + 16
    if not st["has_history"] and not st["today_s"]:
        c.card(M_, y, c.W - 2 * M_, 100, "")
        c.text(M_ + 20, y + 50, fit(F["md"], t("none"), c.W - 2 * M_ - 40), fill=P["DIM"], font=F["md"])
        y += 110 + G_
    else:
        today_s = st["today_s"]
        frac = today_s / goal_s if goal_s else 0.0
        done = frac >= 1.0
        two = c.W >= 720
        lw = 330 if two else c.W - 2 * M_
        rw = (c.W - 2 * M_ - lw - G_) if two else c.W - 2 * M_
        c.card(M_, y, lw, 196, t("today"), hot=done)
        cx, cy = M_ + 84, y + 106
        CH.ring(cv, cx, cy, 52, frac, P["OK"] if done else P["GOLD"], P["CARD2"], 12)
        c.text(cx, cy - 6, "%d%%" % min(999, int(frac * 100)), fill=P["TXT"], font=F["lg"], anchor="center")
        c.text(cx, cy + 16, X.fmt_dur(today_s, lg), fill=P["DIM"], font=F["xs"], anchor="center")
        c.text(M_ + 160, y + 78, "%d %s" % (app.gl_data["daily_min"], t("min")), fill=P["GOLD"], font=F["lg"])
        c.text(M_ + 160, y + 104, fit(F["sm"], t("reached") if done else (t("to_go") % X.fmt_dur(goal_s - today_s, lg)), lw - 176), fill=P["OK"] if done else P["TXT"], font=F["sm"])
        wk = st["rows"][-7:]
        hit = sum(1 for r in wk if r["listen"] >= goal_s)
        c.text(M_ + 160, y + 132, fit(F["xs"], "%s: %s" % (t("this_week"), t("of_days") % hit), lw - 176), fill=P["DIM"], font=F["xs"])
        rx = M_ + (lw + G_ if two else 0)
        ry = y + (0 if two else 196 + G_)
        c.card(rx, ry, rw, 196, t("streak_goal"))
        g = st["goal"]
        c.text(rx + 16, ry + 66, t("days_n") % g["cur"], fill=P["GOLD"], font=F["xl"])
        c.text(rx + 16, ry + 100, t("best") % (t("days_n") % g["best"]), fill=P["DIM"], font=F["sm"])
        c.cv.create_line(rx + 16, ry + 124, rx + rw - 16, ry + 124, fill=P["GRID"])
        c.text(rx + 16, ry + 148, t("streak_listen"), fill=P["TXT"], font=F["sm"])
        c.text(rx + rw - 16, ry + 148, "%s  ·  %s" % (t("days_n") % st["streak_cur"], t("best") % (t("days_n") % st["streak"])), fill=P["GOLD"], font=F["sm"], anchor="e")
        c.text(rx + 16, ry + 172, fit(F["xs"], t("goal_days_n") % g["days"], rw - 32), fill=P["DIM"], font=F["xs"])
        y += (196 + G_) if two else 2 * (196 + G_)
        # five weeks
        grid = week_grid(st["rows"], goal_s)
        if grid:
            cw = c.W - 2 * M_
            cell = max(16, min(34, int((cw - 120) / 7.0) - 6))
            hh = 56 + len(grid) * (cell + 6) + 28
            c.card(M_, y, cw, hh, t("five_weeks"))
            names = X.T(lg, "weekdays")
            gx = M_ + 24
            for d in range(7):
                c.text(gx + d * (cell + 6) + cell / 2.0, y + 40, names[d], fill=P["DIM"], font=F["xs"], anchor="center")
            for w, line in enumerate(grid):
                for d, fr in enumerate(line):
                    x1, y1 = gx + d * (cell + 6), y + 54 + w * (cell + 6)
                    if fr is None:
                        CH.box(cv, x1, y1, x1 + cell, y1 + cell, P, 5, "cell", fill="", outline=P["GRID"])
                    else:
                        col = P["OK"] if fr >= 1.0 else (CH.mix(P["CARD2"], P["GOLD"], 0.35 + 0.6 * min(1.0, fr)) if fr > 0.02 else P["CARD2"])
                        CH.box(cv, x1, y1, x1 + cell, y1 + cell, P, 5, "cell", fill=col, outline="")
                        c.tip(x1, y1, x1 + cell, y1 + cell, "%s\n%s" % (_day_label(st["rows"], w, d, grid, lg), X.fmt_dur(fr * goal_s, lg)))
            lx = gx + 7 * (cell + 6) + 24
            c.text(lx, y + 54, t("less"), fill=P["DIM"], font=F["xs"])
            for k, fr in enumerate((0.0, 0.3, 0.6, 1.0)):
                CH.box(cv, lx, y + 72 + k * 22, lx + 16, y + 88 + k * 22, P, 4, "cell", fill=P["OK"] if fr >= 1 else (CH.mix(P["CARD2"], P["GOLD"], 0.35 + 0.6 * fr) if fr else P["CARD2"]), outline="")
            c.text(lx, y + 72 + 4 * 22 + 8, t("more"), fill=P["DIM"], font=F["xs"])
            y += hh + G_
    # the badges
    prog = progress(st)
    won = app.gl_data["badges"]
    c.text(M_, y + 12, t("badges").upper(), fill=P["TXT"], font=F["lg"])
    c.text(c.W - M_, y + 14, t("total_badges") % (sum(1 for k, *_r in prog if k in won), len(prog)), fill=P["DIM"], font=F["sm"], anchor="e")
    y += 34
    order = sorted(prog, key=lambda r: (0 if r[0] in won else 1, -r[3]))
    n3, w3 = c.cols(3)
    for i, (key, val, target, fr) in enumerate(order):
        x, yy = M_ + (i % n3) * (w3 + G_), y + (i // n3) * (96 + G_)
        on = key in won
        c.card(x, yy, w3, 96, "", hot=on)
        name, desc = badge_text(key, lg)
        mark = x + 16
        cv.create_oval(mark, yy + 14, mark + 14, yy + 28, fill=P["GOLD"] if on else P["CARD2"], outline=P["GOLD"] if on else P["GRID"])
        if on:
            cv.create_line(mark + 4, yy + 21, mark + 6, yy + 24, mark + 10, yy + 18, fill=P["BLK"], width=2)
        c.text(mark + 24, yy + 21, fit(F["md"], name, w3 - 60), fill=P["TXT"] if on else P["DIM"], font=F["md"])
        c.text(x + 16, yy + 46, fit(F["xs"], desc, w3 - 32), fill=P["DIM"], font=F["xs"])
        CH.hbar(cv, x + 16, yy + 62, w3 - 32, 5, 1.0 if on else fr, P["GOLD"] if on else P["BRN2"], P["CARD2"])
        sub = (t("unlocked") % won[key]) if on else (t("locked") % (_num(min(val, target)), _num(target)))
        c.text(x + 16, yy + 82, fit(F["xs"], sub, w3 - 32), fill=P["OK"] if on else P["DIM"], font=F["xs"])
    y += ((len(order) + n3 - 1) // n3) * (96 + G_)
    return y + 24


def _num(x):
    return str(int(x)) if abs(x - round(x)) < 0.05 else "%.1f" % x


def _day_label(rows, w, d, grid, lg):
    last = rows[-1]
    start = last["i"] - last["wd"] - 7 * (len(grid) - 1)
    i = start + w * 7 + d
    for r in rows:
        if r["i"] == i:
            return X.fmt_date(r["key"], lg)
    return ""


class Mixin:
    def gl_stats(self, v):
        """The numbers for the page (kept for 3 seconds: the tab redraws every second)."""
        ck = int(time.time() // 3)
        if self.gl_cache is not None and self.gl_cache[0] == (ck, self.gl_data["daily_min"]):
            return self.gl_cache[1]
        st = stats_from(v, self.gl_data["daily_min"] * 60.0, len(E.favorites))
        self.gl_cache = ((ck, self.gl_data["daily_min"]), st)
        return st

    def gl_set_goal(self, m):
        self.gl_data["daily_min"] = int(m)
        self.gl_cache = None
        self.gl_prev_today = None
        save(self.gl_data)
        if AN is not None:
            AN.note("goal_set", {"minutes": int(m)})
        if hasattr(self, "st_redraw"):
            self.st_redraw()

    def gl_check(self):
        """Unlocks the badges that were earned and says so; tells you the moment today's goal is reached."""
        v = IN.view() if IN is not None else None
        if v is None:
            return
        goal_s = self.gl_data["daily_min"] * 60.0
        st = stats_from(v, goal_s, len(E.favorites))
        if not st["has_history"] and not st["today_s"]:
            return
        lg = I18N.current()
        today = _dt.date.today().isoformat()
        newly = [k for k, val, target, _f in progress(st) if val >= target and k not in self.gl_data["badges"]]
        if newly:
            for k in newly:
                self.gl_data["badges"][k] = today
        first_run = not self.gl_data.get("init")
        self.gl_data["init"] = True
        if newly or first_run:
            save(self.gl_data)
        if newly:
            if first_run and len(newly) > 1:
                self.msg(tx(lg, "badges_hist") % len(newly))
            else:
                self.msg(tx(lg, "badge_msg") % ", ".join(badge_text(k, lg)[0] for k in newly))
            if AN is not None:
                AN.note("badge", {"keys": ",".join(newly)[:100]})
        prev = self.gl_prev_today
        if prev is not None and prev < goal_s <= st["today_s"] and not newly:
            self.msg(tx(lg, "goal_hit_msg") % self.gl_data["daily_min"])
        elif prev is not None and prev < goal_s <= st["today_s"]:
            self.msg(tx(lg, "goal_hit_msg") % self.gl_data["daily_min"] + "  " + tx(lg, "badge_msg") % ", ".join(badge_text(k, lg)[0] for k in newly))
        self.gl_prev_today = st["today_s"]
        self.gl_cache = None

    def gl_poll(self):
        if time.time() < self.gl_next:
            return
        self.gl_next = time.time() + CHECK_EVERY
        try:
            self.gl_check()
        except Exception as e:
            log("goals check: %r" % (e,))


def register(app):
    app.gl_data, app.gl_cache, app.gl_prev_today, app.gl_next = load(), None, None, time.time() + 6.0
    if GS is None or IN is None or CH is None or X is None:
        return
    GS.register_tab("goals", {"en": tx("en", "goals"), "id": tx("id", "goals")}, pg_goals, live=True)
    app.add_texts(**MENU_TEXTS)
    app.add_menu("gl_menu", lambda a: a.st_open("goals"))
    app.add_poll(lambda a: a.gl_poll())


# END-OF-FILE rofpalys_gui_goals.py
