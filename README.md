# yt-music-cli

A terminal client for YouTube Music. Search, browse your library, manage playlists, and play music — all from the command line.

Uses your own YouTube Music account so you get your subscription perks, recommendations, and library.

## Dependencies

- Python 3.11+
- mpv — for audio playback
- yt-dlp — for stream resolution  

```bash
# Debian/Ubuntu
apt install mpv libmpv-dev yt-dlp

# macOS
brew install mpv yt-dlp
```

## Quick start

```bash
git clone https://github.com/YOUR_USER/yt-music-cli.git
cd yt-music-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Authentication

First run a one-time setup to grab your session headers:

```bash
yt-music-cli --setup
```

Then:
1. Open music.youtube.com in your browser and sign in
2. Open DevTools (F12) → Network tab  
3. Search for something to trigger API calls
4. Find a request to `youtubei/v1/browse` or `youtubei/v1/search`
5. Right-click → Copy → Copy Request Headers
6. Paste into the terminal

Credentials are saved to `~/.config/yt-music-cli/headers.json`. You only need to do this once — or if your session expires.

## Usage

```
yt-music-cli
```

| Key | What it does |
|-----|-------------|
| `/` | Jump to search, clear input |
| `Enter` | Play selected track |
| `Space` | Pause / resume |
| `n` `p` | Next / previous track |
| `h` `l` or `←` `→` | Seek backward / forward |
| `+` `-` | Volume |
| `j` `k` | Navigate lists |
| `g` `G` | Jump to top / bottom of list |
| `a` | Add to queue |
| `d` | Remove from queue |
| `s` | Shuffle |
| `r` | Repeat (off → one → all) |
| `1`–`5` | Jump to view: Search, Library, Playlists, Queue, Now Playing |
| `?` | Show all keybindings |
| `q` | Quit |

## Tech

Built with [Textual](https://github.com/Textualize/textual) for the TUI, [ytmusicapi](https://github.com/sigma67/ytmusicapi) for the API, and python-mpv for playback. Event-driven architecture so modules don't step on each other.
