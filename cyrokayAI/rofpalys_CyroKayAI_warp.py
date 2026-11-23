#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - CyroKayAI warp: make the lyrics FOLLOW THE RECORDING (one shift for the whole song + a slower / faster clock), by force
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""The lyrics of Musixmatch (or any lyric file) were timed against ONE version of the song. The recording you play is another version of it:
the YouTube video starts 5 s earlier, the song is 5:30 where the lyrics say 5:25, the voice comes in at 0:10 where the first line says 0:05.
The recording is always right, so the lyrics are bent until they sit on it:

  1. a GLOBAL fit of  t_recording = a + (1 + b) * t_lyrics   (a = one shift in seconds, b = how much slower / faster the lyric clock ran, up to +-5 %).
     Every line group votes with how much voice is under it (and how little voice is where the lyric file says nobody sings); the (a, b) that
     most lines agree on wins. A stretch is only believed when it is clearly better than a plain shift (otherwise b stays 0 and nothing changes).
  2. rofpalys_CyroKayAI_lyric.py then places every line on the voice around that line (small shifts, jumps for extra / missing sections, snapping to
     the voice onsets) - the same solver as before, but now starting from lyrics that already have the right length.
  3. FORCE: when the audio gives no clear answer (confidence < 20 %), the first line is still put on the first singing that starts near it,
     instead of leaving the file's own times (a line is never invented: no singing in the audio = the file's times stay).

No speech recognition: this is the same measurement of 'is there a voice' that the rest of CyroKayAI uses. Needs numpy for step 1 (without numpy only
steps 2 and 3 run). The functions get the lyric module as an argument (L) so this file does not import it (it imports this one)."""
import math

try:
    import numpy as np
except Exception:                                   # no numpy: no global stretch fit, the rest of CyroKayAI still works
    np = None


__version__ = "1.0"
MAX_STRETCH = 0.05                                  # the lyric clock may run up to 5 % slower / faster than the recording
B_STEP = 0.001                                      # coarse grid of the stretch (0.1 % = 0.33 s over a 5:30 song)
A_STEP = 0.2                                        # coarse grid of the shift (s)
MIN_GAIN = 0.004                                    # a stretch must raise the average voice contrast under the lines by this much to be believed (plain shift: gain 0)
MIN_B = 0.0015                                      # ... and be at least this big (0.6 s over 5:30)
MIN_LEVEL = 0.12                                    # ... and the lines must then really sit on a voice (average contrast)
RESIDUAL = 4.0                                      # after the global fit the line solver only searches +-4 s around it


def fit_warp(L, sung, vocal, limit=20.0, max_stretch=MAX_STRETCH):
    """The global shift + stretch. L = rofpalys_CyroKayAI_lyric (the voice scoring lives there), sung = the sung lines [{'t', 'dur', ...}],
    vocal = the vocal curve of the recording, limit = how far (s) the lyrics may be shifted.
    -> None (a plain shift is as good: nothing to bend) or {'a', 'b', 'gain', 'level', 'stretch_s', 'a0'}:  t_rec = a + (1 + b) * t_lyric."""
    if np is None or len(sung) < 6 or max_stretch < MIN_B:
        return None
    n = len(vocal)
    if n < 10:
        return None
    P = np.concatenate(([0.0], np.cumsum(np.asarray(vocal, dtype=np.float64))))
    gm = P[-1] / max(1, n)
    groups = L._groups(sung)
    if len(groups) < 6:
        return None
    gaps_l = L._group_gaps(sung, groups)
    ivs = [[(sung[i]["t"], sung[i]["t"] + sung[i]["dur"]) for i in idxs] for idxs in groups]
    W = np.array([sum(sung[i]["dur"] for i in idxs) for idxs in groups], dtype=np.float64)
    tg = np.array([(v[0][0] + v[-1][1]) / 2.0 for v in ivs], dtype=np.float64)
    W_tot = float(W.sum())
    if W_tot <= 0:
        return None
    t_last = float(tg.max())
    K = int(math.ceil((limit + max_stretch * t_last + 1.0) / A_STEP))
    offs = (np.arange(2 * K + 1) - K) * A_STEP
    table = np.stack([L._gscore_vec(P, n, ivs[g], gaps_l[g], gm, offs) for g in range(len(groups))])      # groups x shifts
    ka = int(limit / A_STEP)
    a_idx = np.arange(-ka, ka + 1)
    gi = np.arange(len(groups))[:, None]
    nb = max(1, int(max_stretch / B_STEP + 1e-9))
    bs = np.arange(-nb, nb + 1) * B_STEP                                     # symmetric around 0 (b = 0 is the 'plain shift' the stretch must beat)
    best, j0 = None, None
    for b in bs:
        sh = np.round(b * tg / A_STEP).astype(int)
        idx = np.clip(K + a_idx[None, :] + sh[:, None], 0, 2 * K)
        J = (table[gi, idx] * W[:, None]).sum(0)
        J = J - 0.05 * W_tot * np.abs(a_idx * A_STEP) / limit - 0.02 * W_tot * abs(b) / max_stretch          # a small pull towards 'no shift, no stretch'
        k = int(np.argmax(J))
        if abs(b) < 1e-9:
            j0 = (float(J[k]), float(a_idx[k] * A_STEP))
        if best is None or J[k] > best[0]:
            best = (float(J[k]), float(b), float(a_idx[k] * A_STEP))
    if best is None or j0 is None:
        return None
    # fine search around the winner: shift +-0.4 s (0.05 s), stretch +-0.0016 (0.0002): the coarse winner sits on a plateau, the true stretch may be a step away
    cands = [(best[2] + da * 0.05, best[1] + db * 0.0002) for da in range(-8, 9) for db in range(-8, 9)]
    ca = np.array([c[0] for c in cands])
    cb = np.array([c[1] for c in cands])
    tot = np.zeros(len(cands))
    for g in range(len(groups)):
        tot += W[g] * L._gscore_vec(P, n, ivs[g], gaps_l[g], gm, ca + cb * tg[g])
    tot -= 0.05 * W_tot * np.abs(ca) / limit + 0.02 * W_tot * np.abs(cb) / max_stretch
    k = int(np.argmax(tot))
    a, b = float(ca[k]), float(cb[k])
    gain = (float(tot[k]) - j0[0]) / W_tot
    level = float(tot[k]) / W_tot
    if abs(b) < MIN_B or gain < MIN_GAIN or level < MIN_LEVEL:
        return None
    return {"a": round(a, 3), "b": round(b, 5), "gain": round(gain, 3), "level": round(level, 3), "stretch_s": round(b * t_last, 2), "a0": round(j0[1], 2)}


def apply(sung, w):
    """The sung lines moved by the global fit (copies; the originals stay). t_new = a + (1 + b) * t, the length of a line stretches with it."""
    a, b = w["a"], w["b"]
    out = []
    for it in sung:
        c = dict(it)
        c["t"] = a + (1.0 + b) * it["t"]
        c["dur"] = it["dur"] * (1.0 + b)
        out.append(c)
    return out


def total(sung, residual, w):
    """The seconds to ADD to each ORIGINAL lyric time: the global fit plus what the line solver found on top of it (residual, per line)."""
    return [w["a"] + w["b"] * it["t"] + r for it, r in zip(sung, residual)]


def force_start(A, t0, limit):
    """The audio gave no clear answer for the lines. Put the FIRST line on the first singing that starts within `limit` seconds of it (the singing
    start that is nearest to where the lyric file says the voice comes in) -> the shift in seconds, or None when the recording has no singing there.
    t0 = the time of the first sung line in the lyric file."""
    spans = [(a, b) for a, b in (getattr(A, "sing", None) or []) if b - a >= 1.5 and abs(a - t0) <= limit]
    if not spans:
        return None
    a = min(spans, key=lambda ab: (abs(ab[0] - t0), ab[0]))[0]
    return round(a - t0, 2)


# END-OF-FILE rofpalys_CyroKayAI_warp.py
