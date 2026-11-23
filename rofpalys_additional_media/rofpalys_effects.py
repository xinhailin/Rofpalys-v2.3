#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rofpalys - sound effects: presets, bass / treble / equalizer, speed and pitch, reverb, stereo width, 8D, voice characters
# Copyright (C) 2026 rofpalys-nagiryu
# License: GPL-3.0-or-later  (see: rofpalys --license)
"""No UI, no engine. Turns the chosen effects into command-line arguments for the player that is used.
Works with mpv (best) and ffplay. Other players (mpg123, afplay, PyGame ...) cannot apply effects and simply play normally.
The filters are the standard ffmpeg audio filters (equalizer, bass, treble, aecho, extrastereo, apulsator, afftfilt, vibrato, acompressor, dynaudnorm, alimiter, atempo).

What can be set (all of it is saved in the settings file):
  preset      a named starting point: it fills in the numbers below (normal, bass, superbass, vocal, treble, lofi, slowed, nightcore, 8d, cinema, club, acoustic)
  bass, treble, gain   in dB (bass -6..+15, treble -6..+12, gain -9..+9);  eq: five bands 60 Hz / 230 Hz / 910 Hz / 3.6 kHz / 14 kHz, -12..+12 dB each
  speed       0.5x .. 2x;  tape=True: the pitch follows the speed (slowed / nightcore), False: only the tempo changes;  pitch: -6..+6 semitones on top
  reverb      off / light / room / hall / cave;  reverb_mix 10..100 %
  width       stereo width 0..200 % (100 = as recorded, 0 = mono)
  eight_d     the sound walks around your head (use headphones)
  voice       a character: none, robot, man, woman, child, monster, alien, ghost, radio, megaphone, underwater
  lofi, night (night mode: quiet parts louder, loud parts softer), normalize
  enabled     False = bypass: everything is switched off but the settings stay, to hear the difference"""

PRESETS = ("normal", "bass", "superbass", "vocal", "treble", "lofi", "slowed", "nightcore", "8d", "cinema", "club", "acoustic")
REVERBS = ("off", "light", "room", "hall", "cave")
VOICES = ("none", "robot", "man", "woman", "child", "monster", "alien", "ghost", "radio", "megaphone", "underwater")
SPEEDS = (0.5, 0.75, 0.85, 1.0, 1.15, 1.25, 1.5, 2.0)
EQ_BANDS = (60, 230, 910, 3600, 14000)
LIMITS = {"bass": (-6, 15), "treble": (-6, 12), "gain": (-9, 9), "pitch": (-6, 6), "width": (0, 200), "reverb_mix": (10, 100), "speed": (0.5, 2.0), "eq": (-12, 12)}
SUPPORTED = ("mpv", "ffplay")
SR = 44100

# effect state (the engine saves these in the settings file)
preset, speed, reverb, normalize = "normal", 1.0, "off", False
bass, treble, gain, pitch, width, reverb_mix = 0, 0, 0, 0, 100, 50
eq = [0, 0, 0, 0, 0]
tape, eight_d, lofi, night, enabled, voice = False, False, False, False, True, "none"

_DEFAULTS = {"preset": "normal", "speed": 1.0, "reverb": "off", "normalize": False, "bass": 0, "treble": 0, "gain": 0, "pitch": 0, "width": 100, "reverb_mix": 50,
             "eq": [0, 0, 0, 0, 0], "tape": False, "eight_d": False, "lofi": False, "night": False, "voice": "none"}
_PRESET_VALUES = {
    "normal": {},
    "bass": {"bass": 8, "eq": [3, 2, 0, 0, 0], "gain": -2},
    "superbass": {"bass": 14, "eq": [6, 3, 0, 0, 0], "gain": -5},
    "vocal": {"eq": [-3, -1, 2, 4, 2]},
    "treble": {"treble": 7, "eq": [0, 0, 0, 2, 4]},
    "lofi": {"lofi": True, "reverb": "light", "reverb_mix": 30},
    "slowed": {"speed": 0.82, "tape": True, "reverb": "hall", "reverb_mix": 55},
    "nightcore": {"speed": 1.25, "tape": True},
    "8d": {"eight_d": True, "reverb": "light", "reverb_mix": 35},
    "cinema": {"bass": 4, "width": 160, "reverb": "room", "reverb_mix": 30, "eq": [2, 0, 0, 1, 2]},
    "club": {"bass": 6, "width": 130, "eq": [4, 2, 0, 1, 3], "gain": -3},
    "acoustic": {"eq": [2, 2, 1, 2, 3], "reverb": "room", "reverb_mix": 20},
}
# pitch ratio and what a voice adds to the sound
_VOICE = {
    "man": {"ratio": 0.84, "f": ["equalizer=f=140:t=q:w=1:g=3", "equalizer=f=4000:t=q:w=1:g=-2"]},
    "woman": {"ratio": 1.2, "f": ["equalizer=f=3000:t=q:w=1:g=2", "equalizer=f=150:t=q:w=1:g=-3"]},
    "child": {"ratio": 1.45, "f": ["equalizer=f=4500:t=q:w=1:g=3", "highpass=f=200"]},
    "monster": {"ratio": 0.62, "f": ["equalizer=f=90:t=q:w=1:g=4", "aecho=0.8:0.7:35:0.45"]},
    "alien": {"ratio": 1.3, "f": ["vibrato=f=7:d=0.45", "aecho=0.8:0.8:25:0.35"]},
    "ghost": {"ratio": 0.86, "f": ["tremolo=f=4:d=0.5", "aecho=0.8:0.88:90|180:0.45|0.3", "lowpass=f=6000"]},
    "robot": {"ratio": 1.0, "f": ["afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75"]},
    "radio": {"ratio": 1.0, "f": ["highpass=f=400", "lowpass=f=3200", "acompressor=threshold=0.1:ratio=6:makeup=3"]},
    "megaphone": {"ratio": 1.0, "f": ["highpass=f=500", "lowpass=f=3500", "volume=5dB", "aecho=0.8:0.6:12:0.4"]},
    "underwater": {"ratio": 1.0, "f": ["lowpass=f=700", "vibrato=f=4:d=0.3", "aecho=0.8:0.7:70:0.3"]},
}
_ECHO = {"light": ("aecho=0.8:%.2f:40:%.2f", 0.30), "room": ("aecho=0.8:%.2f:30|55:%.2f|%.2f", 0.35), "hall": ("aecho=0.8:%.2f:60|120:%.2f|%.2f", 0.40),
         "cave": ("aecho=0.8:%.2f:120|240|360:%.2f|%.2f|%.2f", 0.45)}


def supported(engine_name):
    return engine_name in SUPPORTED


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def to_dict():
    return {"preset": preset, "speed": speed, "reverb": reverb, "normalize": normalize, "bass": bass, "treble": treble, "gain": gain, "pitch": pitch, "width": width,
            "reverb_mix": reverb_mix, "eq": list(eq), "tape": tape, "eight_d": eight_d, "lofi": lofi, "night": night, "enabled": enabled, "voice": voice}


def update(**kw):
    """Set any of the values (checked and clamped; unknown names and wrong values are ignored). Returns the names that really changed."""
    g, changed = globals(), []

    def put(name, value):
        if g[name] != value:
            g[name] = value
            changed.append(name)
    for k, v in kw.items():
        try:
            if k == "preset" and v in PRESETS:
                put(k, v)
            elif k == "reverb" and v in REVERBS:
                put(k, v)
            elif k == "voice" and v in VOICES:
                put(k, v)
            elif k == "speed":
                put(k, round(clamp(float(v), *LIMITS["speed"]), 3))
            elif k in ("bass", "treble", "gain", "pitch", "reverb_mix", "width"):
                put(k, int(round(clamp(float(v), *LIMITS[k]))))
            elif k == "eq" and isinstance(v, (list, tuple)) and len(v) == 5:
                put(k, [int(round(clamp(float(x), *LIMITS["eq"]))) for x in v])
            elif k in ("normalize", "tape", "eight_d", "lofi", "night", "enabled"):
                put(k, bool(v))
        except (TypeError, ValueError):
            continue
    return changed


def from_dict(d):
    """Load the saved state. An old file (only preset / speed / reverb / normalize) works too: its preset is filled in first."""
    reset()
    if not isinstance(d, dict):
        return
    d = dict(d)
    pr = d.pop("preset", "normal")
    if "eq" not in d:                                                 # an old file
        if pr in PRESETS and pr != "normal":
            apply_preset(pr)
        d = {k: v for k, v in d.items() if k in ("speed", "reverb", "normalize") and v != _DEFAULTS[k]}
    update(**d)
    if pr in PRESETS:
        globals()["preset"] = pr


def apply_preset(name):
    """A preset fills in the numbers (everything else goes back to normal); the voice and the on / off switch stay."""
    if name not in PRESETS:
        return False
    keep_voice, keep_on = voice, enabled
    reset()
    update(**_PRESET_VALUES[name])
    globals()["preset"] = name
    update(voice=keep_voice, enabled=keep_on)
    return True


def effective():
    """(speed, tape, reverb): what the engine needs to keep the clock right."""
    if not enabled:
        return 1.0, False, "off"
    return speed, tape, reverb


def is_active():
    if not enabled:
        return False
    return (abs(speed - 1.0) > 0.01 or reverb != "off" or normalize or bass or treble or gain or pitch or width != 100 or any(eq) or eight_d or lofi or night or voice != "none")


def pitch_ratio():
    """The pitch change that is NOT caused by the speed: the voice character and the pitch slider together."""
    r = _VOICE.get(voice, {}).get("ratio", 1.0) * (2.0 ** (pitch / 12.0))
    return clamp(r, 0.5, 2.0)


def _reverb_filter():
    if reverb not in _ECHO:
        return ""
    fmt, base = _ECHO[reverb]
    m = reverb_mix / 100.0
    n = fmt.count("%.2f") - 1
    decays = tuple(clamp(base * (0.35 + 1.3 * m) * (0.78 ** i), 0.05, 0.9) for i in range(n))
    return fmt % ((clamp(0.55 + 0.35 * m, 0.4, 0.92),) + decays)


def _atempo(t):
    """atempo takes 0.5 .. 2.0 each: a bigger change is a chain."""
    out = []
    while t > 2.0:
        out.append("atempo=2.0")
        t /= 2.0
    while t < 0.5:
        out.append("atempo=0.5")
        t /= 0.5
    if abs(t - 1.0) > 0.001:
        out.append("atempo=%.4f" % t)
    return out


def filters(for_ffplay=False):
    """List of ffmpeg audio filters for the current settings, in the order they are applied."""
    if not enabled:
        return []
    f = []
    ratio = pitch_ratio()
    sp, is_tape, _rv = effective()
    if for_ffplay:                                                    # ffplay has no speed option: the filters do speed and pitch
        p = ratio * (sp if is_tape else 1.0)
        t = sp / p
    else:                                                             # mpv does the speed itself (--speed); the filters only do the pitch of voice / slider
        p, t = ratio, 1.0 / ratio
    if abs(p - 1.0) > 0.005:
        f += ["aresample=%d" % SR, "asetrate=%d" % round(SR * p), "aresample=%d" % SR]   # a known sample rate first: asetrate works on it
    if abs(p - 1.0) > 0.005 or for_ffplay:
        f += _atempo(t)                                               # the pitch changed, the tempo must stay (or become the speed)
    if voice in _VOICE:
        f += _VOICE[voice]["f"]
    if lofi:
        f += ["highpass=f=120", "lowpass=f=4500", "acompressor=threshold=0.15:ratio=3"]
    if bass:
        f.append("bass=g=%d:f=100:w=0.7" % bass)
    if treble:
        f.append("treble=g=%d:f=8000:w=0.7" % treble)
    for hz, g in zip(EQ_BANDS, eq):
        if g:
            f.append("equalizer=f=%d:t=q:w=1:g=%d" % (hz, g))
    if width != 100:
        f.append("extrastereo=m=%.2f" % (width / 100.0))
    if eight_d:
        f.append("apulsator=mode=sine:hz=0.18:amount=0.9")
    rv = _reverb_filter()
    if rv:
        f.append(rv)
    if night:
        f.append("acompressor=threshold=0.08:ratio=4:attack=20:release=250:makeup=3")
    if normalize:
        f.append("dynaudnorm=f=150:g=15")
    if gain:
        f.append("volume=%ddB" % gain)
    boost = max(0, bass) + max(0, treble) + max(0, gain) + sum(x for x in eq if x > 0)
    if boost or voice in ("megaphone", "monster") or night:
        f.append("alimiter=limit=0.95:level=0")                        # nothing can clip, however much is boosted
    return f


def speed_for(engine_name):
    """How fast the song really plays with this player (1.0 if it cannot change speed). The engine needs it to keep the clock right."""
    if engine_name in SUPPORTED and enabled:
        return clamp(effective()[0], 0.5, 2.0)
    return 1.0


def args_for(engine_name):
    """Extra arguments that go before the file name."""
    if not is_active() or engine_name not in SUPPORTED:
        return []
    sp, is_tape, _ = effective()
    if engine_name == "mpv":
        a = []
        if abs(sp - 1.0) > 0.01:
            a += ["--speed=%.3f" % sp, "--audio-pitch-correction=%s" % ("no" if is_tape else "yes")]
        f = filters()
        if f:
            a.append("--af=lavfi=[%s]" % ",".join(f))
        return a
    f = filters(for_ffplay=True)                        # ffplay
    return ["-af", ",".join(f)] if f else []


def label():
    if not is_active():
        return "off" if enabled else "bypass"
    parts = []
    if preset != "normal":
        parts.append(preset)
    if voice != "none":
        parts.append(voice)
    sp = effective()[0]
    if abs(sp - 1.0) > 0.01 and preset not in ("slowed", "nightcore"):
        parts.append("%.2gx" % sp)
    if bass:
        parts.append("bass %+d" % bass)
    if reverb != "off" and preset != "slowed":
        parts.append("reverb")
    if eight_d and preset != "8d":
        parts.append("8D")
    if normalize:
        parts.append("norm")
    return " + ".join(parts) or "custom"


def cycle_preset():
    return _cycle(PRESETS, preset)


def _cycle(seq, cur):
    n = seq[(seq.index(cur) + 1) % len(seq)] if cur in seq else seq[0]
    apply_preset(n)
    return n


def reset():
    g = globals()
    for k, v in _DEFAULTS.items():
        g[k] = list(v) if isinstance(v, list) else v
    g["enabled"] = True


# END-OF-FILE rofpalys_effects.py
