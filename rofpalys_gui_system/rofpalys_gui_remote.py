#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - GUI feature: Web Remote (control the player from a browser, for example the one on your phone)
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""A small web page that is the remote control of the Rofpalys window: song, cover, progress (tap to seek), play / pause, next / previous, volume, play mode, favourite, and a
search box that finds songs and starts them. The page has the colours, corners and type of the look in use (Classic / Modern / Cyberpunk).

  Turn it on   Settings > Tools > Remote Web. It is OFF until you turn it on, and the choice is remembered.
  Address      http://127.0.0.1:8765/?t=<token>   - the token is a long random secret kept in <config folder>/remote.json (readable by you only).
               The window shows the link and copies it for you. "New token" makes the old links stop working at once.
  Same device  (default) only programs on THIS device can reach it: open the link in the browser of the phone that runs Rofpalys.
  Other device "Allow other devices on my Wi-Fi" listens on the network too, so a second phone or a laptop can use the link. The traffic is plain HTTP: use it only
               on a network you trust, and turn it off when you are done.

Safety, in short: nothing works without the token (compared in constant time, and a client that guesses wrong too often is slowed down); a page from another web site cannot
use it (no cross-site access, a custom header is needed for every command); a request that arrives under a web name instead of an address is refused (DNS rebinding); songs are
named by short ids, never by file paths, and only songs of your library can be started; the cover that is served is the one of the playing song; bodies are limited to 1 KB.
Only the Tk thread of the window touches the player: the web threads only read a snapshot and hand over jobs. Hub, the handler and the page have no window in them."""
import hashlib
import hmac
import http.server
import ipaddress
import json
import math
import os
import queue
import re
import secrets
import socket
import tempfile
import threading
import time
import urllib.parse

from rofpalys_gui_base import *   # noqa: F401,F403

try:
    import rofpalys_theme as TH2
except Exception:
    TH2 = None
try:
    import rofpalys_insight as IN
except Exception:
    IN = None
try:
    import rofpalys_analytics as AN
except Exception:
    AN = None

FEATURE = {"name": "remote", "title": "Web Remote: control Rofpalys from a browser (token, same device by default)", "version": "1.0", "order": 60, "enabled": True}
DEFAULT_PORT = 8765
MAX_BODY = 1024
MAX_FAILS, FAIL_WINDOW = 20, 60.0
JOB_WAIT = 2.5
MODES = {"en": ("Single", "Repeat 1", "Sequential", "Loop All", "Shuffle"), "id": ("Normal", "Ulangi 1", "Berurutan", "Ulangi Semua", "Acak")}        # the app's own words (engine m_single ... m_shuffle)
TEXTS = {
    "en": dict(rm_menu="Web Remote (control from a browser)", rm_title="Web Remote", rm_off="Off", rm_on="On", rm_turn_on="Turn on", rm_turn_off="Turn off", rm_lan="Allow other devices on my Wi-Fi", rm_copy="Copy link", rm_copied="Link copied", rm_new="New token", rm_new_done="New token made. Old links stopped working.",
               rm_close="Close", rm_link="Link", rm_running="Running on port %d", rm_note="Anyone with the link can control the player. Share it only with people you trust. On Wi-Fi the traffic is not encrypted.",
               rm_busy="The port is busy: %s", rm_started="Web Remote is on", rm_stopped="Web Remote is off"),
    "id": dict(rm_menu="Remote Web (kendalikan dari browser)", rm_title="Remote Web", rm_off="Mati", rm_on="Hidup", rm_turn_on="Hidupkan", rm_turn_off="Matikan", rm_lan="Izinkan perangkat lain di Wi-Fi-ku",  rm_copy="Salin tautan", rm_copied="Tautan disalin", rm_new="Token baru", rm_new_done="Token baru dibuat. Tautan lama tidak berlaku lagi.",
               rm_close="Tutup", rm_link="Tautan", rm_running="Berjalan di port %d", rm_note="Siapa pun yang punya tautan bisa mengendalikan pemutar. Bagikan hanya ke orang yang kamu percaya. Di Wi-Fi lalu lintasnya tidak dienkripsi.",
               rm_busy="Port sedang dipakai: %s", rm_started="Remote Web hidup", rm_stopped="Remote Web mati"),
}
PAGE_TEXTS = {
    "en": dict(title="Rofpalys Remote", nothing="Nothing is playing", search="Search songs ...", favorites="Favourites", recent="Recent", top="Top", empty="Nothing here yet",
               bad_token="This link has no valid token. Open the link that Rofpalys shows.", lost="Connection lost - trying again", modes=MODES["en"], fav="Favourite", vol="Volume"),
    "id": dict(title="Rofpalys Remote", nothing="Tidak ada yang diputar", search="Cari lagu ...", favorites="Favorit", recent="Terbaru", top="Teratas", empty="Belum ada isinya",
               bad_token="Tautan ini tidak punya token yang sah. Buka tautan yang ditampilkan Rofpalys.", lost="Koneksi putus - mencoba lagi", modes=MODES["id"], fav="Favorit", vol="Volume"),
}


def page_texts(lg):
    """The texts of the web page in a language: its own entry (en / id) or the English one through the catalogue (zh, de, ja, ru); the five play-mode names too."""
    lg = I18N.norm(lg) or "en"
    out = {k: I18N.pick(PAGE_TEXTS, lg, k) for k in PAGE_TEXTS["en"]}
    out["modes"] = tuple(MODES[lg]) if lg in MODES else tuple(I18N.tr(x, lg) for x in MODES["en"])
    return out


# ---------------------------------------------------------------- the settings file
def cfg_path():
    return os.path.join(lib.CONFIG_DIR, "remote.json")


def new_token():
    return secrets.token_urlsafe(24)


def load_cfg(p=None):
    """{"enabled", "lan", "port", "token"}; a missing or broken file gives the safe defaults (off, this device only) and a fresh token (saved)."""
    d = {"enabled": False, "lan": False, "port": DEFAULT_PORT, "token": ""}
    p = p or cfg_path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            d["enabled"], d["lan"] = bool(raw.get("enabled")), bool(raw.get("lan"))
            if isinstance(raw.get("port"), int) and 1024 <= raw["port"] <= 65500:
                d["port"] = raw["port"]
            if isinstance(raw.get("token"), str) and len(raw["token"]) >= 16 and re.fullmatch(r"[A-Za-z0-9_\-]+", raw["token"]):
                d["token"] = raw["token"]
    except (OSError, ValueError, TypeError):
        pass
    if not d["token"]:
        d["token"] = new_token()
        save_cfg(d, p)
    return d


def save_cfg(d, p=None):
    p = p or cfg_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".remote-", dir=os.path.dirname(p))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        try:
            os.chmod(tmp, 0o600)                                   # the token is a secret: readable by you only
        except OSError:
            pass
        os.replace(tmp, p)
        return True
    except OSError as e:
        log("remote save: %r" % (e,))
        return False


def song_id(path):
    return hashlib.sha1(("rofpalys:" + path).encode("utf-8", "replace")).hexdigest()[:12]


def lan_addresses():
    """The IPv4 addresses of this device that other devices could use (best effort, never raises)."""
    out = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("10.255.255.255", 1))                              # no packet is sent: this only asks which interface the system would use
        out.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            out.append(info[4][0])
    except OSError:
        pass
    seen, res = set(), []
    for a in out:
        if a and not a.startswith("127.") and a != "0.0.0.0" and a not in seen:
            seen.add(a)
            res.append(a)
    return res


# ---------------------------------------------------------------- the hub: what the web threads and the window share
class Job:
    __slots__ = ("kind", "arg", "done", "result")

    def __init__(self, kind, arg):
        self.kind, self.arg, self.done, self.result = kind, arg, threading.Event(), None


class Hub:
    """The snapshot of the player (replaced as a whole by the window), the jobs for the window, the token and the throttle. No Tk, no player in here."""

    def __init__(self, token, lan=False, texts=None, page_colors=None):
        self.token, self.lan = token, lan
        self.snapshot = {"v": 1, "active": False, "playing": False, "paused": False, "id": "", "title": "", "artist": "", "pos": 0.0, "dur": 0.0, "vol": 0, "mode": 2, "fav": False, "t": time.time()}
        self.jobs = queue.Queue()
        self.fails = {}
        self.lock = threading.Lock()
        self.texts = texts or PAGE_TEXTS["en"]
        self.colors = page_colors or {}
        self.on_request = None

    def check_token(self, given):
        if not isinstance(given, str) or not given:
            return False
        return hmac.compare_digest(given.encode("utf-8", "replace"), self.token.encode("utf-8"))

    def blocked(self, ip):
        """True while this client has failed too often in the last minute."""
        now = time.time()
        with self.lock:
            f = self.fails.get(ip)
            if not f:
                return False
            if now - f[1] > FAIL_WINDOW:
                self.fails.pop(ip, None)
                return False
            return f[0] >= MAX_FAILS

    def fail(self, ip):
        now = time.time()
        with self.lock:
            f = self.fails.get(ip)
            if not f or now - f[1] > FAIL_WINDOW:
                self.fails[ip] = [1, now]
            else:
                f[0] += 1
            if len(self.fails) > 500:                              # the table can never grow without end
                for k in sorted(self.fails, key=lambda k: self.fails[k][1])[:250]:
                    self.fails.pop(k, None)

    def submit(self, kind, arg, wait=True):
        """Called by a web thread: hands a job to the window. With wait the answer comes back (None when the window did not answer in time)."""
        job = Job(kind, arg)
        self.jobs.put(job)
        if not wait:
            return {"ok": True}
        return job.result if job.done.wait(JOB_WAIT) else None

    def drain(self, handler, limit=8):
        """Called by the window's thread (every 0.2 s): runs the waiting jobs through handler(kind, arg)."""
        n = 0
        while n < limit:
            try:
                job = self.jobs.get_nowait()
            except queue.Empty:
                break
            n += 1
            try:
                job.result = handler(job.kind, job.arg)
            except Exception as e:
                log("remote job %s: %r" % (job.kind, e))
                job.result = {"ok": False, "error": "failed"}
            job.done.set()
        return n


def host_ok(host):
    """The Host header must name an address (or localhost): a web name is how a hostile page tries to reach a local server (DNS rebinding)."""
    if host is None or host == "":
        return True
    h = host.strip()
    if h.startswith("["):
        h = h[1:h.find("]")] if "]" in h else h
    else:
        h = h.rsplit(":", 1)[0] if h.count(":") == 1 else h
    if h.lower() == "localhost":
        return True
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


CMDS = {"toggle": None, "next": None, "prev": None, "mode": None, "fav": None, "vol": (0, 100), "seek": (0, 86400 * 4)}


def _safe(fn):
    def wrapper(self):
        try:
            fn(self)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception as e:
            log("remote request: %r" % (e,))
            try:
                self._err(500, "failed")
            except Exception:
                pass
    wrapper.__name__ = fn.__name__
    return wrapper


def make_handler(hub):
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "Rofpalys"
        sys_version = ""
        timeout = 8

        def log_message(self, fmt, *args):
            pass

        # ---- answers
        def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Connection", "close")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _err(self, code, msg):
            self._send(code, {"ok": False, "error": msg})

        def _ip(self):
            return self.client_address[0] if self.client_address else "?"

        def _auth(self, allow_query):
            """True when the request carries the token (header X-Token; the query t=... only where allowed: the page and the cover image, which cannot set headers)."""
            ip = self._ip()
            if hub.blocked(ip):
                self._send(429, {"ok": False, "error": "too many attempts"}, extra={"Retry-After": "30"})
                return False
            tok = self.headers.get("X-Token")
            if tok is None and allow_query:
                tok = (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("t") or [None])[0]
            if hub.check_token(tok):
                return True
            hub.fail(ip)
            self._send(401, {"ok": False, "error": "token"})
            return False

        def _common(self):
            if len(self.path) > 600:
                self._err(414, "too long")
                return None
            if not host_ok(self.headers.get("Host")):
                self._err(421, "host")
                return None
            return urllib.parse.urlsplit(self.path)

        # ---- GET
        @_safe
        def do_GET(self):
            u = self._common()
            if u is None:
                return
            q = urllib.parse.parse_qs(u.query)
            if u.path in ("/", "/index.html"):
                if not self._auth(True):
                    return
                nonce = secrets.token_urlsafe(12)
                csp = "default-src 'none'; script-src 'nonce-%s'; style-src 'nonce-%s'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'" % (nonce, nonce)
                self._send(200, render_page(hub, nonce), "text/html; charset=utf-8", {"Content-Security-Policy": csp})
                return
            if not u.path.startswith("/api/"):
                self._err(404, "not found")
                return
            if not self._auth(u.path == "/api/cover"):
                return
            if u.path == "/api/state":
                self._send(200, hub.snapshot)
            elif u.path == "/api/search":
                text = re.sub(r"[\x00-\x1f\x7f]", " ", (q.get("q") or [""])[0])[:80].strip()
                res = hub.submit("search", text) if text else {"ok": True, "items": []}
                self._send(200, res) if res is not None else self._err(504, "busy")
            elif u.path == "/api/list":
                name = (q.get("name") or [""])[0]
                if name not in ("favorites", "recent", "top"):
                    self._err(400, "list")
                    return
                res = hub.submit("list", name)
                self._send(200, res) if res is not None else self._err(504, "busy")
            elif u.path == "/api/cover":
                res = hub.submit("cover", None)
                if res is None:
                    self._err(504, "busy")
                elif not res.get("data"):
                    self._err(404, "no cover")
                else:
                    self._send(200, res["data"], res.get("type", "image/jpeg"))
            else:
                self._err(404, "not found")

        do_HEAD = do_GET

        # ---- POST (commands): the token must come in the header, so a page of another web site cannot send one
        @_safe
        def do_POST(self):
            u = self._common()
            if u is None:
                return
            if u.path not in ("/api/cmd", "/api/play"):
                self._err(404, "not found")
                return
            if not self._auth(False):
                return
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                self._err(415, "json")
                return
            try:
                n = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                n = -1
            if n < 0 or n > MAX_BODY:
                self._err(413, "too large")
                return
            try:
                body = json.loads(self.rfile.read(n).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("not an object")
            except (ValueError, UnicodeDecodeError, OSError):
                self._err(400, "json")
                return
            if u.path == "/api/play":
                sid = body.get("id")
                if not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f]{12}", sid):
                    self._err(400, "id")
                    return
                res = hub.submit("play", sid)
                if res is None:
                    self._err(504, "busy")
                else:
                    self._send(200 if res.get("ok") else 404, res)
                return
            cmd = body.get("cmd")
            if not isinstance(cmd, str) or cmd not in CMDS:
                self._err(400, "cmd")
                return
            val = body.get("value")
            rng = CMDS[cmd]
            if rng is not None:
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not rng[0] <= val <= rng[1]:
                    self._err(400, "value")
                    return
            else:
                val = None
            hub.submit("cmd", {"cmd": cmd, "value": val}, wait=False)
            self._send(200, {"ok": True})

        def do_PUT(self):
            self._err(405, "method")

        do_DELETE = do_PATCH = do_OPTIONS = do_PUT

    return Handler


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 16


def serve(hub, host="127.0.0.1", port=DEFAULT_PORT, tries=10):
    """(server, port): a server on the first free port from `port` on, already running in a daemon thread. Raises OSError when none is free."""
    last = None
    for p in range(port, port + tries):
        try:
            srv = Server((host, p), make_handler(hub))
        except OSError as e:
            last = e
            continue
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.3}, name="rofpalys-remote", daemon=True).start()
        return srv, srv.server_address[1]
    raise last or OSError("no free port")


def stop(srv):
    try:
        srv.shutdown()
        srv.server_close()
    except Exception:
        pass


# ---------------------------------------------------------------- the page
def page_colors(P, lg):
    st = P.get("STYLE", {})
    shape = st.get("shape", "round")
    fam = ", ".join('"%s"' % f for f in (tuple(st.get("ui", ())) + ("DejaVu Sans",))) + ", system-ui, sans-serif"
    return {"bg": P["BLK"], "panel": P["PNL"], "panel2": P["PNL2"], "hover": P["HOVER"], "txt": P["TXT"], "dim": P["DIM"], "accent": P["GOLD"], "grid": P["GRID"], "ok": P.get("OK", P["GOLD"]),
            "ink": P["BLK"], "radius": {"flat": "0px", "round": "14px", "pill": "20px", "cut": "0px"}.get(shape, "14px"), "cut": "1" if shape == "cut" else "0",
            "glow": "1" if st.get("glow") else "0", "font": fam, "caps": "uppercase" if st.get("caps") else "none", "lang": lg}


PAGE = r"""<!doctype html>
<html lang="%%lang%%"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex">
<meta name="theme-color" content="%%bg%%"><title>%%title%%</title>
<style nonce="%%nonce%%">
:root{--bg:%%bg%%;--panel:%%panel%%;--panel2:%%panel2%%;--hover:%%hover%%;--txt:%%txt%%;--dim:%%dim%%;--accent:%%accent%%;--grid:%%grid%%;--ok:%%ok%%;--ink:%%ink%%;--r:%%radius%%}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:var(--bg);color:var(--txt);font-family:%%font%%;font-size:16px}
body{min-height:100vh;display:flex;justify-content:center}
main{width:100%;max-width:520px;padding:14px 16px calc(24px + env(safe-area-inset-bottom))}
.card{background:var(--panel);border:1px solid var(--grid);border-radius:var(--r);padding:16px}
.cut{border-radius:0;clip-path:polygon(14px 0,100% 0,100% calc(100% - 14px),calc(100% - 14px) 100%,0 100%,0 14px)}
.glow{border-color:var(--accent);box-shadow:0 0 12px -2px var(--accent)}
#bar{display:none;margin-bottom:10px;padding:10px 14px;background:var(--panel2);border:1px solid var(--accent);border-radius:var(--r);color:var(--txt);font-size:14px}
#cover{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:var(--r);background:var(--panel2);display:block}
h1{font-size:22px;margin:16px 0 2px;text-transform:%%caps%%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#artist{color:var(--dim);margin:0 0 12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-transform:%%caps%%}
#prog{height:12px;background:var(--panel2);border-radius:99px;cursor:pointer;position:relative;touch-action:none}
#fill{position:absolute;left:0;top:0;bottom:0;width:0;background:var(--accent);border-radius:99px}
.times{display:flex;justify-content:space-between;color:var(--dim);font-size:13px;margin:6px 2px 10px;font-variant-numeric:tabular-nums}
.row{display:flex;align-items:center;justify-content:center;gap:14px;margin:6px 0}
button{font:inherit;color:var(--txt);background:var(--panel2);border:1px solid var(--grid);border-radius:var(--r);min-width:52px;height:52px;padding:0 14px;cursor:pointer;text-transform:%%caps%%}
button:active{background:var(--hover)}
button.big{width:76px;height:76px;border-radius:99px;background:var(--accent);color:var(--ink);border-color:var(--accent)}
button svg{width:26px;height:26px;fill:currentColor;display:block;margin:auto}
button.on{color:var(--accent);border-color:var(--accent)}
.vol{display:flex;align-items:center;gap:12px;margin:14px 2px 4px}.vol span{color:var(--dim);font-size:13px;min-width:34px;text-align:right}
input[type=range]{flex:1;accent-color:var(--accent);height:30px}
.tabs{display:flex;gap:8px;margin:18px 0 10px;flex-wrap:wrap}.tabs button{height:38px;min-width:0;font-size:14px}
input[type=search]{width:100%;height:46px;font:inherit;color:var(--txt);background:var(--panel2);border:1px solid var(--grid);border-radius:var(--r);padding:0 14px;outline:none}
input[type=search]:focus{border-color:var(--accent)}
ul{list-style:none;margin:10px 0 0;padding:0}
li{display:block;width:100%;text-align:left;padding:10px 12px;margin:0 0 6px;background:var(--panel2);border:1px solid var(--grid);border-radius:var(--r);cursor:pointer}
li:active{background:var(--hover)}li b{display:block;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}li small{color:var(--dim);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
li.cur b{color:var(--accent)}.empty{color:var(--dim);text-align:center;padding:14px 0}
</style></head><body><main>
<div id="bar" role="status"></div>
<div class="card %%cutclass%% %%glowclass%%">
<img id="cover" alt="" hidden>
<h1 id="title"></h1><p id="artist"></p>
<div id="prog" role="slider" aria-label="position"><div id="fill"></div></div>
<div class="times"><span id="pos">0:00</span><span id="dur">0:00</span></div>
<div class="row">
<button id="prev" aria-label="previous"><svg viewBox="0 0 24 24"><path d="M6 5h2v14H6zM20 5v14L9 12z"/></svg></button>
<button id="toggle" class="big" aria-label="play / pause"><svg id="ico" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></button>
<button id="next" aria-label="next"><svg viewBox="0 0 24 24"><path d="M16 5h2v14h-2zM4 5v14l11-7z"/></svg></button>
</div>
<div class="row"><button id="mode"></button><button id="fav" aria-label="favourite"><svg viewBox="0 0 24 24"><path d="M12 21s-8-5.2-8-11a4.6 4.6 0 0 1 8-3 4.6 4.6 0 0 1 8 3c0 5.800-8 11-8 11z"/></svg></button></div>
<div class="vol"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M3 9v6h4l5 4V5L7 9z"/></svg><input id="vol" type="range" min="0" max="100" step="1" aria-label="volume"><span id="volv">0</span></div>
</div>
<div class="tabs" id="tabs"></div>
<input id="q" type="search" autocomplete="off" autocapitalize="off" spellcheck="false">
<ul id="list"></ul>
</main>
<script nonce="%%nonce%%">
(function(){'use strict';
var T=new URLSearchParams(location.search).get('t')||'',L=%%texts%%,st=null,tlast=0,volHold=0,curId='',listName='favorites',pollT=null,qT=null,volT=null;
function $(i){return document.getElementById(i)}
function bar(t){var b=$('bar');if(t){b.textContent=t;b.style.display='block'}else{b.style.display='none'}}
function api(p,o){o=o||{};o.headers=Object.assign({'X-Token':T},o.headers||{});o.cache='no-store';
 return fetch(p,o).then(function(r){if(r.status===401){bar(L.bad_token);throw new Error('auth')}if(!r.ok)throw new Error('http '+r.status);return r.json()})}
function post(cmd,value){return api('/api/cmd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd:cmd,value:value})}).then(function(){setTimeout(poll,150)}).catch(function(){})}
function mmss(s){s=Math.max(0,Math.floor(s||0));var m=Math.floor(s/60),x=s%60;return m+':'+(x<10?'0':'')+x}
function draw(){if(!st)return;var pos=st.pos;if(st.playing)pos=Math.min(st.dur||1e9,st.pos+(Date.now()-tlast)/1000);
 $('pos').textContent=mmss(pos);$('dur').textContent=st.dur>0?mmss(st.dur):'--:--';$('fill').style.width=(st.dur>0?Math.min(100,100*pos/st.dur):0)+'%'}
function render(){if(!st)return;$('title').textContent=st.active?st.title:L.nothing;$('artist').textContent=st.active?st.artist:'';
 $('ico').innerHTML=st.playing?'<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>':'<path d="M8 5v14l11-7z"/>';
 $('mode').textContent=L.modes[st.mode]||'';$('fav').className=st.fav?'on':'';
 if(Date.now()>volHold){$('vol').value=st.vol;$('volv').textContent=st.vol}
 if(st.id!==curId){curId=st.id;var c=$('cover');if(st.id){c.hidden=false;c.src='/api/cover?t='+encodeURIComponent(T)+'&id='+st.id}else{c.hidden=true}markCur()}
 draw()}
function poll(){if(document.hidden)return;api('/api/state').then(function(s){st=s;tlast=Date.now();bar('');render()}).catch(function(e){if(String(e).indexOf('auth')<0)bar(L.lost)})}
function markCur(){var li=document.querySelectorAll('#list li');for(var i=0;i<li.length;i++)li[i].className=(li[i].dataset.id===curId)?'cur':''}
function fill(items){var ul=$('list');ul.textContent='';if(!items||!items.length){var e=document.createElement('div');e.className='empty';e.textContent=L.empty;ul.appendChild(e);return}
 items.forEach(function(it){var li=document.createElement('li'),b=document.createElement('b'),s=document.createElement('small');b.textContent=it.title;s.textContent=it.artist;li.appendChild(b);li.appendChild(s);li.dataset.id=it.id;
  li.addEventListener('click',function(){api('/api/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:it.id})}).then(function(){setTimeout(poll,250)}).catch(function(){})});ul.appendChild(li)});markCur()}
function load(name){listName=name;$('q').value='';var tb=document.querySelectorAll('#tabs button');for(var i=0;i<tb.length;i++)tb[i].className=(tb[i].dataset.n===name)?'on':'';
 api('/api/list?name='+name).then(function(r){fill(r.items)}).catch(function(){})}
function search(){var v=$('q').value.trim();if(!v){load(listName);return}api('/api/search?q='+encodeURIComponent(v)).then(function(r){fill(r.items)}).catch(function(){})}
['prev','next','toggle','mode','fav'].forEach(function(k){$(k).addEventListener('click',function(){post(k==='prev'?'prev':k==='next'?'next':k,null)})});
$('prog').addEventListener('click',function(e){if(!st||!(st.dur>0))return;var r=this.getBoundingClientRect();post('seek',Math.max(0,Math.min(1,(e.clientX-r.left)/r.width))*st.dur)});
$('vol').addEventListener('input',function(){var v=parseInt(this.value,10);$('volv').textContent=v;volHold=Date.now()+1500;clearTimeout(volT);volT=setTimeout(function(){post('vol',v)},120)});
$('q').placeholder=L.search;$('q').addEventListener('input',function(){clearTimeout(qT);qT=setTimeout(search,250)});
[['favorites',L.favorites],['recent',L.recent],['top',L.top]].forEach(function(t){var b=document.createElement('button');b.textContent=t[1];b.dataset.n=t[0];b.addEventListener('click',function(){load(t[0])});$('tabs').appendChild(b)});
document.addEventListener('visibilitychange',function(){if(!document.hidden)poll()});
setInterval(poll,1000);setInterval(draw,250);poll();load('favorites');
})();
</script></body></html>
"""


def render_page(hub, nonce):
    c = hub.colors or {}
    t = hub.texts
    out = PAGE
    for k, v in (("lang", c.get("lang", "en")), ("bg", c.get("bg", "#111111")), ("panel", c.get("panel", "#1a1a1a")), ("panel2", c.get("panel2", "#262626")), ("hover", c.get("hover", "#333333")),
                 ("txt", c.get("txt", "#eeeeee")), ("dim", c.get("dim", "#888888")), ("accent", c.get("accent", "#3ee0a0")), ("grid", c.get("grid", "#333333")), ("ok", c.get("ok", "#3ee0a0")),
                 ("ink", c.get("ink", "#000000")), ("radius", c.get("radius", "14px")), ("font", c.get("font", "system-ui, sans-serif")), ("caps", c.get("caps", "none")),
                 ("cutclass", "cut" if c.get("cut") == "1" else ""), ("glowclass", "glow" if c.get("glow") == "1" else ""), ("title", t.get("title", "Rofpalys Remote")), ("nonce", nonce)):
        out = out.replace("%%" + k + "%%", str(v).replace("<", "").replace(">", "").replace('"', "") if k not in ("font",) else str(v).replace("<", "").replace(">", ""))
    texts = json.dumps({k: v for k, v in t.items()}, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return out.replace("%%texts%%", texts)


# ---------------------------------------------------------------- the window side
def sniff_image(data):
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return ""


def placeholder_svg(title, P):
    letter = (str(title).strip()[:1] or "?").upper()
    letter = letter if letter.isalnum() else "♪"
    letter = letter.replace("&", "").replace("<", "").replace(">", "")
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect width="200" height="200" fill="%s"/><rect y="133" width="200" height="67" fill="%s" opacity=".55"/>'
            '<text x="100" y="128" text-anchor="middle" font-family="sans-serif" font-size="96" font-weight="700" fill="%s">%s</text></svg>' % (P["PNL2"], P["BLK"], P["GOLD"], letter)).encode("utf-8")


class Mixin:
    # ---- the player, as the web threads may see it (all of this runs in the Tk thread)
    def rm_ident(self, path):
        sid = song_id(path)
        if len(self.rm_ids) > 3000:
            self.rm_ids.clear()
        self.rm_ids[sid] = path
        return sid

    def rm_item(self, path):
        it = self.song_item(path)
        return {"id": self.rm_ident(path), "title": it["title"], "artist": it["sub"]}

    def rm_snap(self):
        p = E.playing_song_name
        t, a = "", ""
        if p:
            it = self.song_item(p)
            t, a = it["title"], it["sub"]
        self.rm_hub.snapshot = {"v": 1, "active": bool(p), "playing": bool(E.is_playing and not E.is_paused), "paused": bool(E.is_paused), "id": self.rm_ident(p) if p else "", "title": t, "artist": a,
                                "pos": float(E.current_time_seconds or 0.0), "dur": float(E.total_time_seconds or 0.0) if getattr(E, "duration_known", True) else 0.0, "vol": int(E.volume), "mode": int(E.play_mode) % 5,
                                "fav": bool(p and p in E.favorites), "t": time.time()}

    def rm_job(self, kind, arg):
        if kind == "cmd":
            c, v = arg["cmd"], arg["value"]
            if c == "toggle":
                self.toggle()
            elif c == "next":
                self.step(1)
            elif c == "prev":
                self.step(-1)
            elif c == "mode":
                self.cycle_mode()
            elif c == "fav":
                if E.playing_song_name:
                    self.toggle_fav(E.playing_song_name)
            elif c == "vol":
                self.set_volume(int(round(v)))
            elif c == "seek":
                self.seek(float(v))
            self.rm_snap()
            if AN is not None:
                AN.note("remote_cmd", {"cmd": c})
            return {"ok": True}
        if kind == "play":
            path = self.rm_ids.get(arg)
            if not path or path not in set(E.songs_all):
                return {"ok": False, "error": "unknown song"}
            self.play(path)
            if AN is not None:
                AN.note("remote_cmd", {"cmd": "play"})
            return {"ok": True}
        if kind == "search":
            try:
                res = L.smart_search(arg, E.songs_all, self.cfg["stats"], E.favorites, 20)
            except Exception:
                res = []
            return {"ok": True, "items": [self.rm_item(p) for p, _s in res]}
        if kind == "list":
            songs = E.songs_all
            if arg == "favorites":
                paths = [p for p in songs if p in E.favorites][:60]
            elif arg == "top":
                st = self.cfg["stats"]
                paths = [p for p in sorted(songs, key=lambda p: -int((st.get(p) or {}).get("plays", 0) or 0)) if int((st.get(p) or {}).get("plays", 0) or 0) > 0][:40]
            else:
                paths, seen = [], set()
                have = set(songs)
                v = IN.view() if IN is not None else None
                for row in reversed(IN.recent_plays(v, 80) if v is not None else []):
                    if row[2] in have and row[2] not in seen:
                        seen.add(row[2])
                        paths.append(row[2])
                    if len(paths) >= 30:
                        break
            return {"ok": True, "items": [self.rm_item(p) for p in paths]}
        if kind == "cover":
            p = E.playing_song_name
            if not p:
                return {"data": b""}
            try:
                f = M.thumb(p, 512)
                if f and os.path.isfile(f) and os.path.getsize(f) <= 3 * 1024 * 1024:
                    with open(f, "rb") as fh:
                        data = fh.read()
                    typ = sniff_image(data)
                    if typ:
                        return {"data": data, "type": typ}
            except Exception:
                pass
            P = TH2.palette() if TH2 is not None else {k: globals()[k] for k in ("BLK", "PNL2", "GOLD")}
            return {"data": placeholder_svg(self.song_item(p)["title"], P), "type": "image/svg+xml"}
        return {"ok": False}

    def rm_poll(self):
        hub = self.rm_hub
        if hub is None:
            return
        hub.drain(self.rm_job)
        if time.time() >= self.rm_next_snap:
            self.rm_next_snap = time.time() + 0.5
            self.rm_snap()

    # ---- start / stop
    def rm_lang(self):
        return I18N.current()

    def rm_urls(self):
        if self.rm_srv is None:
            return []
        port = self.rm_port
        hosts = ["127.0.0.1"] + (lan_addresses() if self.rm_cfg["lan"] else [])
        return ["http://%s:%d/?t=%s" % (h, port, self.rm_cfg["token"]) for h in hosts]

    def rm_start(self):
        if self.rm_srv is not None:
            return True
        P = TH2.palette() if TH2 is not None else {k: globals()[k] for k in ("BLK", "PNL", "PNL2", "HOVER", "TXT", "DIM", "GOLD", "GRID")} | {"STYLE": dict(STYLE)}
        lg = self.rm_lang()
        hub = Hub(self.rm_cfg["token"], self.rm_cfg["lan"], page_texts(lg), page_colors(P, lg))
        try:
            srv, port = serve(hub, "0.0.0.0" if self.rm_cfg["lan"] else "127.0.0.1", self.rm_cfg["port"])
        except OSError as e:
            self.msg(self.T("rm_busy") % e)
            return False
        self.rm_hub, self.rm_srv, self.rm_port = hub, srv, port
        self.rm_ids = {}
        self.rm_snap()
        self.rm_cfg["enabled"] = True
        save_cfg(self.rm_cfg)
        if AN is not None:
            AN.note("remote_on", {"lan": self.rm_cfg["lan"]})
        return True

    def rm_stop(self, remember=True):
        srv, self.rm_srv, self.rm_hub = self.rm_srv, None, None
        if srv is not None:
            stop(srv)
        if remember:
            self.rm_cfg["enabled"] = False
            save_cfg(self.rm_cfg)

    def rm_restart(self):
        if self.rm_srv is not None:
            self.rm_stop(remember=False)
            self.rm_start()

    def rm_autostart(self):
        if self.rm_cfg["enabled"] and self.rm_srv is None:
            self.rm_start()

    def rm_set_lan(self, on):
        self.rm_cfg["lan"] = bool(on)
        save_cfg(self.rm_cfg)
        self.rm_restart()

    def rm_new_token(self):
        self.rm_cfg["token"] = new_token()
        save_cfg(self.rm_cfg)
        self.rm_restart()
        self.msg(self.T("rm_new_done"))

    def rm_restyle(self):
        """The page of a running remote follows a theme or language change: new colours and texts for the next load of the page."""
        if self.rm_hub is not None:
            lg = self.rm_lang()
            P = TH2.palette() if TH2 is not None else None
            if P is not None:
                self.rm_hub.colors = page_colors(P, lg)
            self.rm_hub.texts = page_texts(lg)

    # ---- the dialog
    def rm_close_dialog(self):
        w, self.rm_win = self.rm_win, None
        if w is not None:
            try:
                w.destroy()
            except Exception:
                pass

    def rm_dialog(self):
        self.rm_close_dialog()
        P = TH2.palette() if TH2 is not None else {k: globals()[k] for k in ("BLK", "PNL", "PNL2", "HOVER", "TXT", "DIM", "GOLD", "GRID", "OK")} | {"STYLE": dict(STYLE)}
        st = P.get("STYLE", {})
        fonts = look_fonts(self.root, 10)
        T = self.T
        top = tk.Toplevel(self.root)
        top.title(T("rm_title"))
        top.configure(bg=P["BLK"])
        top.resizable(False, False)
        try:
            top.transient(self.root)
        except Exception:
            pass
        self.rm_win = top
        fr = tk.Frame(top, bg=P["PNL"], padx=22, pady=18)
        fr.pack(fill="both", expand=True, padx=2, pady=2)
        on = self.rm_srv is not None
        tk.Label(fr, text=cap(T("rm_title")), bg=P["PNL"], fg=P["GOLD"], font=fonts["head"], anchor="w").pack(fill="x")
        tk.Label(fr, text=(T("rm_on") + "  -  " + T("rm_running") % self.rm_port) if on else T("rm_off"), bg=P["PNL"], fg=P["OK"] if on else P["DIM"], font=fonts["ui"], anchor="w").pack(fill="x", pady=(4, 10))

        def btn(parent, text, fn, accent=False):
            b = ShapeLabel(parent, text=cap(text), bg=P["GOLD"] if accent else P["PNL2"], fg=P["BLK"] if accent else P["TXT"], font=fonts["ui_b"], padx=14, pady=7, cursor="hand2", pbg=P["PNL"])
            b.bind("<Button-1>", lambda e: fn())
            return b
        row = tk.Frame(fr, bg=P["PNL"])
        row.pack(fill="x", pady=(0, 8))
        btn(row, T("rm_turn_off") if on else T("rm_turn_on"), lambda: (self.rm_stop() if on else self.rm_start(), self.rm_dialog()), accent=not on).pack(side="left", padx=(0, 8))
        btn(row, ("[x] " if self.rm_cfg["lan"] else "[ ] ") + T("rm_lan"), lambda: (self.rm_set_lan(not self.rm_cfg["lan"]), self.rm_dialog())).pack(side="left")
        if on:
            tk.Label(fr, text=T("rm_link"), bg=P["PNL"], fg=P["DIM"], font=fonts["small"], anchor="w").pack(fill="x", pady=(12, 2))
            for u in self.rm_urls():
                e = tk.Entry(fr, font=fonts["mono"], bg=P["PNL2"], fg=P["TXT"], relief="flat", bd=0, highlightthickness=1, highlightbackground=P["GRID"], readonlybackground=P["PNL2"], width=52)
                e.insert(0, u)
                e.configure(state="readonly")
                e.pack(fill="x", pady=2, ipady=4)
            row2 = tk.Frame(fr, bg=P["PNL"])
            row2.pack(fill="x", pady=(8, 0))
            btn(row2, T("rm_copy"), self.rm_copy).pack(side="left", padx=(0, 8))
            btn(row2, T("rm_new"), lambda: (self.rm_new_token(), self.rm_dialog())).pack(side="left", padx=(0, 8))
        tk.Label(fr, text=T("rm_note"), bg=P["PNL"], fg=P["DIM"], font=fonts["small"], anchor="w", justify="left", wraplength=470).pack(fill="x", pady=(14, 10))
        btn(fr, T("rm_close"), self.rm_close_dialog).pack(anchor="e")
        top.update_idletasks()                                          # in the middle of the window (a window manager that places it itself keeps its choice)
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - top.winfo_reqwidth()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - top.winfo_reqheight()) // 3)
            top.geometry("+%d+%d" % (x, y))
        except Exception:
            pass

    def rm_copy(self):
        urls = self.rm_urls()
        if not urls:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(urls[-1])
            self.msg(self.T("rm_copied"))
        except Exception:
            pass


def register(app):
    app.rm_cfg, app.rm_srv, app.rm_hub, app.rm_port, app.rm_ids, app.rm_next_snap, app.rm_win = load_cfg(), None, None, 0, {}, 0.0, None
    app.add_texts(**TEXTS)
    app.add_menu("rm_menu", lambda a: a.rm_dialog())
    app.add_poll(lambda a: a.rm_poll())
    app.add_build(lambda a: a.root.after(900, a.rm_autostart))
    app.add_relabel(lambda a: a.rm_restyle())
    if TH2 is not None:
        TH2.on_switch(lambda old, new, m: (app.rm_restyle(), app.rm_close_dialog()))


# END-OF-FILE rofpalys_gui_remote.py
