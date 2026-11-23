#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - main launcher. File name here: rofpalys.py  (so phones can download/open it)
# Install it as:  cp rofpalys.py $PREFIX/bin/rofpalys
#
# Copyright (C) 2026 rofpalys-nagiryu
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details. You should have received a copy of the GNU General Public
# License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""Rofpalys launcher = the PARENT file. It finds every other file, checks that none was cut off, installs them and starts the program.

  rofpalys.py                 this file  (installed as the command  rofpalys)
  CORE FILES (required)       rofpalys_library / _sleep / _lyrics / _CyroKayAI_* (9 files, below) / _queue / _effects / _spectrum / _stats / _playlists / _alarm /
                              _control / _engine / _media / _tui / _gui_base / _gui   .py       -> the list is MODULES below
  THE LYRIC BRAIN (CyroKayAI 4)  rofpalys_CyroKayAI_lyric.py  = the conductor: creator check, internet check, fitting every line to the real voice, 🎶 / 🎵 markers
                              _ears (listening: voice / melody / notes / tempo)   _text (syllables, silences, word times)   _learn (teaches a voice
                              detector on the song itself)   _memory (what it learned from your songs and corrections)   _turbo (all processor cores)
                              _clock (steady song clock + Spotify-style scroll maths)   _view (the Tk screen that draws the live lyrics)
                              _providers (where the lyrics come from: MUSIXMATCH is the standard and, by default, the only source;  rofpalys lyrics source all  adds
                              syncedlyrics, lrcdl, lyriq, librelyrics and the built-in LRCLIB / YouTube / lyrics.ovh, each judged by the audio fit)
                              _warp (the lyrics FOLLOW THE RECORDING: one shift + a slower / faster clock for the whole song: 5:25 lyrics on a 5:30 recording, the voice
                              coming in at 0:10 where the first line says 0:05; and when the audio is unclear the first line still goes onto the first singing).
                              rofpalys_lyrics.py asks the brain first; this launcher only installs the files and runs  rofpalys lyrics ...
  SUPPORT FILES (optional)    rofpalys_analytics.py (+ _calc, _text) = the statistics recorder and its tamper-evident log, rofpalys_theme.py = the three looks
                              (Classic / Modern / Cyberpunk: colours AND shapes AND type - the whole window is built again when you switch), rofpalys_gui_stats_charts.py
                              = the drawing parts of the Statistics page (a menu item in the sidebar, under Now Playing). Without them the player still starts;
                              it just has no statistics and only the Classic look.  Commands:  rofpalys stats ...   rofpalys theme ...
  FEATURE FILES (optional)    rofpalys_gui_playlists.py, rofpalys_gui_queue.py, rofpalys_gui_stats.py, rofpalys_gui_theme.py, rofpalys_gui_effects.py,
                              rofpalys_gui_sleep.py, rofpalys_gui_lyrics.py ...  and any file YOU add: rofpalys_gui_<name>.py
  NEW IN 5.9 (five features)  rofpalys_gui_palette.py = command palette, Ctrl+K: songs, artists, folders, pages and actions in one box
                              rofpalys_gui_mixes.py   = smart mixes (the "Mix" tab): heavy rotation, on repeat, forgotten favorites, fresh finds, night / morning / daily mix, all-time top
                              rofpalys_gui_rewind.py  = Rewind: your month or year in music (a tab of the Statistics page), export as SVG / HTML / text
                              rofpalys_gui_goals.py   = daily listening goal, goal streak and 19 badges (a tab of the Statistics page)
                              rofpalys_gui_remote.py  = Web Remote: control the player from a browser, with a secret token (off until you turn it on in the "..." menu)
                              rofpalys_insight.py     = the shared reader of the listening history that mixes, Rewind and goals use (optional, like the analytics files)
  THE APP (5.9.1)             the icon launcher lives IN THIS FILE now (it used to be rofpalys_launcher.py + rofpalys_logo.svg + rofpalys_launcher.desktop + install_launcher.sh):
                              rofpalys app = the window with the logo and the GUI / CLI switch;  rofpalys install also puts the icon in the application menu and on the
                              Desktop (Linux and Termux desktops; on Termux the menu entry goes to $PREFIX/share/applications, where the XFCE menu looks);  rofpalys app install
                              shows exactly where everything went;  rofpalys app remove takes it away again.  Those four old files are not needed any more.

NEW IN 5.11 (languages)     the icon opens the GUI at once; [GUI | CLI] under the name ROFPALYS in the window and  7y  in the terminal switch screens and keep the song.
                              ONE language for everything: rofpalys_i18n.py (+ rofpalys_i18n_<id|zh|de|ja|ru>.py, one catalogue each) - English, Indonesian, Chinese,
                              German, Japanese, Russian: window, terminal, statistics, remote page, reports.  Language in the menu or  rofpalys lang CODE  (rofpalys lang check).
                              rofpalys_lyrictrans.py = a translation under every lyric line in the language you chose (machine translation by free online services,
                              needs internet, sends the lyric text to them; switch: the "..." menu / Settings / key G in the terminal; rofpalys lang test CODE).
                              rofpalys_switch.py = the GUI <-> CLI hand-over (song, second, paused or playing).

NEW IN 5.13 (Spotify-like)  the library is a set of pages: chips Home | Songs | Mix | Artists | Playlists | Favorites; Songs / Mix / Artists / Playlists are square cards; an artist
                              opens an artist page (popular songs, albums, "Appears on"); a playlist page with a photo, "Add to this playlist" (search, recommended songs),
                              "Save in" and "Name your playlist".  Sidebar: Home, Favorites, Visualizer, Queue, Now Playing, Statistics, Settings (it folds to icons).
                              The "..." button is gone: everything is in the Settings page (Playback, Sound, Library, Lyrics, Appearance, Language, Tools, Data, About).
                              Home has Made for you / Suggested / Most played / Recently added and a footer.  Now Playing: a three-dot menu (Add to playlist, Add to Queue,
                              Open Queue, Open album, View artist), a bigger square cover.  Sound Studio (the equalizer button): knobs for bass / treble / gain, 5 band
                              equalizer, speed, pitch, reverb, stereo width, 8D, 11 voice characters (robot, man, woman, child, monster, alien, ghost, radio, megaphone,
                              underwater), presets; rofpalys ctl fx|voice|bass|treble|pitch|width|8d.  Only music in Termux's own storage is scanned (Settings > Library).
                              Modern is the default look.  rofpalys install lyric = one command for all the lyric downloaders.
                              rofpalys_gui_browse.py (pages) / _dialogs.py (dialogs, sheets) / _settings.py (the Settings page) are new feature files.

NEW IN 5.12 (home page)     the Home tab of the library is a page of cards now: banner "Welcome to RofPalys" with Play Now, Now Playing card, Quick Access (play, liked songs,
                              playlists, top charts), Recently Played, Your Playlists, Top Artists.  Three layouts - Dashboard / Showcase / List (the old list) -
                              from the Look window (F6), Settings, the "..." menu or key F8.  Colours, corners and type stay those of Classic / Modern / Cyberpunk.
                              rofpalys_gui_home.py = the page;  the tabs of the library got icons in the looks that show icons.

THE FOLDER TREE (5.10)      the files can lie flat in one folder (as before) or in the tidy tree below; the launcher finds them either way, checks them, and installs
                              them flat into the program folder.  rofpalys organize  builds the tree from the loose files (copies; --move removes the loose copies).
                                anrofty_rofpalys/
                                  rofpalys_center/            rofpalys.py  (this file: the parent)
                                  rofpalys_system/            rofpalys_control, _engine, _tui, _lyrics, _insight, _switch, _lyrictrans
                                  rofpalys_gui_center/        rofpalys_gui, rofpalys_gui_base
                                  rofpalys_gui_system/        rofpalys_gui_<name>: effects, lyrics, lyricview, playlists, queue, sleep, stats, stats_charts, template,
                                                              theme, palette, mixes, rewind, goals, remote ... and every feature file you add
                                  cyrokayAI/                  rofpalys_CyroKayAI_<name>: clock, ears, learn, lyric, memory, providers, text, turbo, view, warp
                                  rofpalys_analytics/         rofpalys_analytics, _analytics_calc, _analytics_text
                                  rofpalys_language/          rofpalys_i18n, rofpalys_i18n_id / _zh / _de / _ja / _ru  (the catalogues)
                                  rofpalys_additional_media/  alarm, effects, library, media, playlists, queue, sleep, spectrum, stats, theme
                              A file that is not in the table goes by its name (rofpalys_gui_* -> rofpalys_gui_system, rofpalys_CyroKayAI_* -> cyrokayAI, ...). New folders
                              and files are fine: the launcher looks in every sub-folder of the tree.

Add a feature = add one file:  copy rofpalys_gui_template.py to rofpalys_gui_<name>.py (in rofpalys_gui_system/ or next to this file), edit it, then  python rofpalys.py install.
Nothing else has to change: the launcher discovers the file, checks it (its last line must be  # END-OF-FILE <its name>), installs it, and the
GUI loads it by itself.  List everything with  rofpalys features ,  check completeness with  rofpalys verify .
"""
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.request

VERSION = "5.13.0"
REPO_RAW = "https://raw.githubusercontent.com/rofpalys-nagiryu/rofpalys-/main/"
SELF = os.path.realpath(__file__)
MODULES = ("rofpalys_library.py", "rofpalys_sleep.py", "rofpalys_lyrics.py", "rofpalys_CyroKayAI_ears.py", "rofpalys_CyroKayAI_text.py", "rofpalys_CyroKayAI_turbo.py", "rofpalys_CyroKayAI_memory.py", "rofpalys_CyroKayAI_providers.py", "rofpalys_CyroKayAI_warp.py",
           "rofpalys_CyroKayAI_learn.py", "rofpalys_CyroKayAI_clock.py", "rofpalys_CyroKayAI_view.py", "rofpalys_CyroKayAI_lyric.py", "rofpalys_queue.py", "rofpalys_effects.py", "rofpalys_spectrum.py", "rofpalys_stats.py",
           "rofpalys_playlists.py", "rofpalys_alarm.py", "rofpalys_control.py", "rofpalys_engine.py", "rofpalys_media.py", "rofpalys_tui.py", "rofpalys_i18n.py", "rofpalys_switch.py",
           "rofpalys_gui_base.py", "rofpalys_gui.py")        # REQUIRED files. Any other rofpalys_*.py (e.g. rofpalys_gui_playlists.py) is a feature file: found, checked and installed by itself
SUPPORT = ("rofpalys_theme.py", "rofpalys_analytics.py", "rofpalys_analytics_calc.py", "rofpalys_analytics_text.py", "rofpalys_gui_stats_charts.py", "rofpalys_insight.py",
           "rofpalys_i18n_id.py", "rofpalys_i18n_zh.py", "rofpalys_i18n_de.py", "rofpalys_i18n_ja.py", "rofpalys_i18n_ru.py", "rofpalys_lyrictrans.py")      # optional: the player starts without them (a missing language file = that language shows English)
HOME = os.path.expanduser("~")
PREFIX = os.environ.get("PREFIX", "")
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.txt"
HELP = """Rofpalys %s - music player for Termux, Linux, macOS and Windows   (GPL-3.0-or-later)

  rofpalys                      terminal UI (whole library)
  rofpalys FILE|FOLDER|M3U ...  play songs from ANYWHERE (they join the list)
  rofpalys gui [FILE ...]       graphical UI with cover art, video and lyrics (needs a display; Termux: python-tkinter + X11/VNC)
  rofpalys app [--mode gui|cli] [--now]   the app window with the Rofpalys logo: choose GUI or CLI and start (--now starts at once, no window)
                                the app ICON opens the window player (GUI) at once; its right-click menu has GUI, CLI and the chooser.  GUI: the [GUI | CLI] buttons under the
                                name ROFPALYS switch to the terminal; terminal: type 7y to come back - the song carries on at the same second
  rofpalys app install|remove   put the Rofpalys icon in the application menu and on the Desktop / take it away (rofpalys install does it too; Linux)
  rofpalys media [reset]        show / delete the downloaded cover art and video cache
  rofpalys scan                 scan home + phone storage and print what was found
  rofpalys yt URL               download audio with yt-dlp and play it
  rofpalys doctor               check players, storage access, tools; suggests fixes
  rofpalys integrate            Termux: share a song/link from any app -> plays here; shortcuts for the Termux:Widget
  rofpalys ctl COMMAND          steer the running player: next, prev, toggle, vol +5, seek +10, sleep 30, queue FILE, fx slowed, lyrics sync ...   (rofpalys ctl help)
  rofpalys lyrics FILE ...      CyroKayAI: who made it -> internet -> listen -> fetch from Musixmatch -> force the lyrics onto the real recording (🎶 / 🎵 for the melody)
  rofpalys lyrics melody|analyze|timeline|cut|all|bench|learn|forget|view|source|providers|reset|selftest   (rofpalys lyrics help)
  rofpalys lyrics source [musixmatch|all]   MUSIXMATCH is the standard (default: the only source); "all" also asks the other downloaders + LRCLIB / YouTube / lyrics.ovh
  rofpalys lyrics providers [install]   the downloaders behind it: musixmatch -> syncedlyrics -> lrcdl -> lyriq -> librelyrics (+ the built-in safety net in "all" mode)
  rofpalys now [--json]         what is playing right now
  rofpalys stats [PAGE]         statistics in the terminal: overview, songs, artists, days, hours, heatmap, log, records, quality, verify, export ...   (rofpalys stats help)
  rofpalys lang [CODE]          the language of EVERYTHING (window, terminal, statistics, lyric translation): en id zh de ja ru;  rofpalys lang check | lang test [CODE]
  rofpalys theme [NAME]         the look: classic (brown) | modern | cyberpunk - an open window follows at once (F6 in the window switches too)
  rofpalys daemon               player without a window: notification buttons, alarms and ctl keep working in the background
  rofpalys install [-y]         put all files in place by itself (modules, command, permissions) and check everything; works from loose files AND from the folder tree
  rofpalys install lyric        ONE command that installs every lyric downloader (syncedlyrics = Musixmatch, lrcdl, lyriq, librelyrics) and shows the result   (also: install lyrics)
  rofpalys organize [FOLDER] [--move]   put the loose rofpalys_*.py files into the tidy tree  FOLDER/anrofty_rofpalys/<group>/  (copies; --move removes the loose copies)
  rofpalys verify               check that every installed file is complete (finds a paste that was cut off)
  rofpalys features             list the core files and the feature files (rofpalys_gui_<name>.py) and which are on
  rofpalys reset [-y] [--keep-favorites] [--keep-stats]   DEEP reset: delete everything Rofpalys stored (settings, favorites, lyrics + CyroKayAI measurements, caches, statistics history...); never your songs
  rofpalys update               fetch the newest files from GitHub
  rofpalys --license | --version | --help
""" % VERSION


def libdir():
    """Where the 4 module files live: next to this file, $ROFPALYS_HOME, $PREFIX/lib/rofpalys, ~/.local/share/rofpalys."""
    cands = [os.environ.get("ROFPALYS_HOME"), os.path.dirname(SELF), os.path.join(PREFIX, "lib", "rofpalys") if PREFIX else None,
             os.path.join(HOME, ".local", "share", "rofpalys")]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "rofpalys_engine.py")):
            return c
    return None


def install_dir():
    if PREFIX and os.access(os.path.join(PREFIX, "lib"), os.W_OK):
        return os.path.join(PREFIX, "lib", "rofpalys")
    return os.path.join(HOME, ".local", "share", "rofpalys")


def make_executable(path):
    try:
        mode = os.stat(path).st_mode
        if (mode & 0o111) != 0o111:
            os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return True
    except OSError:
        pass
    return False


def fix_permissions(d):
    """The equivalent of: chmod +x $PREFIX/bin/rofpalys  and the module files. Runs on every start (cheap)."""
    changed = [p for p in [SELF] + ([os.path.join(d, m) for m in MODULES] if d else []) if os.path.isfile(p) and make_executable(p)]
    if changed and "--quiet" not in sys.argv:
        print("[rofpalys] permissions set (chmod +x): " + ", ".join(os.path.basename(p) for p in changed))


def fetch(name, timeout=25):
    req = urllib.request.Request(REPO_RAW + name, headers={"User-Agent": "Rofpalys-updater/" + VERSION})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ------------------------------------------------------------------ automatic install: finds the downloaded / pasted files and puts them in place
def bin_path():
    b = os.path.join(PREFIX, "bin") if PREFIX else ""
    if b and os.path.isdir(b) and os.access(b, os.W_OK):
        return os.path.join(b, "rofpalys")
    return os.path.join(HOME, ".local", "bin", "rofpalys")


def is_installed():
    return os.path.realpath(SELF) == os.path.realpath(bin_path())


_NAME = re.compile(r"^(rofpalys(?:_[A-Za-z0-9_]*[A-Za-z0-9])?)(?:[ _-]?\(\d+\))?\.py$")        # rofpalys.py, rofpalys_<anything>.py (capitals allowed: rofpalys_CyroKayAI_lyric.py), and copies like "name (1).py"

# MANIFEST-BEGIN (written by the release script: lines, bytes, sha256[:16] of each module of this release)
MANIFEST = {
    'rofpalys_CyroKayAI_clock.py': (360, 17645, '656b01e37d271021'),
    'rofpalys_CyroKayAI_ears.py': (663, 29054, 'b37091b9da583b3e'),
    'rofpalys_CyroKayAI_learn.py': (327, 17038, 'b1edc1129a4480e5'),
    'rofpalys_CyroKayAI_lyric.py': (1746, 92930, '062a3709080415e7'),
    'rofpalys_CyroKayAI_memory.py': (261, 10439, 'aefeaa07c9b2a724'),
    'rofpalys_CyroKayAI_providers.py': (1041, 50859, '54059093106dcf12'),
    'rofpalys_CyroKayAI_text.py': (109, 5352, 'ffbe6e488ca586fb'),
    'rofpalys_CyroKayAI_turbo.py': (193, 7473, '1234a55bdd5e63fd'),
    'rofpalys_CyroKayAI_view.py': (421, 20503, 'f023a0924efcf347'),
    'rofpalys_CyroKayAI_warp.py': (126, 7507, 'fb6b411a2c8b85d3'),
    'rofpalys_alarm.py': (140, 4421, 'c8a0cdb6444d9807'),
    'rofpalys_analytics.py': (1471, 66986, '637fa3070dbdd3a9'),
    'rofpalys_analytics_calc.py': (644, 28716, '1b31b645f7a9ecc6'),
    'rofpalys_analytics_text.py': (475, 30551, 'b54e9136b788f60a'),
    'rofpalys_control.py': (386, 16027, '3b53ed18e4162f4c'),
    'rofpalys_effects.py': (291, 12739, '97ae3ea27c4e8df7'),
    'rofpalys_engine.py': (1298, 54207, '7a7925d0038bb252'),
    'rofpalys_gui.py': (2020, 94482, '23a0fe6721c06528'),
    'rofpalys_gui_base.py': (1101, 66990, '91d5af2950eb2825'),
    'rofpalys_gui_browse.py': (714, 36385, 'c4a38f3fe4b1cb71'),
    'rofpalys_gui_dialogs.py': (202, 9219, '5867c6c740b7918e'),
    'rofpalys_gui_effects.py': (522, 26177, 'b75be08aeb511138'),
    'rofpalys_gui_goals.py': (386, 20512, 'e5a16dec4ee48788'),
    'rofpalys_gui_home.py': (765, 41752, '9071bf7c490340fb'),
    'rofpalys_gui_lyrics.py': (271, 13693, '126efbdbc1fe4a15'),
    'rofpalys_gui_lyricview.py': (377, 15539, '7df3d28da6fe8a82'),
    'rofpalys_gui_mixes.py': (233, 11137, '6d086996b24ba964'),
    'rofpalys_gui_palette.py': (561, 26388, 'b1740f1be06b4cb1'),
    'rofpalys_gui_playlists.py': (598, 25210, '7a2d9bb5a9dc00b5'),
    'rofpalys_gui_queue.py': (133, 4961, 'dec0fe3de8b65a9a'),
    'rofpalys_gui_remote.py': (852, 43295, 'cc7a1638a309bff3'),
    'rofpalys_gui_rewind.py': (481, 29247, 'e35208c4cacedcfb'),
    'rofpalys_gui_settings.py': (525, 28794, '0aa206f117b181d5'),
    'rofpalys_gui_sleep.py': (233, 12073, 'bdfe9d9a22a407e0'),
    'rofpalys_gui_stats.py': (981, 51123, '31269bf39b963823'),
    'rofpalys_gui_stats_charts.py': (258, 13415, 'a0f6d5b5fd57bae6'),
    'rofpalys_gui_template.py': (41, 2864, 'c9e47c595cda7d0c'),
    'rofpalys_gui_theme.py': (297, 16170, '6fca8bf6229817a0'),
    'rofpalys_i18n.py': (250, 11149, 'a83b59a706c6f385'),
    'rofpalys_i18n_de.py': (842, 52736, 'fc167a7657888c3d'),
    'rofpalys_i18n_id.py': (842, 50114, '4a19647059d5eedd'),
    'rofpalys_i18n_ja.py': (842, 58567, 'd2eb2275d42b3778'),
    'rofpalys_i18n_ru.py': (842, 68379, 'f06ce30acac59edc'),
    'rofpalys_i18n_zh.py': (842, 49861, '87ee90b3f5538f55'),
    'rofpalys_insight.py': (188, 5848, '14a680502f3e1fea'),
    'rofpalys_library.py': (418, 17898, '52aa722f9a82227b'),
    'rofpalys_lyrics.py': (466, 19752, '8305cfa3756aebd1'),
    'rofpalys_lyrictrans.py': (461, 18466, 'b3d80c8b6012dbc8'),
    'rofpalys_media.py': (775, 27329, 'ff82fcce1014172c'),
    'rofpalys_playlists.py': (276, 7986, 'de02c171959ae128'),
    'rofpalys_queue.py': (88, 2404, 'eda3a36ef052db1a'),
    'rofpalys_sleep.py': (228, 9812, 'd97ce01c93cd0e44'),
    'rofpalys_spectrum.py': (140, 4719, '36bcf8e6d9634dd3'),
    'rofpalys_stats.py': (128, 4436, '081c18568fa4b7b7'),
    'rofpalys_switch.py': (165, 7081, '50e965c00cfb3d44'),
    'rofpalys_theme.py': (532, 26576, 'f5877e892670adfa'),
    'rofpalys_tui.py': (781, 30862, '7b27d0103aeaba49'),
}
# MANIFEST-END


LEGACY_APP_FILES = ("rofpalys_launcher.py", "rofpalys_logo.svg", "rofpalys_launcher.desktop", "install_launcher.sh")      # the four loose files of the old icon launcher: all inside this file now


# ------------------------------------------------------------------ the tidy folder tree (optional: loose files in one folder work as before)
ROOT_NAME = "anrofty_rofpalys"
ROOT_NAMES = (ROOT_NAME, "anfty_rofpalys")                 # the second spelling is accepted too (it was typed that way in the first sketch of the tree)
LAYOUT = {                                                 # folder -> the files in it; a file that is not listed goes by its name (see folder_of)
    "rofpalys_center": ("rofpalys.py",),
    "rofpalys_system": ("rofpalys_control.py", "rofpalys_engine.py", "rofpalys_tui.py", "rofpalys_lyrics.py", "rofpalys_insight.py", "rofpalys_switch.py", "rofpalys_lyrictrans.py"),
    "rofpalys_gui_center": ("rofpalys_gui.py", "rofpalys_gui_base.py"),
    "rofpalys_gui_system": ("rofpalys_gui_effects.py", "rofpalys_gui_lyrics.py", "rofpalys_gui_lyricview.py", "rofpalys_gui_playlists.py", "rofpalys_gui_queue.py",
                            "rofpalys_gui_sleep.py", "rofpalys_gui_stats.py", "rofpalys_gui_stats_charts.py", "rofpalys_gui_template.py", "rofpalys_gui_theme.py",
                            "rofpalys_gui_palette.py", "rofpalys_gui_mixes.py", "rofpalys_gui_rewind.py", "rofpalys_gui_goals.py", "rofpalys_gui_remote.py", "rofpalys_gui_home.py",
                            "rofpalys_gui_browse.py", "rofpalys_gui_dialogs.py", "rofpalys_gui_settings.py"),
    "cyrokayAI": ("rofpalys_CyroKayAI_clock.py", "rofpalys_CyroKayAI_ears.py", "rofpalys_CyroKayAI_learn.py", "rofpalys_CyroKayAI_lyric.py", "rofpalys_CyroKayAI_memory.py",
                  "rofpalys_CyroKayAI_providers.py", "rofpalys_CyroKayAI_text.py", "rofpalys_CyroKayAI_turbo.py", "rofpalys_CyroKayAI_view.py", "rofpalys_CyroKayAI_warp.py"),
    "rofpalys_analytics": ("rofpalys_analytics.py", "rofpalys_analytics_calc.py", "rofpalys_analytics_text.py"),
    "rofpalys_language": ("rofpalys_i18n.py", "rofpalys_i18n_id.py", "rofpalys_i18n_zh.py", "rofpalys_i18n_de.py", "rofpalys_i18n_ja.py", "rofpalys_i18n_ru.py"),
    "rofpalys_additional_media": ("rofpalys_alarm.py", "rofpalys_effects.py", "rofpalys_library.py", "rofpalys_media.py", "rofpalys_playlists.py", "rofpalys_queue.py",
                                  "rofpalys_sleep.py", "rofpalys_spectrum.py", "rofpalys_stats.py", "rofpalys_theme.py"),
}


def folder_of(name):
    """The folder of the tree a file belongs in."""
    for folder, files in LAYOUT.items():
        if name in files:
            return folder
    low = name.lower()
    if low.startswith("rofpalys_cyrokayai_"):
        return "cyrokayAI"
    if low.startswith("rofpalys_analytics"):
        return "rofpalys_analytics"
    if low.startswith("rofpalys_i18n"):
        return "rofpalys_language"
    if low.startswith("rofpalys_gui_"):
        return "rofpalys_gui_system"
    return "rofpalys_system"


def search_dirs():
    """The folders where downloaded / pasted files are looked for (real paths, no duplicates, only those that exist)."""
    dirs = [os.path.dirname(SELF), os.getcwd(), HOME, os.path.join(HOME, "storage", "downloads"), os.path.join(HOME, "storage", "shared", "Download"),
            os.path.join(HOME, "Downloads")]
    seen, out = set(), []
    for d in dirs:
        d = os.path.realpath(d)
        if d not in seen and os.path.isdir(d):
            seen.add(d)
            out.append(d)
    return out


def project_roots():
    """The folder trees (anrofty_rofpalys/ ...) that can be seen from where files are looked for: the one this file lies in, and any in the search folders."""
    roots, seen = [], set()

    def add(r):
        r = os.path.realpath(r)
        if r not in seen and os.path.isdir(r):
            seen.add(r)
            roots.append(r)
    for d in search_dirs():
        cur = d
        for _ in range(4):                                                  # inside the tree: .../anrofty_rofpalys/rofpalys_center
            b = os.path.basename(cur)
            if b in ROOT_NAMES or b in LAYOUT:
                add(cur if b in ROOT_NAMES else os.path.dirname(cur))
                break
            up = os.path.dirname(cur)
            if up == cur:
                break
            cur = up
        try:
            entries = sorted(os.listdir(d))
        except OSError:
            continue
        for e in entries:                                                   # a tree next to the loose files (any name for the root folder)
            p = os.path.join(d, e)
            if e in ROOT_NAMES or os.path.isdir(os.path.join(p, "rofpalys_center")):
                add(p)
            elif "rofpalys" in e.lower() or "anrofty" in e.lower():         # an unpacked zip often has a wrapper folder around the tree
                try:
                    for c in sorted(os.listdir(p)):
                        if c in ROOT_NAMES or os.path.isdir(os.path.join(p, c, "rofpalys_center")):
                            add(os.path.join(p, c))
                except OSError:
                    pass
    return roots


def source_dirs():
    """search_dirs() plus every folder of the trees found (the root and each sub-folder: new folders are fine)."""
    out, seen = [], set()

    def add(d):
        d = os.path.realpath(d)
        if d not in seen and os.path.isdir(d):
            seen.add(d)
            out.append(d)
    for d in search_dirs():
        add(d)
    for r in project_roots():
        add(r)
        try:
            subs = sorted(os.listdir(r))
        except OSError:
            continue
        for sdir in subs:
            if not sdir.startswith("."):
                add(os.path.join(r, sdir))
    return out


def legacy_app_files():
    """Old launcher files lying around (they are not used any more) - [path, ...]."""
    out = []
    for d in search_dirs():
        try:
            out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if re.sub(r"[ _-]?\(\d+\)(?=\.)", "", f) in LEGACY_APP_FILES]
        except OSError:
            pass
    return out


def find_sources():
    """{'rofpalys_gui.py': [(mtime, path), ...newest first]} - every copy found next to this script, in the current folder, home and Downloads, and in the folder tree."""
    found = {}
    for d in source_dirs():
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for f in names:
            m = _NAME.match(f)
            if not m or (m.group(1) + ".py") in LEGACY_APP_FILES:        # rofpalys_launcher.py is part of this file now: never treated as a feature file
                continue
            path = os.path.join(d, f)
            try:
                mt = os.path.getmtime(path)
            except OSError:
                continue
            found.setdefault(m.group(1) + ".py", []).append((mt, path))
    for k in found:
        found[k].sort(reverse=True)
    return found


def inspect(path, name):
    """('ok' | 'modified' | 'cut' | 'broken', explanation).
    cut = the file stops early (typical when a long paste into nano is cut off) - it may still be valid Python, so it is detected by
    the END-OF-FILE marker and by the line count of the release."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return "broken", str(e)
    lines, sha = data.count(b"\n"), hashlib.sha256(data).hexdigest()[:16]
    exp = MANIFEST.get(name)
    if exp and sha == exp[2]:
        return "ok", ""
    if exp and hashlib.sha256(data.replace(b"\r\n", b"\n").rstrip() + b"\n").hexdigest()[:16] == exp[2]:
        return "ok", ""                                                        # only blank lines at the end / Windows line ends differ: copying and downloading add those
    try:
        compile(data, path, "exec")
    except SyntaxError as e:
        return "broken", "syntax error at line %s - the file has a pasting mistake or is cut off (%d lines%s)" % (e.lineno, lines, (", release: %d" % exp[0]) if exp else "")
    if (b"END-OF-FILE " + name.encode()) not in data.rstrip()[-300:]:
        return "cut", "the file stops early: %d lines%s - the paste was cut off" % (lines, (", the release has %d" % exp[0]) if exp else "")
    if exp:
        return "modified", "differs from this release (%d lines, release: %d) - edited or from another version" % (lines, exp[0])
    return "ok", ""


def _put(src, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dest)
    make_executable(dest)


def read_feature_meta(path):
    """FEATURE = {...} of a feature file, read WITHOUT running it (None if there is none)."""
    import ast
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            tree = ast.parse(f.read())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FEATURE" for t in node.targets):
                return ast.literal_eval(node.value)
    except Exception:
        pass
    return None


def cmd_features(d):
    """What is installed: the required core files and every feature file (rofpalys_gui_<name>.py ...) with its title, version and state."""
    if d is None:
        print("Rofpalys is not installed here.  Run:  python rofpalys.py install")
        return 1
    print("Rofpalys %s - program folder: %s\n" % (VERSION, d))
    print("CORE FILES (required)")
    for n in MODULES:
        st = "ok" if os.path.isfile(os.path.join(d, n)) and inspect(os.path.join(d, n), n)[0] in ("ok", "modified") else "PROBLEM"
        print("  %-8s %s" % (st, n))
    print("\nSUPPORT FILES (optional: without them there are no statistics and only the Classic look)")
    for n in SUPPORT:
        have = os.path.isfile(os.path.join(d, n))
        st = inspect(os.path.join(d, n), n)[0] if have else "absent"
        print("  %-8s %s" % ({"ok": "ok", "modified": "ok", "absent": "absent", "cut": "CUT OFF", "broken": "CUT OFF"}[st], n))
    print("\nFEATURE FILES (optional: add a file here and it is used the next time you start the program)")
    feats = sorted(f for f in os.listdir(d) if re.match(r"^rofpalys_[A-Za-z0-9_]+\.py$", f) and f not in MODULES and f not in SUPPORT)
    for f in feats:
        meta = read_feature_meta(os.path.join(d, f)) or {}
        st, why = inspect(os.path.join(d, f), f)
        state = "CUT OFF" if st in ("cut", "broken") else ("off" if meta.get("enabled") is False else "on")
        print("  %-8s %-28s v%-5s %s" % (state, f, meta.get("version", "?"), meta.get("title", "(no FEATURE info)")))
    if not feats:
        print("  (none)")
    print("\nAdd a feature: copy rofpalys_gui_template.py to rofpalys_gui_<name>.py, edit it, run  python ~/rofpalys.py install")
    return 0


def cmd_verify(d):
    """Are the installed files complete? (Catches a paste that was cut off.)"""
    if d is None:
        print("Rofpalys: no installed modules found.  Run:  python rofpalys.py install")
        return 1
    bad = 0
    print("Checking %s" % d)
    extras = sorted({f for f in os.listdir(d) if re.match(r"^rofpalys_[A-Za-z0-9_]+\.py$", f)} | set(MANIFEST)) if os.path.isdir(d) else []
    for name in list(MODULES) + [n for n in extras if n not in MODULES]:
        p = os.path.join(d, name)
        if not os.path.isfile(p):
            if name in MODULES:
                print("  MISSING   %s" % name)
                bad += 1
            else:
                print("  absent    %s   (optional %s file - not installed)" % (name, "support" if name in SUPPORT else "feature"))
            continue
        st, why = inspect(p, name)
        print("  %-9s %s%s%s" % ({"ok": "ok", "modified": "changed", "cut": "CUT OFF", "broken": "BROKEN"}[st], name, "" if name in MODULES else ("   (support)" if name in SUPPORT else "   (feature)"), ("   " + why) if why else ""))
        bad += st in ("cut", "broken")
    if bad:
        print("\nFix: download the marked file(s) again (tap the file card, do not paste), put it in Downloads or ~, then run:  python ~/rofpalys.py install")
    return 1 if bad else 0


def cmd_install(args=(), auto=False):
    """Does by itself what used to be typed by hand: move the module files into the lib folder, install the command into bin, chmod +x.
    Every file is checked first; a cut-off copy is never installed (an older complete copy is used if there is one)."""
    yes = "-y" in args or "--yes" in args
    found, target, bp = find_sources(), install_dir(), bin_path()
    problems, done, warns = [], [], []
    names = list(MODULES) + sorted(n for n in found if n not in MODULES and n != "rofpalys.py")      # feature files are picked up automatically
    for name in names:
        chosen, errs = None, []
        for mt, src in found.get(name, []):
            st, why = inspect(src, name)
            if st in ("ok", "modified"):
                chosen = src
                if st == "modified":
                    warns.append("%s: %s" % (name, why))
                break
            errs.append("%s: %s" % (src, why))
        if chosen:
            dest = os.path.join(target, name)
            if os.path.realpath(chosen) != os.path.realpath(dest):
                _put(chosen, dest)
                done.append(name)
                if os.path.dirname(os.path.realpath(chosen)) == os.path.realpath(HOME):      # like the old `mv ~/rofpalys_*.py ...`
                    try:
                        os.remove(chosen)
                    except OSError:
                        pass
        else:
            have = os.path.join(target, name)
            if errs:
                problems.append("%s - %s" % (name, "; ".join(errs)))
            elif not os.path.isfile(have) and name in MODULES:
                problems.append("%s: not found (looked in %s, ~, Downloads)" % (name, os.path.dirname(SELF)))
            if os.path.isfile(have) and errs:
                st, why = inspect(have, name)
                if st in ("cut", "broken"):
                    problems.append("%s: the INSTALLED copy is also bad (%s)" % (name, why))
    cands = list(found.get("rofpalys.py", []))
    if SELF.endswith(".py") and not is_installed():
        cands.append((os.path.getmtime(SELF), SELF))
    for mt, src in sorted(cands, reverse=True):
        st, why = inspect(src, "rofpalys.py")
        if st in ("ok", "modified"):
            if os.path.realpath(src) != os.path.realpath(bp):
                _put(src, bp)
                done.append("rofpalys (command)")
            break
        problems.append("rofpalys.py (%s): %s" % (src, why))
    make_executable(bp)
    for m in names:
        make_executable(os.path.join(target, m))
    if done:
        print("[rofpalys] installed: " + ", ".join(done))
        print("           modules -> %s\n           command -> %s" % (target, bp))
    for w in warns:
        print("[rofpalys] note: " + w)
    menu = app_install(quiet=True) if os.path.isfile(bp) else []        # the icon in the application menu (Linux / Termux desktop): whatever else is wrong, it still starts the window
    if menu:
        print("[rofpalys] app icon: %s  (details: rofpalys app install;  take it away: rofpalys app remove)" % ", ".join(menu))
    old = legacy_app_files()
    if old:
        print("[rofpalys] note: the icon launcher is part of rofpalys.py now. These old files are not used any more and can be deleted:\n           " + "\n           ".join(old))
    if problems:
        print("[rofpalys] PROBLEMS - these files are incomplete. Download them again (tap the file card instead of pasting), then run  python rofpalys.py install :")
        for pr in problems:
            print("   - " + pr)
        return 1
    if not done and not menu:
        print("[rofpalys] everything is already installed and up to date.")
    if not auto:
        missing = []
        for tool, pkg in (("mpv", "mpv"), ("ffmpeg", "ffmpeg"), ("yt-dlp", "yt-dlp")):
            if not shutil.which(tool):
                missing.append(pkg)
        try:
            import tkinter  # noqa: F401
        except ImportError:
            missing.append("python-tkinter")
        if missing and shutil.which("pkg"):
            ok = yes
            if not yes:
                try:
                    ok = input("Install missing tools (%s) with pkg now? [Y/n] " % " ".join(missing)).strip().lower() in ("", "y", "yes")
                except (EOFError, KeyboardInterrupt):
                    ok = False
            if ok:
                subprocess.call(["pkg", "install", "-y"] + missing)
        elif missing:
            print("[rofpalys] optional tools missing: %s" % ", ".join(missing))
        sys.path.insert(0, target)
        cmd_doctor(target)
    elif shutil.which("pkg"):
        print("           (tools like mpv/ffmpeg/yt-dlp:  rofpalys install   - it offers to install them)")
    return 0

def cmd_install_lyric(args=()):
    """rofpalys install lyric  (also: lyrics, lirik): one command that installs every lyric downloader of CyroKayAI and then shows the result.
    Musixmatch (through the syncedlyrics package) is the standard source; lrcdl, lyriq and librelyrics are the helpers that "rofpalys lyrics source all" can add.
    Packages already there are left alone; a Python that is too old for one of them only skips that one."""
    d = libdir()
    if d is None or not os.path.isfile(os.path.join(d, "rofpalys_CyroKayAI_providers.py")):
        print("rofpalys_CyroKayAI_providers.py is missing.  Download it again, put it in Downloads or ~, then run:  python ~/rofpalys.py install")
        return 1
    sys.path.insert(0, d)
    try:
        import rofpalys_CyroKayAI_providers as PV
    except ImportError as e:
        print("rofpalys_CyroKayAI_providers.py could not be loaded: %s" % (e,))
        return 1
    flags = [a for a in args if a.startswith("--")]
    only = [a for a in args if not a.startswith("-") and a in PV.DEFAULT_ORDER]
    names = only or list(PV.DEFAULT_ORDER)
    print("Rofpalys %s - lyric downloaders: %s\n" % (VERSION, " -> ".join(names)))
    res = PV.install(names, flags, lambda m: print("  " + m))
    for n, (ok, msg) in res.items():
        print("  %-13s %s  %s" % (n, "ok    " if ok else "FAILED", msg))
    print("\n" + PV.format_status("id" if os.environ.get("LANG", "").lower().startswith("id") else "en"))
    if not all(ok for ok, _ in res.values()):
        print("\nSomething could not be installed.  On a system-managed Python add:  rofpalys install lyric --break-system-packages")
    else:
        print("\nDone.  Musixmatch is the standard source.  To let the other downloaders help as well:  rofpalys lyrics source all")
    return 0 if all(ok for ok, _ in res.values()) else 1


def cmd_organize(args):
    """rofpalys organize [FOLDER] [--move]: the loose rofpalys_*.py files -> FOLDER/anrofty_rofpalys/<group>/ (FOLDER = here). Copies the newest COMPLETE copy of every
    file (a cut-off copy is never used); --move then removes the loose copies that are identical to what was put in the tree. The running file is never removed."""
    move = "--move" in args
    rest = [a for a in args if not a.startswith("-")]
    base = os.path.realpath(os.path.expanduser(rest[0])) if rest else os.getcwd()
    if os.path.basename(base) in ROOT_NAMES:
        root = base
    else:
        root = os.path.join(base, ROOT_NAME)
    found = find_sources()
    names = sorted(n for n in found if n != "rofpalys.py") + (["rofpalys.py"] if "rofpalys.py" in found or SELF.endswith(".py") else [])
    if not names:
        print("[rofpalys] no rofpalys_*.py files found (looked in: %s)" % ", ".join(source_dirs()))
        return 1
    placed, same, bad, removed = {}, 0, [], 0
    for name in names:
        cands = list(found.get(name, []))
        if name == "rofpalys.py" and SELF.endswith(".py") and os.path.isfile(SELF):
            cands.append((os.path.getmtime(SELF), SELF))
        chosen, errs = None, []
        for mt, src in sorted(cands, reverse=True):
            st, why = inspect(src, name)
            if st in ("ok", "modified"):
                chosen = src
                break
            errs.append("%s: %s" % (src, why))
        if not chosen:
            bad.append("%s - %s" % (name, "; ".join(errs) or "not found"))
            continue
        folder = folder_of(name)
        dest = os.path.join(root, folder, name)
        if os.path.realpath(chosen) == os.path.realpath(dest):
            same += 1
        else:
            _put(chosen, dest)
            placed.setdefault(folder, []).append(name)
        if move:
            try:
                with open(dest, "rb") as f:
                    want = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                continue
            for mt, src in cands:
                if os.path.realpath(src) in (os.path.realpath(dest), os.path.realpath(SELF)) or os.path.realpath(os.path.dirname(src)).startswith(os.path.realpath(root)):
                    continue
                try:
                    with open(src, "rb") as f:
                        if hashlib.sha256(f.read()).hexdigest() == want:
                            os.remove(src)
                            removed += 1
                except OSError:
                    pass
    total = sum(len(v) for v in placed.values())
    print("[rofpalys] folder tree: %s" % root)
    for folder in LAYOUT:
        if folder in placed:
            print("  %-27s %2d new   %s" % (folder + "/", len(placed[folder]), ", ".join(n[len("rofpalys_"):-3] if n != "rofpalys.py" else n for n in placed[folder])))
    for folder in sorted(set(placed) - set(LAYOUT)):
        print("  %-27s %2d new" % (folder + "/", len(placed[folder])))
    print("[rofpalys] %d file(s) put in place, %d already there%s" % (total, same, (", %d loose copy(ies) removed" % removed) if move else ""))
    for b in bad:
        print("[rofpalys] NOT put in the tree (incomplete): " + b)
    cmd = os.path.join(root, "rofpalys_center", "rofpalys.py")
    if move and os.path.isfile(SELF) and not os.path.realpath(SELF).startswith(os.path.realpath(root) + os.sep):
        print("[rofpalys] this running file (%s) was not removed: it is the same as rofpalys_center/rofpalys.py, delete it yourself when you like" % SELF)
    print("Install / start from the tree:  python %s install" % cmd)
    return 1 if bad else 0


def start_recorder(surface):
    """Start the statistics recorder (rofpalys_analytics.py) for this program: 'gui', 'tui' or 'daemon'. Silent and harmless when the file is missing or anything goes wrong:
    the music must never depend on its statistics."""
    if os.environ.get("ROFPALYS_NO_STATS"):
        return None
    try:
        import rofpalys_analytics as AN
        import rofpalys_engine as E
        return AN.start(E, surface)
    except Exception:
        return None


def cmd_daemon(d):
    """The player without a window: the control socket, the notification buttons and the alarms keep working (start it with `nohup rofpalys daemon &`)."""
    import signal
    sys.path.insert(0, d)
    import rofpalys_alarm as AL
    import rofpalys_control as CT
    import rofpalys_engine as E
    import rofpalys_stats as ST
    E.load_favorites()
    E.load_settings()
    ST.load()
    E.refresh_playlist()
    E.scan_library_async()
    on = CT.start(E, notify=E.notify_controls)
    if not on["socket"]:
        print("Another Rofpalys is already running (the control socket is taken). Close it first, or just use:  rofpalys ctl ...")
        return 1
    start_recorder("daemon")                               # statistics: what the daemon plays and what you do through ctl and the notification buttons
    AL.start(E.alarm_fire)
    stop = []
    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *a: stop.append(1))
    print("Rofpalys daemon is running (notification buttons: %s). Steer it with:  rofpalys ctl help   |   Ctrl+C stops it." % ("on" if on["notification"] else "off"))
    print("Termux tip: run  termux-wake-lock  so Android does not put it to sleep (needed for alarms).")
    try:
        while not stop:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        AL.stop()
        CT.stop_server()
        E.shutdown()
    return 0


def cmd_reset(d, args):
    """Deep reset from the terminal. Deletes only what Rofpalys created for itself (see rofpalys_engine.reset_everything)."""
    sys.path.insert(0, d)
    import rofpalys_engine as E
    import rofpalys_library as lib
    pidf = os.path.join(lib.CACHE_DIR, "gui.pid")
    try:
        with open(pidf) as f:
            pid = int(f.read().strip() or 0)
        if pid and pid != os.getpid() and os.name != "nt":
            os.kill(pid, 0)
            print("The Rofpalys window is still open (pid %d). Close it first - otherwise it saves its old state again when it closes." % pid)
            return 1
    except (OSError, ValueError):
        pass
    keep = "--keep-favorites" in args
    keep_stats = "--keep-stats" in args
    an_dir = os.path.join(lib.CONFIG_DIR, "analytics")
    if os.path.isdir(an_dir) and not keep_stats:
        try:
            import rofpalys_analytics as AN
            if AN.status()["recording_elsewhere"]:
                print("A Rofpalys program (window, terminal player or daemon) is still open and writing statistics. Close it first.")
                return 1
        except Exception:
            pass
    targets = [p for p in (os.path.join(lib.CONFIG_DIR, n) for n in ("rof_settings.json", "gui.json", "rof_favorites.json", "theme.json")) if os.path.isfile(p)]
    size = 0
    for root, _, files in os.walk(lib.CACHE_DIR):
        size += sum(os.path.getsize(os.path.join(root, f)) for f in files if os.path.exists(os.path.join(root, f)))
    print("DEEP RESET will delete:")
    for p in targets:
        if keep and p.endswith("rof_favorites.json"):
            continue
        print("   " + p)
    print("   %s   (lyrics, CyroKayAI measurements, covers, videos, library cache - %.1f MB)" % (lib.CACHE_DIR, size / 1048576.0))
    if os.path.isdir(an_dir):
        an_size = sum(os.path.getsize(os.path.join(r_, f_)) for r_, _, fs_ in os.walk(an_dir) for f_ in fs_ if os.path.exists(os.path.join(r_, f_)))
        print("   %s   (%s - %.1f MB)" % (an_dir, "statistics history: KEPT because of --keep-stats" if keep_stats else "ALL statistics history (the tamper-evident log); keep it with --keep-stats", an_size / 1048576.0))
    print("NOT touched: your songs, your own .lrc files, the audio in Music/ROFPALys, the Rofpalys program files.")
    if not ("-y" in args or "--yes" in args):
        try:
            if input("Type RESET to continue: ").strip() != "RESET":
                print("Cancelled.")
                return 1
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 1
    removed = E.reset_everything(keep_favorites=keep)
    if os.path.isdir(an_dir) and not keep_stats:
        try:
            shutil.rmtree(an_dir)
            removed = list(removed or []) + [an_dir]
        except OSError as e:
            print("could not remove %s: %s" % (an_dir, e))
    tj = os.path.join(lib.CONFIG_DIR, "theme.json")
    if os.path.isfile(tj):
        try:
            os.remove(tj)
            removed = list(removed or []) + [tj]
        except OSError:
            pass
    print("Done: %d item(s) removed. Start Rofpalys again - it begins like the first time." % len(removed))
    return 0


def cmd_update():
    d = libdir() or install_dir()
    os.makedirs(d, exist_ok=True)
    print("Updating from", REPO_RAW)
    ok = 0
    for name in ("rofpalys.py",) + MODULES + SUPPORT:
        try:
            data = fetch(name)
            compile(data, name, "exec")                    # never install a file that is not valid Python
            if b"rofpalys" not in data.lower():
                raise ValueError("does not look like a Rofpalys file")
        except Exception as e:
            if name not in SUPPORT:                        # an optional file that is not in the repository (yet) is no news
                print("  skip %-20s %s" % (name, e))
            continue
        dest = SELF if name == "rofpalys.py" else os.path.join(d, name)
        try:
            if os.path.exists(dest):
                shutil.copy2(dest, dest + ".bak")
            with open(dest + ".part", "wb") as f:
                f.write(data)
            os.replace(dest + ".part", dest)
            make_executable(dest)
            ok += 1
            print("  ok   %s" % name)
        except OSError as e:
            print("  FAIL %-20s %s" % (name, e))
    try:                                                   # GNU license text next to the code
        data = urllib.request.urlopen(LICENSE_URL, timeout=15).read()
        with open(os.path.join(d, "COPYING"), "wb") as f:
            f.write(data)
    except Exception:
        pass
    print("%d file(s) updated. (old versions kept as *.bak)" % ok)
    return 0 if ok else 1


def cmd_license(d):
    print("Rofpalys %s - Copyright (C) 2026 rofpalys-nagiryu" % VERSION)
    print("Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).")
    print("This is free software: you may redistribute and modify it under the terms of the GPL.")
    print("There is NO WARRANTY, to the extent permitted by law.")
    print("Full text: " + LICENSE_URL)
    if d and os.path.isfile(os.path.join(d, "COPYING")):
        print("Local copy: " + os.path.join(d, "COPYING"))
    else:
        print("Get a local copy with:  rofpalys update")
    return 0


def cmd_integrate():
    """Termux: 'Share -> Termux' from any app runs ~/bin/termux-file-editor (files) and ~/bin/termux-url-opener (links)."""
    import rofpalys_library as lib
    if not lib.IS_TERMUX:
        print("integrate is for Termux only. On Linux/macOS/Windows, set Rofpalys as the 'open with' app for audio files:  rofpalys %f")
        return 1
    sh = os.path.join(PREFIX, "bin", "sh")
    binp = os.path.join(HOME, "bin")
    os.makedirs(binp, exist_ok=True)
    scripts = os.path.join(HOME, ".shortcuts")             # Termux:Widget shows every script in this folder as a button
    os.makedirs(scripts, exist_ok=True)
    for label, body in (("Rofpalys Play-Pause", "rofpalys ctl toggle"), ("Rofpalys Next", "rofpalys ctl next"), ("Rofpalys Previous", "rofpalys ctl prev"),
                        ("Rofpalys Sleep 30 min", "rofpalys ctl sleep 30"), ("Rofpalys Volume up", "rofpalys ctl vol +10"), ("Rofpalys Volume down", "rofpalys ctl vol -10")):
        p = os.path.join(scripts, label)
        if os.path.exists(p) and "rofpalys-hook" not in open(p, errors="replace").read():
            continue
        with open(p, "w") as f:
            f.write("#!%s\n# rofpalys-hook\n%s\n" % (sh, body))
        make_executable(p)
    print("  ok   %s  (Termux:Widget buttons: Play-Pause, Next, Previous, Sleep 30, Volume)" % scripts)
    hooks = {"termux-file-editor": 'exec rofpalys play "$@"',
             "termux-url-opener": 'case "$1" in\n  http*|*youtu*) exec rofpalys yt "$1" ;;\n  *) exec rofpalys play "$@" ;;\nesac'}
    for name, body in hooks.items():
        p = os.path.join(binp, name)
        if os.path.exists(p) and "rofpalys-hook" not in open(p, errors="replace").read():
            print("  skip %s (you already have your own; backup not touched)" % p)
            continue
        with open(p, "w") as f:
            f.write("#!%s\n# rofpalys-hook\n%s\n" % (sh, body))
        make_executable(p)
        print("  ok   " + p)
    print("Now in any app: Share -> Termux. Audio files open in Rofpalys; YouTube links download and play.")
    return 0


# ------------------------------------------------------------------ the app: the window with the Rofpalys logo, the menu entry and the Desktop icon
# All of this used to be four loose files (rofpalys_launcher.py, rofpalys_logo.svg, rofpalys_launcher.desktop, install_launcher.sh). Nothing needs tkinter until the window opens.
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <polygon points="128,16 225,72 225,184 128,240 31,184 31,72" fill="#0b0b0d" stroke="#8b5a2b" stroke-width="8" stroke-linejoin="round"/>
  <circle cx="128" cy="128" r="74" fill="none" stroke="#2f6fed" stroke-width="4"/>
  <rect x="72"  y="106" width="16" height="44"  rx="8" fill="#c08a4b"/>
  <rect x="96"  y="86"  width="16" height="84"  rx="8" fill="#5ea0ff"/>
  <rect x="120" y="68"  width="16" height="120" rx="8" fill="#2ecc71"/>
  <rect x="144" y="92"  width="16" height="72"  rx="8" fill="#5ea0ff"/>
  <rect x="168" y="102" width="16" height="52"  rx="8" fill="#c08a4b"/>
</svg>
"""
DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=Rofpalys
Comment=Rofpalys Music Suite (GUI / CLI)
Exec=%(gui)s
Icon=%(icon)s
Terminal=false
Categories=AudioVideo;Audio;Player;
Actions=gui;cli;window;
X-Rofpalys-Menu=1

[Desktop Action gui]
Name=Buka GUI
Exec=%(gui)s

[Desktop Action cli]
Name=Buka CLI
Exec=%(cli)s

[Desktop Action window]
Name=Pilih mode (jendela GUI / CLI)
Exec=%(open)s
"""
APP_COLORS = dict(black="#0b0b0d", panel="#15110e", brown="#8b5a2b", sand="#c08a4b", blue="#2f6fed", sky="#5ea0ff", green="#2ecc71", text="#e8e2d8", mute="#8a8277")
APP_MODES = {"GUI": dict(sub="gui", color=APP_COLORS["green"], desc="Tampilan grafis - terminal disembunyikan"),
             "CLI": dict(sub="tui", color=APP_COLORS["sky"], desc="Mode terminal - diketik otomatis di terminal")}
_APP_T = "Rofpalys CLI"
APP_TERMS = (("xfce4-terminal", ["-T", _APP_T, "-x"]), ("gnome-terminal", ["--title", _APP_T, "--"]), ("mate-terminal", ["--title", _APP_T, "-x"]), ("konsole", ["-e"]),
             ("qterminal", ["-e"]), ("lxterminal", ["-t", _APP_T, "-e"]), ("alacritty", ["-t", _APP_T, "-e"]), ("kitty", ["--title", _APP_T]),
             ("x-terminal-emulator", ["-e"]), ("xterm", ["-T", _APP_T, "-e"]))


def app_log_path():
    return os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "rofpalys", "launcher.log")


def app_cmd(sub):
    """The command that starts Rofpalys in a sub-mode: THIS Python with THIS file (so the Python that has tkinter and the rest is the one that runs it)."""
    return [sys.executable or "python3", SELF, sub]


def app_log_tail():
    """The last line the started program wrote to launcher.log (what went wrong), shortened."""
    try:
        with open(app_log_path(), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4000))
            lines = [x.strip() for x in f.read().decode("utf-8", "replace").splitlines() if x.strip()]
        return (lines[-1][:140] + " ...") if lines and len(lines[-1]) > 140 else (lines[-1] if lines else "")
    except OSError:
        return ""


def app_start(mode):
    """Starts Rofpalys in the chosen mode -> (ok, text for the window, process or None). GUI: in the background, the terminal is not shown (what it prints goes to launcher.log).
    CLI: a terminal window that runs  rofpalys tui  (it shows its own errors)."""
    cmd = app_cmd(APP_MODES[mode]["sub"])
    dn = subprocess.DEVNULL
    try:
        if mode == "GUI":
            lp = app_log_path()
            os.makedirs(os.path.dirname(lp), exist_ok=True)
            kw = {"start_new_session": True} if os.name == "posix" else {"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
            with open(lp, "ab") as log:
                proc = subprocess.Popen(cmd, stdin=dn, stdout=log, stderr=log, cwd=HOME, **kw)
            return True, "Rofpalys GUI dijalankan", proc
        import shlex
        script = (shlex.join(cmd) + '; rc=$?; [ $rc -ne 0 ] && { echo; read -r -p "[exit $rc] Enter untuk menutup..." _; }; exit $rc')
        for term, pre in APP_TERMS:
            if shutil.which(term):
                subprocess.Popen([term, *pre, "bash", "-lc", script], stdin=dn, stdout=dn, stderr=dn, start_new_session=True)
                return True, "CLI dibuka di " + term, None
        return False, "Terminal tidak ditemukan (pasang xterm / xfce4-terminal)", None
    except OSError as e:
        return False, str(e), None


def app_run(mode):
    """app_start without the process: (ok, text)."""
    ok, text, _proc = app_start(mode)
    return ok, text


def app_failed(proc, wait=1.2):
    """A GUI that was started a moment ago: did it die at once? -> the reason (log tail) or None when it is running (or ended well)."""
    if proc is None:
        return None
    try:
        rc = proc.wait(timeout=wait)
    except subprocess.TimeoutExpired:
        return None
    if rc in (0, None):
        return None
    return "gagal (kode %s): %s" % (rc, app_log_tail() or app_log_path())


def app_error_window(text, mode="GUI"):
    """The icon starts Rofpalys without a terminal, so a start that fails would be silent: a small window says why and offers the terminal version.
    Silent when there is no display or no tkinter (then there is nobody to show it to)."""
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception:
        return
    C = APP_COLORS
    root.title("Rofpalys")
    root.configure(bg=C["black"])
    root.geometry("560x260")
    tk.Label(root, text="Rofpalys %s tidak bisa dibuka" % mode, bg=C["black"], fg="#e5534b", font=("DejaVu Sans", 13, "bold")).pack(pady=(16, 6))
    tk.Label(root, text=text, bg=C["black"], fg=C["text"], wraplength=520, justify="left", font=("DejaVu Sans", 10)).pack(padx=16, fill="x")
    tk.Label(root, text="Log: " + app_log_path(), bg=C["black"], fg=C["mute"], wraplength=520, justify="left", font=("DejaVu Sans", 9)).pack(padx=16, pady=(8, 0), fill="x")
    row = tk.Frame(root, bg=C["black"])
    row.pack(side="bottom", pady=14)

    def cli():
        ok, _t, _p = app_start("CLI")
        if ok:
            root.destroy()

    if mode == "GUI":
        tk.Button(row, text="Buka versi CLI", command=cli, bg=C["sky"], fg=C["black"], relief="flat", padx=16, pady=6).pack(side="left", padx=6)
    tk.Button(row, text="Tutup", command=root.destroy, bg=C["panel"], fg=C["text"], relief="flat", padx=16, pady=6).pack(side="left", padx=6)
    try:
        root.mainloop()
    except Exception:
        pass


def app_draw_logo(cv, cx, cy, r, accent):
    """The logo on a Tk canvas: brown hexagon + blue ring + equalizer bars (the middle bar takes the colour of the active mode)."""
    C = APP_COLORS
    cv.delete("all")
    s = r / 112.0

    def P(x, y):
        return cx + (x - 128) * s, cy + (y - 128) * s

    pts = [P(*p) for p in [(128, 16), (225, 72), (225, 184), (128, 240), (31, 184), (31, 72)]]
    cv.create_polygon(pts, fill=C["black"], outline=C["brown"], width=max(2, 8 * s), joinstyle="round")
    x0, y0 = P(54, 54)
    x1, y1 = P(202, 202)
    cv.create_oval(x0, y0, x1, y1, outline=C["blue"], width=max(1, 4 * s))
    cols = [C["sand"], C["sky"], accent, C["sky"], C["sand"]]
    for i, (h, col) in enumerate(zip((44, 84, 120, 72, 52), cols)):
        ax, ay = P(72 + i * 24, 128 - h / 2)
        bx, by = P(88 + i * 24, 128 + h / 2)
        cv.create_rectangle(ax, ay, bx, by, fill=col, outline="")


def app_window(mode):
    """The app window: the logo, a GUI / CLI menu and one big button. Keys: Enter = start, g / c = mode, Esc = close."""
    import tkinter as tk
    C = APP_COLORS

    class AppWindow(tk.Tk):
        def __init__(self, first):
            super().__init__()
            self.title("Rofpalys")
            self.geometry("520x380")
            self.minsize(340, 300)
            self.configure(bg=C["black"])
            self.mode = tk.StringVar(value=first)
            top = tk.Frame(self, bg=C["panel"])
            top.pack(fill="x")
            self.mb = tk.Menubutton(top, bg=C["panel"], fg=C["text"], relief="flat", activebackground=C["brown"], activeforeground=C["text"], padx=12, pady=6,
                                    font=("DejaVu Sans", 11, "bold"))
            menu = tk.Menu(self.mb, tearoff=0, bg=C["panel"], fg=C["text"], activebackground=C["brown"], activeforeground=C["text"], selectcolor=C["green"])
            for m in APP_MODES:
                menu.add_radiobutton(label=m, variable=self.mode, value=m, command=self.refresh)
            self.mb["menu"] = menu
            self.mb.pack(side="left")
            tk.Label(top, text="ANROFTY", bg=C["panel"], fg=C["brown"], font=("DejaVu Sans", 9, "bold")).pack(side="right", padx=12)
            self.cv = tk.Canvas(self, bg=C["black"], highlightthickness=0)
            self.lbl_name = tk.Label(self, text="R O F P A L Y S", bg=C["black"], fg=C["text"])
            self.lbl_desc = tk.Label(self, bg=C["black"], fg=C["mute"])
            self.lbl_cmd = tk.Label(self, bg=C["black"], fg=C["sand"])
            self.btn = tk.Button(self, text="▶  JALANKAN", relief="flat", bd=0, fg=C["black"], padx=24, pady=8, command=self.go, font=("DejaVu Sans", 12, "bold"))
            self.lbl_status = tk.Label(self, bg=C["black"], fg=C["mute"], font=("DejaVu Sans", 9))
            # the text parts are packed from the bottom FIRST and the logo canvas LAST: a small window then shrinks the logo, never the button or the status line
            self.lbl_status.pack(side="bottom", pady=(0, 8))
            self.btn.pack(side="bottom", pady=8)
            for w in (self.lbl_cmd, self.lbl_desc, self.lbl_name):
                w.pack(side="bottom")
            self.cv.pack(fill="both", expand=True)
            self.cv.bind("<Configure>", lambda e: self.refresh())
            self.bind("<Return>", lambda e: self.go())
            self.bind("<Escape>", lambda e: self.destroy())
            self.bind("g", lambda e: self.set_mode("GUI"))
            self.bind("c", lambda e: self.set_mode("CLI"))

        def set_mode(self, m):
            self.mode.set(m)
            self.refresh()

        def refresh(self):
            m = self.mode.get()
            info = APP_MODES[m]
            w, h = self.cv.winfo_width(), self.cv.winfo_height()
            app_draw_logo(self.cv, w / 2, h / 2, max(30, min(w, h) / 2 - 8), info["color"])
            fs = max(14, min(30, self.winfo_width() // 16))
            self.lbl_name.config(font=("DejaVu Sans", fs, "bold"))
            self.lbl_desc.config(text=info["desc"], font=("DejaVu Sans", 10))
            self.lbl_cmd.config(text="$ rofpalys " + info["sub"], font=("DejaVu Sans Mono", 10))
            self.mb.config(text="☰  %s  ▾" % m)
            self.btn.config(bg=info["color"], activebackground=info["color"])

        def go(self):
            ok, text, proc = app_start(self.mode.get())
            self.lbl_status.config(text=text, fg=C["green"] if ok else "#e5534b")
            if not ok:
                return
            if proc is None:
                self.after(700, self.destroy)                  # CLI: the terminal shows its own errors
            else:
                self.after(1300, lambda: self.settle(proc))

        def settle(self, proc):
            """The GUI was started 1.3 s ago: if it died at once, stay open and say why (launcher.log); otherwise this window is done."""
            why = app_failed(proc, wait=0)
            if why:
                self.lbl_status.config(text="Rofpalys " + why, fg="#e5534b", wraplength=max(200, self.winfo_width() - 24))
            else:
                self.destroy()

    AppWindow(mode).mainloop()


# --- the icon in the application menu (what install_launcher.sh did) - Linux and Termux desktops
def desktop_dir():
    """The Desktop folder (as the user's own settings name it: ~/.config/user-dirs.dirs), or None when there is none (or it is the home folder itself)."""
    cand = os.path.join(HOME, "Desktop")
    try:
        with open(os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "user-dirs.dirs"), encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'\s*XDG_DESKTOP_DIR\s*=\s*"?([^"\n]*)"?', line)
                if m and m.group(1).strip():
                    cand = m.group(1).strip().replace("$HOME", HOME).rstrip("/") or cand
    except OSError:
        pass
    return cand if os.path.isdir(cand) and os.path.realpath(cand) != os.path.realpath(HOME) else None


def app_linux():
    """Linux and Android (Termux) have application menus; Python 3.13+ calls the Termux platform 'android'."""
    return sys.platform.startswith(("linux", "android"))


def termux_share():
    """$PREFIX/share on Termux - where Termux's own programs (and the desktop menu) look - else None."""
    if PREFIX and "com.termux" in PREFIX and os.access(os.path.join(PREFIX, "share"), os.W_OK):
        return os.path.join(PREFIX, "share")
    return None


def data_homes():
    """The folders a menu entry can live in, the one Rofpalys writes to first: Termux $PREFIX/share (then ~/.local/share); elsewhere ~/.local/share ($XDG_DATA_HOME)."""
    xdg = os.environ.get("XDG_DATA_HOME")
    user = xdg or os.path.join(HOME, ".local", "share")
    sysd = termux_share()
    homes = [sysd, user] if (sysd and not xdg) else [user] + ([sysd] if sysd else [])
    return [h for i, h in enumerate(homes) if h not in homes[:i]]


def _icon_path(home):
    return os.path.join(home, "icons", "hicolor", "scalable", "apps", "rofpalys.svg")


def _entry_path(home):
    return os.path.join(home, "applications", "rofpalys.desktop")


def app_files():
    """Where the icon, the menu entry and the Desktop icon are written: {"icon", "entry", "desktop"?}."""
    home = data_homes()[0]
    out = {"icon": _icon_path(home), "entry": _entry_path(home)}
    dd = desktop_dir()
    if dd:
        out["desktop"] = os.path.join(dd, "rofpalys.desktop")
    return out


def _dq(arg):
    """One argument of an Exec= line, quoted the way the Desktop Entry specification wants it (spaces, quotes, $, backticks, backslash, %)."""
    arg = str(arg).replace("%", "%%")
    if re.match(r"^[A-Za-z0-9_@+=:,./%-]+$", arg):
        return arg
    return '"' + re.sub(r'(["`$])', r"\\\1", arg.replace("\\", "\\\\\\\\")) + '"'


def app_python():
    """The Python for Exec= lines. Termux (and pyenv, venvs) have  python  and  python3  that are the same program; which name started us depends on how Rofpalys was called
    ("python ~/rofpalys.py" or the  rofpalys  command), so the name is made the same every time: python3 when that is the same file as this Python, else what sys.executable says."""
    exe = sys.executable or "python3"
    try:
        real = os.path.realpath(exe)
        cand = os.path.join(os.path.dirname(exe), "python3")
        if os.path.isfile(cand) and os.path.realpath(cand) == real:
            return cand
    except OSError:
        pass
    return exe


def app_base():
    """The start of every Exec= line: this Python, the installed command (or this file), and  app."""
    exe = bin_path() if os.path.isfile(bin_path()) else SELF
    return "%s %s app" % (_dq(app_python()), _dq(exe))


def app_entry_text(icon):
    base = app_base()
    return DESKTOP_ENTRY % dict(open=base, gui=base + " --mode gui --now", cli=base + " --mode cli --now", icon=icon)


def app_owned(path):
    """Is this .desktop file ours (written by this launcher, or by the old install_launcher.sh)? Another one with the same name is never touched."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            t = f.read()
    except OSError:
        return False
    return "X-Rofpalys-Menu" in t or "rofpalys_launcher.py" in t


def _write_text(path, text, mode=None):
    """Writes the file when its content differs (a .part file first, so a crash never leaves half a file) -> True when something was written."""
    try:
        with open(path, encoding="utf-8") as f:
            same = f.read() == text
    except OSError:
        same = False
    if not same:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".part"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    if mode is not None:
        try:
            os.chmod(path, mode)                           # a launcher on the Desktop must be executable to be trusted
        except OSError:
            pass
    return not same


def _refresh_menu_cache(folder):
    exe = shutil.which("update-desktop-database")
    if exe:
        try:
            subprocess.run([exe, folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except (OSError, subprocess.SubprocessError):
            pass
    exe = shutil.which("xfdesktop")                        # XFCE: the desktop (icons + right-click menu) reads its files again, when we are inside that session
    if exe and os.environ.get("DISPLAY"):
        try:
            subprocess.run([exe, "--reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass


def _short(path):
    return ("~" + path[len(HOME):]) if HOME and path.startswith(HOME + os.sep) else path


def app_install(quiet=False, force=False):
    """Puts the logo (icon), the menu entry and - when there is a Desktop folder - the Desktop icon in place -> what was written, e.g. ["icon", "menu entry"] ([] = nothing to do / skipped).
    Linux and Termux desktops only; ROFPALYS_NO_MENU=1 turns it off (not for the explicit  rofpalys app install ). A file with that name that is not ours is left alone;
    an older entry of ours in another menu folder is removed (the one in your home folder would hide the new one)."""
    if not app_linux() or (os.environ.get("ROFPALYS_NO_MENU") and not force):
        if not quiet:
            print("The menu icon is for Linux desktops (also a Termux X11 / VNC desktop). Here, open the window with:  rofpalys app")
        return []
    f, changed = app_files(), []
    try:
        if _write_text(f["icon"], LOGO_SVG):
            changed.append("icon")
        text = app_entry_text(f["icon"])
        for key, label in (("entry", "menu entry"), ("desktop", "Desktop icon")):
            if key not in f:
                continue
            if os.path.exists(f[key]) and not app_owned(f[key]):
                print("[rofpalys] note: %s exists and is not Rofpalys's own - left alone" % f[key])
                continue
            if _write_text(f[key], text, 0o755):
                changed.append(label)
    except OSError as e:
        print("[rofpalys] could not write the app icon: %s" % e)
        return changed
    for home in data_homes()[1:]:                          # an older entry of ours somewhere else would hide (or double) the new one
        e, i = _entry_path(home), _icon_path(home)
        if os.path.isfile(e) and app_owned(e):
            try:
                os.remove(e)
                if os.path.isfile(i):
                    os.remove(i)
                changed.append("older entry in %s removed" % _short(home))
            except OSError:
                pass
    if changed:
        _refresh_menu_cache(os.path.dirname(f["entry"]))
    return changed


def app_remove():
    """Takes the icon, the menu entry and the Desktop icon away, wherever Rofpalys put them (only its own files) -> what was removed."""
    gone = []
    homes = data_homes()
    targets = [(_entry_path(h), "menu entry", True) for h in homes] + [(p, "Desktop icon", True) for p in [app_files().get("desktop")] if p] + [(_icon_path(h), "icon", False) for h in homes]
    for p, label, check in targets:
        if not os.path.isfile(p) or (check and not app_owned(p)):
            continue
        try:
            os.remove(p)
            gone.append(label)
        except OSError as e:
            print("[rofpalys] could not remove %s: %s" % (p, e))
    if gone:
        _refresh_menu_cache(os.path.dirname(app_files()["entry"]))
    return gone


def app_status():
    """One line for  rofpalys doctor ."""
    if not app_linux():
        return "the menu icon is for Linux desktops; the window works everywhere:  rofpalys app"
    found = [h for h in data_homes() if os.path.isfile(_entry_path(h))]
    if not found:
        return "no menu icon yet ->  rofpalys app install   (the window:  rofpalys app)"
    home = found[0]
    entry = _entry_path(home)
    if not app_owned(entry):
        return "a menu entry named rofpalys.desktop that is not Rofpalys's own exists (left alone)"
    try:
        with open(entry, encoding="utf-8") as fh:
            same = fh.read() == app_entry_text(_icon_path(home))
    except OSError:
        same = False
    if same and os.path.isfile(_icon_path(home)):
        return "icon + menu entry installed (%s)%s" % (entry, "; Desktop icon too" if os.path.isfile(app_files().get("desktop", "")) else "")
    return "the menu entry is out of date (other Python or location, or the icon file is gone) ->  rofpalys app install"


def app_report():
    """What is where - printed by  rofpalys app install , so a missing icon can be traced."""
    f = app_files()
    for label, key in (("icon", "icon"), ("menu entry", "entry"), ("Desktop icon", "desktop")):
        if key in f:
            print("   %-13s %-8s %s" % (label, "ok" if os.path.isfile(f[key]) else "MISSING", f[key]))
        else:
            print("   %-13s none     no Desktop folder found (looked for ~/Desktop and in ~/.config/user-dirs.dirs)" % label)
    print("   starts with   %s" % app_base())
    print("   look for it:  Applications > Multimedia > Rofpalys  (and on the Desktop)")
    print("   not there yet? Menus are cached: restart the desktop (Termux X11: Stop Desktop, then start it again) or log out and in again.")


def cmd_app(args):
    """rofpalys app [--mode gui|cli] [--now]  |  rofpalys app install  |  rofpalys app remove"""
    import argparse
    ap = argparse.ArgumentParser(prog="rofpalys app", description="The Rofpalys app window (logo + GUI / CLI) and its menu icon.")
    ap.add_argument("action", nargs="?", choices=("install", "remove"), help="install = icon in the application menu and on the Desktop; remove = take it away")
    ap.add_argument("--mode", choices=("gui", "cli"), default="gui", help="the mode that is chosen when the window opens (default gui)")
    ap.add_argument("--now", action="store_true", help="start at once, without the window")
    a = ap.parse_args(args)
    if a.action == "install":
        if not app_linux():
            app_install()
            return 1
        done = app_install(force=True)
        print("[rofpalys] app icon: %s" % (", ".join(done) if done else "already in place"))
        app_report()
        return 0
    if a.action == "remove":
        gone = app_remove()
        print("[rofpalys] app icon removed: %s" % (", ".join(gone) if gone else "nothing of Rofpalys's own to remove"))
        return 0
    mode = a.mode.upper()
    if a.now:
        ok, text, proc = app_start(mode)
        why = app_failed(proc) if ok else None
        print(("Rofpalys " + why) if why else text)
        if why or not ok:
            app_error_window(("Rofpalys " + why) if why else text, mode)          # an icon has no terminal: the reason is shown in a small window
        return 0 if ok and not why else 1
    try:
        import tkinter as tk
    except ImportError:
        print("The app window needs tkinter:  pkg install python-tkinter  (Termux)  |  sudo apt install python3-tk  |  or start directly:  rofpalys app --now   /   rofpalys tui")
        return 1
    try:
        app_window(mode)
    except tk.TclError as e:
        print("The app window could not open (%s).  It needs a graphical display (Termux: X11 / VNC).  Without one:  rofpalys tui" % e)
        return 1
    return 0


def cmd_doctor(d):
    import platform
    import rofpalys_library as lib
    import rofpalys_engine as E
    print("Rofpalys %s | Python %s | %s%s" % (VERSION, platform.python_version(), sys.platform, " (Termux)" if lib.IS_TERMUX else ""))
    cmd_verify(d)
    print("modules : %s" % d)
    print("config  : %s" % lib.CONFIG_DIR)
    names = [e["name"] for e in E.AVAILABLE_ENGINES]
    print("players : %s" % (", ".join(names) or "NONE"))
    if not names:
        print("   -> install one:  pkg install mpv   (Termux)   |   sudo apt install mpv   |   brew install mpv")
    elif "mpv" not in names and "ffplay" not in names and "VLC" not in names:
        print("   -> only basic players found: no seek. Better:  pkg install mpv")
    print("seek    : %s" % ("yes" if any(e.get("seek") or e["name"] == "PyGame" for e in E.AVAILABLE_ENGINES) else "no (needs mpv/ffplay/VLC/mplayer/PyGame)"))
    print("ffprobe : %s" % ("ok" if shutil.which("ffprobe") else "missing -> no song length;  pkg install ffmpeg"))
    print("yt-dlp  : %s" % ("ok" if shutil.which("yt-dlp") else "missing -> no auto video / audio download;  pkg install yt-dlp"))
    print("control : %s%s" % ("socket ok" if hasattr(__import__("socket"), "AF_UNIX") else "no unix sockets here (rofpalys ctl is off)",
                              "; notification buttons ready (termux-notification found)" if shutil.which("termux-notification") else "; notification buttons need the Termux:API app + pkg install termux-api"))
    print("effects : %s" % ("mpv/ffplay found: equalizer, speed, slowed+reverb work" if ("mpv" in names or "ffplay" in names) else "need mpv (pkg install mpv) or ffplay"))
    print("spectrum: %s" % ("real audio visualizer ready (ffmpeg)" if shutil.which("ffmpeg") else "needs ffmpeg for the real visualizer; the simulation is used"))
    print("lyrics  : safety net LRCLIB + lyrics.ovh online%s" % ("; YouTube captions via yt-dlp" if shutil.which("yt-dlp") else " (install yt-dlp for YouTube captions)"))
    try:
        import rofpalys_CyroKayAI_providers as PV
        rows = PV.status()
        print("providers: %s" % "  >  ".join("%s %s" % (r["name"], ("ok" + (" " + r["version"] if r["version"] else "")) if r["installed"] else ("needs Python %d.%d+" % PV.MIN_PY[r["name"]]) if not r["python_ok"] else "MISSING") for r in rows))
        print("source  : %s" % ("ONLY Musixmatch (the standard); lyrics are forced onto the recording.  Other sources:  rofpalys lyrics source all" if PV.strict() else
                                "all sources, Musixmatch first.  Musixmatch only:  rofpalys lyrics source musixmatch"))
        if any(not r["installed"] and r["python_ok"] for r in rows):
            print("          -> install the missing ones:  rofpalys install lyric")
    except ImportError:
        print("providers: rofpalys_CyroKayAI_providers.py missing -> only the built-in LRCLIB / lyrics.ovh;  python ~/rofpalys.py install")
    try:
        import rofpalys_CyroKayAI_lyric as CK
        print("cyrokay : brain v%s | voice detector: %s | ffprobe (creator tags): %s | internet: %s | self-test: %s" % (
            CK.__version__, "full (numpy)" if CK.np is not None else "basic - for the full one: pkg install python-numpy", "ok" if shutil.which("ffprobe") else "missing (pkg install ffmpeg)",
            "online" if CK.internet_ok(force=True) else "offline", "OK" if CK.selftest(False) else "FAILED"))
        if CK.np is None:
            sb = os.path.join(PREFIX, "bin") if PREFIX else ""
            mine = bool(sb) and os.path.realpath(sys.executable).startswith(os.path.realpath(sb))
            print("          numpy    : missing for %s" % sys.executable)
            if PREFIX and not mine:
                print("          -> this is not Termux's own python (pyenv / venv): 'pkg install python-numpy' installs numpy for Termux's python, which this one cannot see.")
                print("             Either  pkg install python-numpy python-tkinter  and use Termux's python (pyenv global system),  or  pip install numpy  into this one (it compiles: slow).")
        try:
            import rofpalys_CyroKayAI_turbo as TB
            print("          processor: %s" % TB.describe())
        except ImportError:
            print("          processor: rofpalys_CyroKayAI_turbo.py missing -> single core")
        try:
            import rofpalys_CyroKayAI_memory as MEM
            print("          memory   : %s" % MEM.summary())
        except ImportError:
            print("          memory   : rofpalys_CyroKayAI_memory.py missing -> nothing is learned between songs")
        if not shutil.which("ffmpeg"):
            print("          -> without ffmpeg CyroKayAI cannot listen to the song: lyrics keep the times of the file, markers still work;  pkg install ffmpeg")
    except ImportError:
        print("cyrokay : rofpalys_CyroKayAI_lyric.py missing -> lyrics work the old way, without the exact sync;  python ~/rofpalys.py install")
    try:
        import rofpalys_analytics as AN
        print("stats   : %s" % AN.describe())
        print("          rofpalys stats  |  rofpalys stats verify  |  rofpalys stats export csv FILE  |  page: Statistics in the sidebar, or F7")
    except ImportError:
        print("stats   : rofpalys_analytics.py (+ _calc, _text) missing -> no statistics;  python ~/rofpalys.py install")
    except Exception as e:
        print("stats   : problem reading the statistics: %r" % (e,))
    try:
        import rofpalys_theme as TH
        print("look    : %s  (colours + shapes + type; rofpalys theme classic|modern|cyberpunk; window: Settings > Display, or F6)" % TH.INFO[TH.current()]["name"])
    except ImportError:
        print("look    : rofpalys_theme.py missing -> only the Classic look;  python ~/rofpalys.py install")
    try:                                                     # the Web Remote: what is saved (never the token itself)
        import json as _json
        if not os.path.isfile(os.path.join(d, "rofpalys_gui_remote.py")):
            raise FileNotFoundError("feature file not installed")
        with open(os.path.join(lib.CONFIG_DIR, "remote.json"), "r", encoding="utf-8") as _f:
            _rc = _json.load(_f)
        print("remote  : Web Remote is %s (%s, port %s);  the link and the switch are in the window: Settings > Tools > Remote Web" % ("ON at start" if _rc.get("enabled") else "off", "other devices on your Wi-Fi allowed" if _rc.get("lan") else "this device only", _rc.get("port", 8765)))
    except (OSError, ValueError):
        if os.path.isfile(os.path.join(d, "rofpalys_gui_remote.py")):
            print("remote  : Web Remote is off (window: Settings > Tools > Remote Web; it is off until you turn it on)")
        else:
            print("remote  : not installed (rofpalys_gui_remote.py is missing;  put it next to rofpalys.py, then  python ~/rofpalys.py install)")
    print("app     : %s" % app_status())
    print("ffmpeg  : %s" % ("ok (cover conversion + video playback)" if shutil.which("ffmpeg") else "missing -> no cover art / video in the GUI;  pkg install ffmpeg"))
    try:
        import PIL  # noqa: F401
        print("pillow  : ok (faster cover scaling)")
    except ImportError:
        print("pillow  : not installed (optional; ffmpeg is used instead)")
    try:
        import tkinter  # noqa: F401
        print("tkinter : ok (GUI available, display: %s)" % (os.environ.get("DISPLAY") or "none"))
    except ImportError:
        print("tkinter : missing -> GUI off;  pkg install python-tkinter")
    if lib.IS_TERMUX:
        print("storage : %s" % ("ok" if os.path.isdir(os.path.join(HOME, "storage")) else "NOT linked -> run: termux-setup-storage"))
        print("volume  : %s" % ("termux-volume ok" if shutil.which("termux-volume") else "install Termux:API app + pkg install termux-api for the volume keys"))
    E.load_settings()
    t0 = time.time()
    roots = E._roots()
    print("scan    : roots = %s" % ", ".join(roots))
    n = len(lib.scan(roots, lib.AUDIO_EXTS, E.min_size_kb * 1024, skip_names=E.exclude_dirs))
    print("          %d songs found in %.1fs" % (n, time.time() - t0))
    return 0


def main(argv):
    os.environ["ROFPALYS_LAUNCHER"] = SELF                  # the programs started from here (the GUI button "CLI", "7y" in the terminal) find their way back with it
    os.environ["ROFPALYS_VERSION"] = VERSION
    d = libdir()
    fix_permissions(d)                                     # chmod +x on every start, even for --version
    if "--version" in argv or "-V" in argv:
        print("Rofpalys " + VERSION)
        return 0
    if argv[:1] in (["--help"], ["-h"], ["help"]):
        print(HELP)
        return 0
    if argv[:1] == ["--license"] or argv[:1] == ["license"]:
        return cmd_license(d)
    if argv[:1] == ["update"]:
        return cmd_update()
    if argv[:1] == ["install"] and argv[1:2] and argv[1].lower() in ("lyric", "lyrics", "lirik"):
        return cmd_install_lyric(argv[2:])
    if argv[:1] == ["install"]:
        return cmd_install(argv[1:])
    if argv[:1] == ["organize"]:
        return cmd_organize(argv[1:])
    if not is_installed() and not os.environ.get("ROFPALYS_NO_AUTO") and SELF.endswith(".py"):
        rc = cmd_install(auto=True)                        # first run from a downloaded file: set everything up, then carry on
        if rc != 0:
            return rc
        bp = bin_path()
        try:
            os.execv(sys.executable, [sys.executable, bp] + argv)
        except OSError:
            pass
        d = libdir()
    if argv[:1] == ["app"] and argv[1:2] in (["install"], ["remove"]):
        return cmd_app(argv[1:])                           # only files: no modules needed
    if d is None:
        print("Rofpalys: module files not found (rofpalys_engine.py, ...).")
        print("Download all the files into one folder (Downloads or ~) and run:  python rofpalys.py install")
        return 1
    sys.path.insert(0, d)
    gone = [m for m in MODULES if not os.path.isfile(os.path.join(d, m))]
    if gone and argv[:1] not in (["verify"], ["reset"]):                       # a friendly message instead of a Python traceback
        print("Rofpalys: %d file(s) are missing in %s:\n   %s" % (len(gone), d, ", ".join(gone)))
        print("Download them again (tap the file card), put them in Downloads or ~, then run:  python ~/rofpalys.py install")
        return 1
    cmd, rest = (argv[0], argv[1:]) if argv and argv[0] in ("gui", "tui", "play", "scan", "yt", "doctor", "integrate", "media", "reset", "verify", "ctl", "now", "daemon", "features", "lyrics", "stats", "theme", "app", "lang") else (None, argv)
    if cmd == "app":
        return cmd_app(rest)
    if cmd == "lang":
        try:
            import rofpalys_i18n as I18N_
        except ImportError as e:
            print("rofpalys_i18n.py is missing: %s\nDownload it again (tap the file card), put it in Downloads or ~, then run:  python ~/rofpalys.py install" % e)
            return 1
        return I18N_.cli(rest)
    if cmd == "doctor":
        return cmd_doctor(d)
    if cmd == "integrate":
        return cmd_integrate()
    if cmd == "reset":
        return cmd_reset(d, rest)
    if cmd in ("ctl", "now"):
        import rofpalys_control as CT
        return CT.ctl_main((["now"] if cmd == "now" else []) + rest)
    if cmd == "daemon":
        return cmd_daemon(d)
    if cmd == "verify":
        return cmd_verify(d)
    if cmd == "features":
        return cmd_features(d)
    if cmd in ("stats", "theme"):
        mod = "rofpalys_analytics" if cmd == "stats" else "rofpalys_theme"
        try:
            M_ = __import__(mod)
        except ImportError as e:
            print("%s.py (or a file it needs) is missing: %s\nDownload it again (tap the file card), put it in Downloads or ~, then run:  python ~/rofpalys.py install" % (mod, e))
            return 1
        return M_.cli(rest)
    if cmd == "lyrics":
        try:
            import rofpalys_CyroKayAI_lyric as CK
        except ImportError:
            print("rofpalys_CyroKayAI_lyric.py is missing.  Download it again (tap the file card), put it in Downloads or ~, then run:  python ~/rofpalys.py install")
            return 1
        return CK.cli(rest)
    import rofpalys_library as lib
    if cmd == "scan":
        import rofpalys_engine as E
        E.load_settings()
        t0 = time.time()
        found = E.scan_library_sync()
        print("%d songs in %.1fs" % (len(found), time.time() - t0))
        for p in sorted(found)[:15]:
            print("  " + p)
        if len(found) > 15:
            print("  ... and %d more" % (len(found) - 15))
        if not found and lib.storage_hint():
            print("Hint: " + lib.storage_hint())
        return 0
    if cmd == "media":
        import rofpalys_media as M
        if rest[:1] == ["reset"]:
            M.reset_all()
            print("Downloaded cover art and video deleted (your own files were not touched).")
        a, v = M.cache_info()
        print("Cover art cache: %.1f MB | Video cache: %.1f MB | %s" % (a, v, M.MEDIA_DIR))
        return 0
    if cmd == "yt":
        if not rest:
            print("usage: rofpalys yt URL")
            return 1
        import rofpalys_tui
        start_recorder("tui")
        rofpalys_tui.run([], yt=rest[0])
        return 0
    paths, skipped = lib.resolve_inputs([a for a in rest if not a.startswith("--")])
    for s in skipped:
        print("skipped (not an audio file / folder / unreachable): " + s)
    if cmd == "gui":
        import rofpalys_gui
        if not hasattr(rofpalys_gui, "main"):
            print("rofpalys_gui.py is incomplete (cut off while pasting).  Check with:  rofpalys verify")
            return 1
        start_recorder("gui")
        return rofpalys_gui.main(paths)
    import rofpalys_tui
    if not hasattr(rofpalys_tui, "run"):
        print("rofpalys_tui.py is incomplete (cut off while pasting).  Check with:  rofpalys verify")
        return 1
    start_recorder("tui")
    rofpalys_tui.run(paths)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:                                 # e.g.  rofpalys ctl help | head
        sys.exit(0)

# END-OF-FILE rofpalys.py
