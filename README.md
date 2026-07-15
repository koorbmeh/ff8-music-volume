# ff8-music-volume

Lower or mute the background music in **Final Fantasy VIII** (2013 / Steam re-release) — without changing sound effects, graphics, or controls. Pick a level from **Off to 100%**, change it anytime, and restore the originals with one click.

This tool ships **no game audio**. It generates the quieter music on your own PC from **your own installed copy** of the game, and backs up your originals first.

## Requirements
- A legally installed copy of **Final Fantasy VIII (2013 / Steam)**.
- **Windows** with **Python 3.8+**. No extra packages needed — standard library only.
  - Don't have Python? Get it at https://www.python.org/downloads/ and tick **"Add Python to PATH"** during install.

## Quick start
1. Close FF8 if it's running.
2. Double-click **`FF8 Music Volume.bat`** (or run `python ff8_music_volume.py`).
3. First run: if it can't auto-find the game, paste your FF8 folder path (in Steam: right-click **FINAL FANTASY VIII → Manage → Browse local files**).
4. Pick a level from the menu. Start the game to hear it.

Prefer the command line:

```
python ff8_music_volume.py --level 20      # set music to 20%
python ff8_music_volume.py --restore       # back to original (100%)
python ff8_music_volume.py --game "D:\Games\FINAL FANTASY VIII"
```

## Levels
Off (silent), 5%, 10%, 20%, 40%, 70%, and Restore original (100%). Re-run anytime to change.

## How it works
- On the first change, your original music is backed up once to `<game>\_FF8Tools-backup\`.
- The game's music is a DirectMusic soundbank (`FF8.dls`) plus streamed `.wav` tracks. The tool makes quieter copies by scaling the audio samples (in 32-bit float, matching the game's own format) and writes them into your game. Sound effects live in a separate file and are never touched.
- **Restore original (100%)** copies your untouched backup back.

## Notes
- Not affiliated with, endorsed by, or associated with Square Enix. "Final Fantasy" is a trademark of Square Enix.
- This tool only reads and modifies files on your own machine and includes none of the game's audio. Use at your own risk — your originals are backed up and restorable.
- License: MIT (see `LICENSE`).
