#!/usr/bin/env python3
"""
FF8 Music Volume - lower or mute the background music in Final Fantasy VIII
(2013 / Steam re-release), without touching sound effects, graphics, or controls.

How it works: it reads YOUR OWN installed game's music - the DirectMusic soundbank
(FF8.dls) plus the streamed .wav tracks - makes quieter copies by scaling the audio
samples, and writes them back into your game. Your originals are backed up once and
can be restored at any time. No game audio ships with this tool; it is generated from
the files you already own.

Usage (double-click "FF8 Music Volume.bat", or run this directly):
    python ff8_music_volume.py                 # interactive menu
    python ff8_music_volume.py --level 20      # set music to 20% and exit
    python ff8_music_volume.py --restore       # restore originals (100%)
    python ff8_music_volume.py --game "D:\\path\\to\\FINAL FANTASY VIII"

Standard library only - no third-party packages required.
"""
import os, sys, struct, array, shutil, argparse

LEVELS = {"off": 0.0, "5": 0.05, "10": 0.10, "20": 0.20, "40": 0.40, "70": 0.70, "100": 1.0}
MENU = [("1", "Off / silent", "off"), ("2", "5%  (barely there)", "5"), ("3", "10%", "10"),
        ("4", "20%", "20"), ("5", "40%", "40"), ("6", "70%", "70"),
        ("7", "Restore original music (100%)", "100")]


# ---------- audio scaling (float32, matching the game's own bake) ----------
def f32(x):
    """Round a Python float to 32-bit float precision (matches the original bake)."""
    return struct.unpack('f', struct.pack('f', float(x)))[0]


def _table16(factor):
    """Lookup table mapping every signed 16-bit sample to its scaled value."""
    ff = f32(factor)
    t = array.array('h', bytes(2 * 65536))
    for s in range(-32768, 32768):
        v = round(f32(f32(s) * ff))
        t[s & 0xffff] = -32768 if v < -32768 else 32767 if v > 32767 else int(v)
    return t


def _table8(factor):
    """Lookup table for unsigned 8-bit samples (centered on 128)."""
    ff = f32(factor)
    t = bytearray(256)
    for s in range(256):
        v = round(f32((f32(s) - f32(128)) * ff)) + 128
        t[s] = 0 if v < 0 else 255 if v > 255 else int(v)
    return bytes(t)


def _scale16(raw, t16):
    n = (len(raw) // 2) * 2
    a = array.array('h')
    a.frombytes(raw[:n])
    for i in range(len(a)):
        a[i] = t16[a[i] & 0xffff]
    return a.tobytes() + raw[n:]


def _scale_data(raw, bits, t16, t8):
    return _scale16(raw, t16) if bits == 16 else raw.translate(t8)


def scale_wav(buf, t16, t8):
    """Return a copy of a PCM WAV with its sample data scaled; headers untouched."""
    out = bytearray(buf)
    bits = 16
    p = 12
    while p + 8 <= len(buf):
        cid = buf[p:p + 4]
        sz = struct.unpack_from('<I', buf, p + 4)[0]
        b = p + 8
        if cid == b'fmt ':
            bits = struct.unpack_from('<H', buf, b + 14)[0]
        elif cid == b'data':
            out[b:b + sz] = _scale_data(bytes(buf[b:b + sz]), bits, t16, t8)
        p = b + sz + (sz & 1)
    return bytes(out)


def scale_dls(buf, t16, t8):
    """Return a copy of a DLS soundbank with every wave's sample data scaled."""
    out = bytearray(buf)

    def walk(off, end):
        p = off
        while p + 8 <= end:
            cid = buf[p:p + 4]
            sz = struct.unpack_from('<I', buf, p + 4)[0]
            b = p + 8
            if cid == b'LIST':
                if buf[b:b + 4] == b'wave':
                    q = b + 4
                    bits = 16
                    dat = None
                    while q + 8 <= b + sz:
                        s2 = buf[q:q + 4]
                        z2 = struct.unpack_from('<I', buf, q + 4)[0]
                        sb = q + 8
                        if s2 == b'fmt ':
                            bits = struct.unpack_from('<H', buf, sb + 14)[0]
                        elif s2 == b'data':
                            dat = (sb, z2, bits)
                        q = sb + z2 + (z2 & 1)
                    if dat:
                        sb, z2, bits = dat
                        out[sb:sb + z2] = _scale_data(bytes(buf[sb:sb + z2]), bits, t16, t8)
                walk(b + 4, b + sz)
            p = b + sz + (sz & 1)

    walk(12, len(buf))
    return bytes(out)


# ---------- locating the game + file operations ----------
HERE = os.path.dirname(os.path.abspath(__file__))
PATHFILE = os.path.join(HERE, "gamepath.txt")
DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VIII"


def is_game(d):
    return bool(d) and os.path.isfile(os.path.join(d, "FF8_Launcher.exe"))


def _remember(d):
    try:
        with open(PATHFILE, "w") as fh:
            fh.write(d)
    except OSError:
        pass


def find_game(cli):
    saved = None
    if os.path.isfile(PATHFILE):
        with open(PATHFILE) as fh:
            saved = fh.read().strip()
    for cand in (cli, saved, DEFAULT_GAME):
        if is_game(cand):
            _remember(cand)
            return cand
    while True:
        d = input("\nPaste your FINAL FANTASY VIII folder path (blank to cancel): ").strip().strip('"')
        if not d:
            return None
        if is_game(d):
            _remember(d)
            return d
        print("  That folder has no FF8_Launcher.exe in it. Let's try again.")


def paths(game):
    return (os.path.join(game, "Data", "Music", "dmusic"),
            os.path.join(game, "Data", "Music", "stream"),
            os.path.join(game, "_FF8Tools-backup", "music-original"))


def ensure_backup(game):
    dmusic, stream, bk = paths(game)
    if os.path.isfile(os.path.join(bk, "done.flag")):
        return True
    src_dls = os.path.join(dmusic, "FF8.dls")
    if not os.path.isfile(src_dls):
        print("  Could not find the game's music (FF8.dls). Is this the right folder?")
        return False
    os.makedirs(os.path.join(bk, "stream"), exist_ok=True)
    print("  Backing up your current music once...")
    shutil.copy2(src_dls, os.path.join(bk, "FF8.dls"))
    if os.path.isdir(stream):
        for w in os.listdir(stream):
            if w.lower().endswith(".wav"):
                shutil.copy2(os.path.join(stream, w), os.path.join(bk, "stream", w))
    with open(os.path.join(bk, "done.flag"), "w") as fh:
        fh.write("ok")
    return True


def apply_level(game, key):
    if key == "100":
        return restore(game)
    if not ensure_backup(game):
        return
    dmusic, stream, bk = paths(game)
    factor = LEVELS[key]
    shown = "Off" if key == "off" else key + "%"
    print("  Building music at %s ... (a few seconds)" % shown)
    t16 = _table16(factor)
    t8 = _table8(factor)
    with open(os.path.join(bk, "FF8.dls"), "rb") as fh:
        src = fh.read()
    with open(os.path.join(dmusic, "FF8.dls"), "wb") as fh:
        fh.write(scale_dls(src, t16, t8))
    bstream = os.path.join(bk, "stream")
    if os.path.isdir(bstream):
        for w in os.listdir(bstream):
            if w.lower().endswith(".wav"):
                with open(os.path.join(bstream, w), "rb") as fh:
                    src = fh.read()
                with open(os.path.join(stream, w), "wb") as fh:
                    fh.write(scale_wav(src, t16, t8))
    print("  Done. Start the game to hear it.")


def restore(game):
    dmusic, stream, bk = paths(game)
    if not os.path.isfile(os.path.join(bk, "done.flag")):
        print("  No backup yet - your music is already the original.")
        return
    shutil.copy2(os.path.join(bk, "FF8.dls"), os.path.join(dmusic, "FF8.dls"))
    bstream = os.path.join(bk, "stream")
    if os.path.isdir(bstream):
        for w in os.listdir(bstream):
            if w.lower().endswith(".wav"):
                shutil.copy2(os.path.join(bstream, w), os.path.join(stream, w))
    print("  Original music restored.")


def menu(game):
    lookup = dict((m[0], m[2]) for m in MENU)
    while True:
        print("\n" + "=" * 58)
        print("  FF8 MUSIC VOLUME")
        print("  Game: " + game)
        print("=" * 58)
        print("  Lowers MUSIC only - sound effects stay the same.\n")
        for num, label, _ in MENU:
            print("    %s) %s" % (num, label))
        print("    0) Quit")
        ch = input("\n  Type a number and press Enter: ").strip()
        if ch == "0":
            return
        pick = lookup.get(ch)
        if not pick:
            continue
        print("  (Close the game first if it's running.)")
        apply_level(game, pick)


def main():
    ap = argparse.ArgumentParser(description="Lower or mute FF8 (2013/Steam) background music.")
    ap.add_argument("--game")
    ap.add_argument("--level", choices=list(LEVELS))
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    game = find_game(a.game)
    if not game:
        print("No FF8 install found. Pass --game \"...\" or run again.")
        sys.exit(1)
    if a.restore:
        restore(game)
    elif a.level:
        apply_level(game, a.level)
    else:
        menu(game)


if __name__ == "__main__":
    main()
