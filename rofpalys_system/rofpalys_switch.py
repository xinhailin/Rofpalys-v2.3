#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - switch between the window (GUI) and the terminal (CLI) without losing the song: the GUI button "CLI", and "7y" in the terminal
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""The two screens are two programs. A switch is: remember what plays (song, position, paused or not) in a small file, start the other screen, and close this one.
The other screen reads the file when it starts and carries on at the same second.

    snap = snapshot(E)                    # what plays now
    ok, text = start("CLI", snap)         # the GUI button; "GUI" is what  7y  in the terminal calls
    snap = take("GUI")                    # the screen that was just started: the song to carry on with (None when it was started by hand)

The terminal that shows the CLI is found the way the app icon does it (xfce4-terminal, gnome-terminal, konsole ... xterm). Nothing here needs tkinter or curses."""
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

import rofpalys_library as lib

__version__ = "1.0"
HANDOFF = os.path.join(lib.CACHE_DIR, "handoff.json")
FRESH_S = 60.0                                       # a hand-off file older than this was left behind by a switch that never finished: ignored
TITLE = "Rofpalys CLI"
TERMS = (("xfce4-terminal", ["-T", TITLE, "-x"]), ("gnome-terminal", ["--title", TITLE, "--"]), ("mate-terminal", ["--title", TITLE, "-x"]), ("konsole", ["-e"]),
         ("qterminal", ["-e"]), ("lxterminal", ["-t", TITLE, "-e"]), ("alacritty", ["-t", TITLE, "-e"]), ("kitty", ["--title", TITLE]),
         ("x-terminal-emulator", ["-e"]), ("xterm", ["-T", TITLE, "-e"]))
SUB = {"GUI": "gui", "CLI": "tui"}


def snapshot(E):
    """What plays now: {'song', 'pos', 'playing'} (song None = nothing is loaded)."""
    song = getattr(E, "playing_song_name", None)
    try:
        pos = float(E.get_position()) if song else 0.0
    except Exception:
        pos = 0.0
    return {"song": song, "pos": round(pos, 2), "playing": bool(song and getattr(E, "is_playing", False) and not getattr(E, "is_paused", False))}


def _write(snap, to):
    data = dict(snap or {}, to=to, at=time.time())
    try:
        os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
        tmp = HANDOFF + ".part"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, HANDOFF)
        return True
    except OSError:
        return False


def clear():
    try:
        os.remove(HANDOFF)
    except OSError:
        pass


def take(to):
    """The hand-off for the screen `to` ('GUI' / 'CLI'): the file is read once and removed. None when there is none, it is old, or it was meant for the other screen."""
    try:
        with open(HANDOFF, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if str(d.get("to", "")).upper() != to.upper():
        return None
    clear()
    if time.time() - float(d.get("at", 0) or 0) > FRESH_S or not d.get("song"):
        return None
    return d


def resume(E, snap):
    """Carries on with a hand-off in this screen: the same song at the same second (paused when it was paused) -> True when something was started."""
    if not snap or not snap.get("song") or not os.path.isfile(snap["song"]):
        return False
    try:
        E.play_song(snap["song"], start=max(0.0, float(snap.get("pos", 0) or 0)))
        if not snap.get("playing", True):                     # it was paused over there: pause as soon as the engine reports the song as started
            for _ in range(30):
                if getattr(E, "is_playing", False):
                    break
                time.sleep(0.02)
            if getattr(E, "is_playing", False) and not getattr(E, "is_paused", False):
                E.toggle_play()
        return True
    except Exception:
        return False


def command(sub):
    """[python, rofpalys, sub]: the command that starts a screen. ROFPALYS_LAUNCHER is what the launcher sets for the programs it starts."""
    exe = os.environ.get("ROFPALYS_LAUNCHER") or ""
    if not (exe and os.path.isfile(exe)):
        exe = shutil.which("rofpalys") or ""
    if not exe:
        for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser("~")):
            cand = os.path.join(d, "rofpalys.py")
            if os.path.isfile(cand):
                exe = cand
                break
    if not exe:
        return None
    return [sys.executable or "python3", exe, sub]


def can_gui():
    """(True, '') when a window can open here, else (False, why)."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False, "Tk"
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False, "DISPLAY"
    return True, ""


def _log_path():
    return os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache"), "rofpalys", "launcher.log")


def start(mode, snap=None, settle=1.5):
    """Starts the other screen -> (ok, text). mode 'GUI' = the window (in the background), 'CLI' = a terminal window that runs the terminal player.
    The hand-off is written first; when the start fails it is removed again and text says why."""
    mode = mode.upper()
    cmd = command(SUB[mode])
    if cmd is None:
        return False, "rofpalys command not found"
    if snap is not None:
        _write(snap, mode)
    dn = subprocess.DEVNULL
    try:
        if mode == "GUI":
            lp = _log_path()
            os.makedirs(os.path.dirname(lp), exist_ok=True)
            kw = {"start_new_session": True} if os.name == "posix" else {"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
            with open(lp, "ab") as log:
                proc = subprocess.Popen(cmd, stdin=dn, stdout=log, stderr=log, cwd=os.path.expanduser("~"), **kw)
            try:
                rc = proc.wait(timeout=settle)
            except subprocess.TimeoutExpired:
                return True, "GUI"                                   # still running after the settle time: it is up
            if rc in (0, None):
                return True, "GUI"                                   # started from a terminal it hands over to a second process and ends well
            clear()
            return False, "GUI: exit code %s (see %s)" % (rc, lp)
        script = shlex.join(cmd) + '; rc=$?; [ $rc -ne 0 ] && { echo; read -r -p "[exit $rc] Enter..." _; }; exit $rc'
        for term, pre in TERMS:
            if shutil.which(term):
                subprocess.Popen([term, *pre, "bash", "-lc", script], stdin=dn, stdout=dn, stderr=dn, start_new_session=True)
                return True, "CLI: " + term
        clear()
        return False, "no terminal found (xterm / xfce4-terminal)"
    except OSError as e:
        clear()
        return False, str(e)


# END-OF-FILE rofpalys_switch.py
