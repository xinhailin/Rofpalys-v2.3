#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Rewind (your month or your year in music, like the "wrapped" recaps)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""A new tab "Rewind" in the Statistics page: pick a month or a year (the arrows go back and forth) and see the story of it - how long you listened, your number one song
and artist, your top five, your best day, your longest run of days, the hour you listen most, how many songs were new to you, and a listening style that is read from the
numbers (night owl, early bird, loyalist, explorer, marathoner ...). The look follows the theme (Classic / Modern / Cyberpunk).

  Export   SVG (a picture card, 1080 x 1350, opens in any browser and can be shared), HTML (the same card with the lists below it) and TXT, saved in
           <config folder>/rewind/ as rewind-2026-10.svg ... The window says where.
  Open     Statistics > Rewind, or Settings > Tools > Rewind

Everything is read from rofpalys_analytics.py (the history of your listening); nothing is sent anywhere. summary() and the three renderers below have no window in them."""
import datetime as _dt
import html as _html
import os
import time

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    import rofpalys_insight as IN
    import rofpalys_analytics_text as X
    import rofpalys_analytics_calc as C
    import rofpalys_gui_stats as GS
    import rofpalys_gui_stats_charts as CH
except Exception:
    IN = X = C = GS = CH = None
try:
    import rofpalys_analytics as AN
except Exception:
    AN = None
try:
    import rofpalys_theme as TH2
except Exception:
    TH2 = None

FEATURE = {"name": "rewind", "title": "Rewind: your month and year in music, with export", "version": "1.0", "order": 40, "enabled": True}
M_, G_ = 18, 12
ACTIVE_S = getattr(C, "ACTIVE_DAY_S", 60.0) if C is not None else 60.0

MONTHS = {"en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
          "id": ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"),
          "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"),
          "ru": ("Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"),
          "zh": ("一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"),
          "ja": ("1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月")}
TX = {
    "en": dict(rewind="Rewind", month="Month", year="Year", listening="Listening time", counts="%s plays  ·  %s songs  ·  %s artists", active="%d of %d days with music",
               vs_month="vs the same days last month", vs_year="vs the same days last year", top_song="Top song", top_artist="Top artist", best_day="Best day",
               streak="Longest run", peak_hour="Favourite hour", fav_day="Favourite weekday", new_songs="New to you", finished="Songs finished", by_day="Listening by day",
               by_month="Listening by month", style="Listening style", none="No listening in this period yet. Play some music and come back.", saved="Saved: %s", top5="Top songs",
               top_a="Top artists", plays_n="%s plays", days_n="%d days", songs_n="%d songs", export="Export", made="made with Rofpalys", in_progress="so far", no_history="No history yet",
               s_quiet="Quiet period", s_night_owl="Night owl", s_early_bird="Early bird", s_loyalist="Loyalist", s_explorer="Explorer", s_marathoner="Marathoner", s_regular="Regular",
               s_balanced="All-rounder",
               w_quiet="Hardly any music here.", w_night_owl="%d%% of your listening happened between midnight and 5 AM.", w_early_bird="%d%% of your listening happened between 5 and 11 AM.",
               w_loyalist="%d%% of your plays were songs you had already played this period.", w_explorer="%d songs in this period were new to you.",
               w_marathoner="On the days you listened, you listened %s on average.", w_regular="You listened on %d%% of the days.", w_balanced="A bit of everything, spread evenly."),
    "id": dict(rewind="Rewind", month="Bulan", year="Tahun", listening="Waktu mendengarkan", counts="%s putaran  ·  %s lagu  ·  %s artis", active="%d dari %d hari ada musik",
               vs_month="dibanding hari yang sama bulan lalu", vs_year="dibanding hari yang sama tahun lalu", top_song="Lagu teratas", top_artist="Artis teratas", best_day="Hari terbaik",
               streak="Rangkaian terpanjang", peak_hour="Jam favorit", fav_day="Hari favorit", new_songs="Baru buatmu", finished="Lagu sampai habis", by_day="Mendengarkan per hari",
               by_month="Mendengarkan per bulan", style="Gaya mendengarkan", none="Belum ada yang didengar di periode ini. Putar musik dulu, lalu kembali.", saved="Tersimpan: %s",
               top5="Lagu teratas", top_a="Artis teratas", plays_n="%s putaran", days_n="%d hari", songs_n="%d lagu", export="Ekspor", made="dibuat dengan Rofpalys",
               in_progress="sampai sekarang", no_history="Belum ada riwayat", s_quiet="Periode sepi", s_night_owl="Burung hantu", s_early_bird="Burung pagi", s_loyalist="Setia",
               s_explorer="Penjelajah", s_marathoner="Maraton", s_regular="Rutin", s_balanced="Serba bisa",
               w_quiet="Nyaris tidak ada musik di sini.", w_night_owl="%d%% waktu dengarmu terjadi antara tengah malam dan jam 5 pagi.",
               w_early_bird="%d%% waktu dengarmu terjadi antara jam 5 dan 11 pagi.", w_loyalist="%d%% putaranmu adalah lagu yang sudah kamu putar di periode ini.",
               w_explorer="%d lagu di periode ini baru buatmu.", w_marathoner="Di hari kamu mendengarkan, rata-rata kamu mendengarkan %s.", w_regular="Kamu mendengarkan di %d%% dari hari.",
               w_balanced="Sedikit dari segalanya, merata."),
}
MENU_TEXTS = {"en": dict(rw_menu="Rewind (month / year recap)"), "id": dict(rw_menu="Rewind (rekap bulan / tahun)")}


def tx(lg, k):
    return I18N.pick(TX, lg, k)


def period_label(kind, y, m, lg):
    return ("%s %d" % (MONTHS.get(lg, MONTHS["en"])[m - 1], y)) if kind == "month" else str(y)


def period_days(kind, y, m):
    return IN.month_span(y, m) if kind == "month" else IN.year_span(y)


def prev_period(kind, y, m):
    if kind == "month":
        return (y - 1, 12) if m == 1 else (y, m - 1)
    return (y - 1, m)


# ---------------------------------------------------------------- the numbers
def style_of(sm):
    """The listening style, read from the numbers: (key, number the sentence shows)."""
    if sm["listen"] < 600 or not sm["starts"]:
        return "quiet", 0
    sh = sm["shares"]
    if sh["night"] >= 0.35:
        return "night_owl", round(sh["night"] * 100)
    if sh["morning"] >= 0.35:
        return "early_bird", round(sh["morning"] * 100)
    if sm["repeat_ratio"] >= 0.6:
        return "loyalist", round(sm["repeat_ratio"] * 100)
    if sm["new_n"] >= 15 and sm["new_n"] >= 0.4 * max(1, sm["songs_n"]):
        return "explorer", sm["new_n"]
    if sm["active_days"] and sm["listen"] / sm["active_days"] >= 3 * 3600:
        return "marathoner", sm["listen"] / sm["active_days"]
    if sm["days_n"] and sm["active_days"] / float(sm["days_n"]) >= 0.8:
        return "regular", round(100.0 * sm["active_days"] / sm["days_n"])
    return "balanced", 0


def summary(v, a, b, prev=None, today=None):
    """Everything the recap shows for the day numbers a..b (days after `today` are not counted as days). prev = (first, last) of the period to compare with, or None."""
    today = IN.today(v) if today is None else today
    end = min(b, today)
    tot = IN.totals_days(v, a, end) or {}
    songs = IN.rank_days(v, a, end, "song", "plays", "lastfm", 0)
    arts = IN.rank_days(v, a, end, "artist", "plays", "lastfm", 0)
    series = IN.listen_days(v, a, end)
    hours = list(tot.get("hours") or [0.0] * 24)
    hs = sum(hours)
    shares = {"night": sum(hours[0:5]) / hs, "morning": sum(hours[5:12]) / hs, "afternoon": sum(hours[12:18]) / hs, "evening": sum(hours[18:24]) / hs} if hs > 0 else \
        {"night": 0.0, "morning": 0.0, "afternoon": 0.0, "evening": 0.0}
    best = None
    for r in series:
        if r["listen"] > 0 and (best is None or r["listen"] > best["listen"]):
            best = r
    run, run_best, run_from, best_from = 0, 0, None, None
    for r in series:
        if r["listen"] >= ACTIVE_S:
            run += 1
            run_from = r["key"] if run == 1 else run_from
            if run > run_best:
                run_best, best_from = run, run_from
        else:
            run = 0
    wd = [0.0] * 7
    for r in series:
        wd[r["wd"]] += r["listen"]
    starts, plays = int(tot.get("starts", 0)), int(tot.get("lastfm", 0))
    new = IN.new_in_period(v, a, end)
    sm = {"a": a, "b": end, "listen": float(tot.get("listen", 0.0)), "open": float(tot.get("open", 0.0)), "starts": starts, "plays": plays,
          "songs_n": len(songs), "artists_n": len(arts), "active_days": int(tot.get("active_days", 0)), "days_n": max(0, end - a + 1),
          "songs": songs, "artists": arts, "series": series, "hours": hours, "shares": shares, "best_day": best, "run": run_best, "run_from": best_from,
          "peak_hour": max(range(24), key=lambda h: hours[h]) if hs > 0 else None, "weekday_s": wd, "fav_weekday": max(range(7), key=lambda w: wd[w]) if sum(wd) > 0 else None,
          "new_n": len(new), "repeat_ratio": (1.0 - len(songs) / float(starts)) if starts else 0.0,
          "completion": (float(tot.get("completed", 0)) / starts) if starts else 0.0, "prev_listen": None}
    if prev is not None:
        pa, pb = prev
        pb = min(pb, pa + max(0, end - a))                         # the same number of days: an unfinished month is not compared with a whole one
        pt = IN.totals_days(v, pa, pb)
        sm["prev_listen"] = float(pt.get("listen", 0.0)) if pt else None
    sm["style"], sm["style_n"] = style_of(sm)
    return sm


def style_text(sm, lg):
    k, n = sm["style"], sm["style_n"]
    why = tx(lg, "w_" + k)
    if k == "marathoner":
        why = why % X.fmt_dur(n, lg)
    elif "%" in why:
        why = why % n
    return tx(lg, "s_" + k), why


def clock(h):
    return "%02d:00" % h if h is not None else "-"


def fmt_day(key, lg):
    return X.fmt_date(key, lg, year=True) if key else "-"


# ---------------------------------------------------------------- the renderers (no window)
def render_text(sm, label, lg):
    t = lambda k: tx(lg, k)
    sty, why = style_text(sm, lg)
    L = ["ROFPALYS REWIND  -  " + label, "=" * 44, "%s: %s" % (t("listening"), X.fmt_dur(sm["listen"], lg)),
         t("counts") % (X.fmt_num(sm["plays"], lg), X.fmt_num(sm["songs_n"], lg), X.fmt_num(sm["artists_n"], lg)), t("active") % (sm["active_days"], sm["days_n"]),
         "%s: %s  -  %s" % (t("style"), sty, why), ""]
    L.append(t("top5").upper())
    for i, r in enumerate(sm["songs"][:5]):
        L.append("%2d. %s - %s  (%s)" % (i + 1, r["title"], r["artist"], t("plays_n") % X.fmt_num(r["plays"], lg)))
    L.append("")
    L.append(t("top_a").upper())
    for i, r in enumerate(sm["artists"][:5]):
        L.append("%2d. %s  (%s)" % (i + 1, r["name"], t("plays_n") % X.fmt_num(r["plays"], lg)))
    L.append("")
    if sm["best_day"]:
        L.append("%s: %s  (%s)" % (t("best_day"), fmt_day(sm["best_day"]["key"], lg), X.fmt_dur(sm["best_day"]["listen"], lg)))
    L.append("%s: %s" % (t("streak"), t("days_n") % sm["run"]))
    L.append("%s: %s" % (t("peak_hour"), clock(sm["peak_hour"])))
    if sm["fav_weekday"] is not None:
        L.append("%s: %s" % (t("fav_day"), X.T(lg, "weekdays_long")[sm["fav_weekday"]]))
    L.append("%s: %d" % (t("new_songs"), sm["new_n"]))
    L.append("")
    L.append(t("made"))
    return "\n".join(L) + "\n"


def _x(s):
    return _html.escape(str(s), quote=True)


def _cut(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


def _svg_box(x, y, w, h, fill, stroke, shape, r, sw=2, extra=""):
    if shape in ("round", "pill"):
        return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s" %s/>' % (x, y, w, h, r, fill, stroke, sw, extra)
    if shape == "cut":
        c = r
        pts = "%s,%s %s,%s %s,%s %s,%s %s,%s %s,%s" % (x + c, y, x + w, y, x + w, y + h - c, x + w - c, y + h, x, y + h, x, y + c)
        return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" %s/>' % (pts, fill, stroke, sw, extra)
    return '<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s" %s/>' % (x, y, w, h, fill, stroke, sw, extra)


def render_svg(sm, label, lg, P):
    """A 1080 x 1350 picture card in the colours, corners and type of the look given in P (a theme palette)."""
    t = lambda k: tx(lg, k)
    st = P.get("STYLE", {})
    shape, rad = st.get("shape", "flat"), {"round": 26, "cut": 24, "pill": 26}.get(st.get("shape", "flat"), 0)
    fam = ", ".join("'%s'" % f for f in (tuple(st.get("ui", ())) + ("DejaVu Sans",))) + ", Arial, sans-serif"
    disp = ", ".join("'%s'" % f for f in (tuple(st.get("display", ())) + ("DejaVu Sans",))) + ", Arial, sans-serif"
    sty, why = style_text(sm, lg)
    caps = bool(st.get("caps"))
    up = (lambda s: str(s).upper()) if caps else (lambda s: str(s))
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1350" width="1080" height="1350" role="img" aria-label="%s">' % _x("Rofpalys Rewind " + label),
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>' % (P["PNL"], P["BLK"]),
         '<rect width="1080" height="1350" fill="url(#bg)"/>',
         '<circle cx="940" cy="150" r="260" fill="%s" opacity="0.13"/>' % P["GOLD"], '<circle cx="90" cy="1250" r="300" fill="%s" opacity="0.10"/>' % P["ACC2"],
         '<text x="70" y="108" font-family="%s" font-size="30" letter-spacing="8" fill="%s">%s</text>' % (fam, P["GOLD"], _x("ROFPALYS REWIND")),
         '<text x="70" y="196" font-family="%s" font-size="76" font-weight="700" fill="%s">%s</text>' % (disp, P["TXT"], _x(up(label))),
         '<text x="70" y="262" font-family="%s" font-size="30" fill="%s">%s</text>' % (fam, P["DIM"], _x(up(t("listening")))),
         '<text x="70" y="388" font-family="%s" font-size="148" font-weight="700" fill="%s">%s</text>' % (disp, P["GOLD"], _x(X.fmt_dur(sm["listen"], lg))),
         '<text x="70" y="448" font-family="%s" font-size="32" fill="%s">%s</text>' % (fam, P["TXT"], _x(t("counts") % (X.fmt_num(sm["plays"], lg), X.fmt_num(sm["songs_n"], lg), X.fmt_num(sm["artists_n"], lg))))]
    # the style badge
    o.append(_svg_box(70, 492, 940, 118, P["PNL2"], P["GOLD"], shape, rad))
    o.append('<text x="104" y="548" font-family="%s" font-size="42" font-weight="700" fill="%s">%s</text>' % (disp, P["GOLD"], _x(up(sty))))
    o.append('<text x="104" y="590" font-family="%s" font-size="26" fill="%s">%s</text>' % (fam, P["TXT"], _x(_cut(why, 74))))
    # two lists
    def column(x, title, rows, sub):
        out = [_svg_box(x, 650, 450, 440, P["PNL2"], P["GRID"], shape, rad, 2), '<text x="%d" y="704" font-family="%s" font-size="26" letter-spacing="3" fill="%s">%s</text>' % (x + 30, fam, P["GOLD"], _x(up(title)))]
        for i, r in enumerate(rows[:5]):
            yy = 764 + i * 62
            out.append('<text x="%d" y="%d" font-family="%s" font-size="34" font-weight="700" fill="%s">%d</text>' % (x + 30, yy, disp, P["GOLD"] if i == 0 else P["DIM"], i + 1))
            out.append('<text x="%d" y="%d" font-family="%s" font-size="27" fill="%s">%s</text>' % (x + 76, yy - 6, fam, P["TXT"], _x(_cut(r[0], 24))))
            out.append('<text x="%d" y="%d" font-family="%s" font-size="20" fill="%s">%s</text>' % (x + 76, yy + 18, fam, P["DIM"], _x(_cut(r[1], 32))))
        return out
    o += column(70, t("top5"), [(r["title"], "%s  ·  %s" % (r["artist"], t("plays_n") % X.fmt_num(r["plays"], lg))) for r in sm["songs"]], "")
    o += column(560, t("top_a"), [(r["name"], "%s  ·  %s" % (t("plays_n") % X.fmt_num(r["plays"], lg), t("songs_n") % r["songs"])) for r in sm["artists"]], "")
    # three small facts
    facts = [(t("best_day"), (X.fmt_date(sm["best_day"]["key"], lg) if sm["best_day"] else "-")), (t("peak_hour"), clock(sm["peak_hour"])), (t("streak"), t("days_n") % sm["run"])]
    for i, (k, val) in enumerate(facts):
        x = 70 + i * 316
        o.append(_svg_box(x, 1124, 308, 120, P["PNL2"], P["GRID"], shape, rad, 2))
        o.append('<text x="%d" y="1166" font-family="%s" font-size="20" letter-spacing="2" fill="%s">%s</text>' % (x + 24, fam, P["DIM"], _x(up(k))))
        o.append('<text x="%d" y="1218" font-family="%s" font-size="38" font-weight="700" fill="%s">%s</text>' % (x + 24, disp, P["TXT"], _x(_cut(val, 14))))
    o.append('<text x="540" y="1306" text-anchor="middle" font-family="%s" font-size="22" fill="%s">%s</text>' % (fam, P["DIM"], _x(t("made"))))
    o.append("</svg>")
    return "\n".join(o)


def render_html(sm, label, lg, P):
    t = lambda k: tx(lg, k)
    svg = render_svg(sm, label, lg, P)
    rows = "".join("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (i + 1, _x(r["title"]), _x(r["artist"]), _x(X.fmt_num(r["plays"], lg))) for i, r in enumerate(sm["songs"][:10]))
    arts = "".join("<tr><td>%d</td><td>%s</td><td>%s</td></tr>" % (i + 1, _x(r["name"]), _x(X.fmt_num(r["plays"], lg))) for i, r in enumerate(sm["artists"][:10]))
    return ("<!doctype html>\n<html lang=\"%s\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Rofpalys Rewind - %s</title>"
            "<style>body{margin:0;background:%s;color:%s;font-family:system-ui,Arial,sans-serif}main{max-width:560px;margin:0 auto;padding:16px}svg{width:100%%;height:auto;display:block}"
            "h2{color:%s;font-size:15px;letter-spacing:.12em;text-transform:uppercase;margin:28px 0 8px}table{width:100%%;border-collapse:collapse}td{padding:6px 8px;border-bottom:1px solid %s}"
            "td:first-child{color:%s;width:32px}</style></head><body><main>%s<h2>%s</h2><table>%s</table><h2>%s</h2><table>%s</table></main></body></html>\n"
            % (lg, _x(label), P["BLK"], P["TXT"], P["GOLD"], P["GRID"], P["DIM"], svg, _x(t("top5")), rows, _x(t("top_a")), arts))


def export_files(sm, label, key, lg, P, folder=None):
    """Writes rewind-<key>.svg / .html / .txt; returns [paths]."""
    folder = folder or os.path.join(lib.CONFIG_DIR, "rewind")
    os.makedirs(folder, exist_ok=True)
    out = []
    for ext, data in (("svg", render_svg(sm, label, lg, P)), ("html", render_html(sm, label, lg, P)), ("txt", render_text(sm, label, lg))):
        path = os.path.join(folder, "rewind-%s.%s" % (key, ext))
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        out.append(path)
    return out


# ---------------------------------------------------------------- the page (drawn with the statistics page's own tools)
def pg_rewind(c):
    app, P, F, lg, v, cv = c.app, c.P, c.F, c.lg, c.v, c.cv
    t = lambda k: tx(lg, k)
    fit = GS.fit
    y = 14
    y = c.pills(M_, y, [("month", t("month")), ("year", t("year"))], app.rw_kind, app.rw_set_kind) + 14
    label = period_label(app.rw_kind, app.rw_y, app.rw_m, lg)
    sm, key = app.rw_data(v)
    aw = F["md"].measure("    ") + 28                                           # the arrows are drawn lines, so no font has to have an arrow glyph
    lw = F["lg"].measure(label)
    for k, (ax, d) in enumerate(((M_, -1), (M_ + aw + 28 + lw, 1))):
        CH.pill(cv, ax, y, "    ", False, F["md"], P)
        mx, my, dx = ax + aw / 2.0, y + 14, (-3 if d < 0 else 3)
        cv.create_line(mx - dx, my - 5, mx + dx, my, mx - dx, my + 5, fill=P["TXT"], width=2)
        c.click(ax, y, ax + aw, y + 28, (lambda dd=d: app.rw_move(dd)))
    c.text(M_ + aw + 14, y + 14, label, fill=P["TXT"], font=F["lg"])
    y += 28 + 12
    if sm is None or sm["listen"] <= 0:
        c.card(M_, y, c.W - 2 * M_, 110, "")
        c.text(M_ + 20, y + 55, fit(F["md"], t("none") if IN is not None and IN.view() is not None else t("no_history"), c.W - 2 * M_ - 40), fill=P["DIM"], font=F["md"])
        return y + 140
    # export row
    y = c.pills(M_, y, [("svg", t("export") + " SVG"), ("html", t("export") + " HTML"), ("txt", t("export") + " TXT")], None, app.rw_export) + 14
    if app.rw_note:
        c.text(M_, y, fit(F["xs"], app.rw_note, c.W - 2 * M_), fill=P["GOLD"], font=F["xs"])
        y += 20
    y += 4
    # hero
    two = c.W >= 700
    hh = 150
    c.card(M_, y, c.W - 2 * M_, hh, t("listening") + (("  ·  " + t("in_progress")) if sm["b"] < app.rw_end else ""), hot=True)
    c.text(M_ + 20, y + 74, X.fmt_dur(sm["listen"], lg), fill=P["GOLD"], font=F["xl"])
    sub = t("counts") % (X.fmt_num(sm["plays"], lg), X.fmt_num(sm["songs_n"], lg), X.fmt_num(sm["artists_n"], lg))
    wsub = (c.W - 2 * M_ - 40) * (0.55 if two else 1.0)
    c.text(M_ + 20, y + 108, fit(F["sm"], sub, wsub), fill=P["TXT"], font=F["sm"])
    d = X.delta_text(sm["listen"], sm["prev_listen"], lg) if sm["prev_listen"] else ""
    line2 = t("active") % (sm["active_days"], sm["days_n"]) + (("   ·   %s %s" % (d, t("vs_month" if app.rw_kind == "month" else "vs_year"))) if d else "")
    c.text(M_ + 20, y + 130, fit(F["xs"], line2, wsub), fill=(P["OK"] if d.startswith("+") else (P["WARN"] if d else P["DIM"])), font=F["xs"])
    sty, why = style_text(sm, lg)
    if two:
        bx = M_ + (c.W - 2 * M_) * 0.58
        c.text(bx, y + 40, t("style").upper(), fill=P["DIM"], font=F["xs"])
        c.text(bx, y + 72, fit(F["lg"], sty, c.W - M_ - bx - 20), fill=P["GOLD"], font=F["lg"])
        cv.create_text(bx, y + 92, text=why, fill=P["TXT"], font=F["xs"], anchor="nw", width=c.W - M_ - bx - 20)
    else:
        c.text(M_ + 20, y + 28, fit(F["xs"], t("style").upper() + ":  " + sty, c.W - 2 * M_ - 40), fill=P["GOLD"], font=F["xs"], anchor="w")
    y += hh + G_
    # number one song and artist
    n2, w2 = c.cols(2)
    s1 = sm["songs"][0] if sm["songs"] else None
    a1 = sm["artists"][0] if sm["artists"] else None
    for i, (title, big, sub1, sub2) in enumerate(((t("top_song"), s1["title"] if s1 else "-", s1["artist"] if s1 else "", ("%s  ·  %s" % (t("plays_n") % X.fmt_num(s1["plays"], lg), X.fmt_dur(s1["time"], lg))) if s1 else ""),
                                                  (t("top_artist"), a1["name"] if a1 else "-", (t("songs_n") % a1["songs"]) if a1 else "", ("%s  ·  %s" % (t("plays_n") % X.fmt_num(a1["plays"], lg), X.fmt_dur(a1["time"], lg))) if a1 else ""))):
        x = M_ + (i * (w2 + G_) if n2 > 1 else 0)
        yy = y + (0 if n2 > 1 else i * (130 + G_))
        c.card(x, yy, w2, 130, title)
        c.text(x + 18, yy + 58, fit(F["lg"], big, w2 - 36), fill=P["GOLD"], font=F["lg"])
        c.text(x + 18, yy + 84, fit(F["sm"], sub1, w2 - 36), fill=P["TXT"], font=F["sm"])
        c.text(x + 18, yy + 106, fit(F["xs"], sub2, w2 - 36), fill=P["DIM"], font=F["xs"])
        if i == 0 and s1:
            c.click(x, yy, x + w2, yy + 130, lambda p=s1["name"]: app.st_select_song(p))
    y += (130 + G_) if n2 > 1 else 2 * (130 + G_)
    # top five lists (the statistics page's own list)
    h1 = GS.toplist(c, M_, y, w2, sm["songs"][:5], c.t("top_songs"), "song")
    h2 = GS.toplist(c, M_ + (w2 + G_ if n2 > 1 else 0), y + (0 if n2 > 1 else h1 + G_), w2, sm["artists"][:5], c.t("top_artists"), "artist")
    y += (max(h1, h2) if n2 > 1 else h1 + G_ + h2) + G_
    # small facts
    bd = sm["best_day"]
    facts = [(t("best_day"), X.fmt_date(bd["key"], lg) if bd else "-", X.fmt_dur(bd["listen"], lg) if bd else ""),
             (t("streak"), t("days_n") % sm["run"], (fmt_day(sm["run_from"], lg)) if sm["run_from"] else ""),
             (t("peak_hour"), clock(sm["peak_hour"]), ""),
             (t("fav_day"), X.T(lg, "weekdays_long")[sm["fav_weekday"]] if sm["fav_weekday"] is not None else "-", ""),
             (t("new_songs"), str(sm["new_n"]), ""),
             (t("finished"), X.fmt_pct(sm["completion"]), "")]
    n3, w3 = c.cols(3)
    for i, (cap, val, sub) in enumerate(facts):
        x, yy = M_ + (i % n3) * (w3 + G_), y + (i // n3) * (100 + G_)
        c.card(x, yy, w3, 100, cap)
        c.text(x + 16, yy + 54, fit(F["lg"], val, w3 - 32), fill=P["GOLD"], font=F["lg"])
        c.text(x + 16, yy + 82, fit(F["xs"], sub, w3 - 32), fill=P["DIM"], font=F["xs"])
    y += ((len(facts) + n3 - 1) // n3) * (100 + G_)
    # the chart: days of a month, months of a year
    if app.rw_kind == "month":
        bars = [(r["key"][8:], r["listen"]) for r in sm["series"]]
        tips = [(X.fmt_date(r["key"], lg) + "\n" + X.fmt_dur(r["listen"], lg)) for r in sm["series"]]
        ttl = t("by_day")
    else:
        agg = {}
        for r in sm["series"]:
            agg[int(r["key"][5:7])] = agg.get(int(r["key"][5:7]), 0.0) + r["listen"]
        mo = X.T(lg, "months")
        last_m = int(sm["series"][-1]["key"][5:7]) if sm["series"] else 0
        bars = [(mo[m - 1], agg.get(m, 0.0)) for m in range(1, last_m + 1)]
        tips = ["%s\n%s" % (MONTHS.get(lg, MONTHS["en"])[i], X.fmt_dur(b[1], lg)) for i, b in enumerate(bars)]
        ttl = t("by_month")
    if bars:
        cw = c.W - 2 * M_
        c.card(M_, y, cw, 232, ttl)
        top_i = max(range(len(bars)), key=lambda i: bars[i][1])
        CH.bars(cv, M_ + 16, y + 30, cw - 32, 196, bars, P, F["xs"], 1 if cw > 620 and len(bars) <= 20 else (2 if len(bars) <= 31 else 1), c.hits, top_i,
                lambda i: tips[i], lambda s: X.fmt_axis(s, lg))
        y += 232 + G_
    return y + 24


class Mixin:
    def rw_range(self):
        """(first day, last day, label, key, previous period) of what is picked."""
        a, b = period_days(self.rw_kind, self.rw_y, self.rw_m)
        py, pm = prev_period(self.rw_kind, self.rw_y, self.rw_m)
        pa, pb = period_days(self.rw_kind, py, pm)
        key = ("%04d-%02d" % (self.rw_y, self.rw_m)) if self.rw_kind == "month" else "%04d" % self.rw_y
        return a, b, key, (pa, pb)

    def rw_data(self, v):
        """The summary of the picked period (kept for a few seconds; a redraw every second must not recount the history)."""
        a, b, key, prev = self.rw_range()
        self.rw_end = b
        ck = (self.rw_kind, key, int(time.time() // 8))
        if self.rw_cache is not None and self.rw_cache[0] == ck:
            return self.rw_cache[1], key
        try:
            sm = summary(v, a, b, prev)
        except Exception as e:
            log("rewind: %r" % (e,))
            sm = None
        self.rw_cache = (ck, sm)
        return sm, key

    def rw_set_kind(self, k):
        self.rw_kind = k
        self.rw_cache = None
        self.rw_note = ""
        self.st_redraw()

    def rw_move(self, d):
        today = _dt.date.today()
        v = IN.view() if IN is not None else None
        first = IN.day_date(IN.all_span(v)[0]) if v is not None else today
        if self.rw_kind == "month":
            n = self.rw_y * 12 + (self.rw_m - 1) + d
            y, m = n // 12, n % 12 + 1
            if (y, m) > (today.year, today.month) or (y, m) < (first.year, first.month):
                return
            self.rw_y, self.rw_m = y, m
        else:
            y = self.rw_y + d
            if y > today.year or y < first.year:
                return
            self.rw_y = y
        self.rw_cache = None
        self.rw_note = ""
        self.st_redraw()

    def rw_export(self, kind=None):
        v = IN.view() if IN is not None else None
        sm, key = self.rw_data(self.st_view_now() if hasattr(self, "st_view_now") else v)
        if sm is None or sm["listen"] <= 0:
            return
        lg = self.st_lang() if hasattr(self, "st_lang") else "en"
        P = TH2.palette() if TH2 is not None else {k: globals()[k] for k in ("BLK", "PNL", "PNL2", "GOLD", "TXT", "DIM", "ACC2", "GRID")} | {"STYLE": dict(STYLE)}
        label = period_label(self.rw_kind, self.rw_y, self.rw_m, lg)
        try:
            paths = export_files(sm, label, key, lg, P)
        except OSError as e:
            self.rw_note = str(e)
            self.st_redraw()
            return
        want = {"svg": 0, "html": 1, "txt": 2}.get(kind, 0)
        self.rw_note = tx(lg, "saved") % paths[want]
        if AN is not None:
            AN.note("rewind_export", {"kind": kind or "svg", "period": key})
        self.msg(self.rw_note)
        self.st_redraw()


def register(app):
    today = _dt.date.today()
    app.rw_kind, app.rw_y, app.rw_m, app.rw_cache, app.rw_note, app.rw_end = "month", today.year, today.month, None, "", 0
    if GS is None or IN is None or CH is None or X is None:
        return
    GS.register_tab("rewind", {"en": tx("en", "rewind"), "id": tx("id", "rewind")}, pg_rewind)
    app.add_texts(**MENU_TEXTS)
    app.add_menu("rw_menu", lambda a: a.st_open("rewind"))


# END-OF-FILE rofpalys_gui_rewind.py
