# yt-music-cli

Terminal-based YouTube Music client with OAuth authentication.

## Requirements

- Python 3.11+
- mpv (system package: `apt install mpv` or `brew install mpv`)
- YouTube Music subscription

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Setup (first run)

1. Run `yt-music-cli`
2. On first launch, the app will prompt for authentication
3. A browser window will open — log in with your Google account
4. Credentials are saved to `~/.config/yt-music-cli/oauth.json`

## Controls

| Key | Action |
|-----|--------|
| `/` | Focus search |
| `Space` | Play / Pause |
| `n` / `p` | Next / Previous track |
| `←` / `→` | Seek backward / forward |
| `+` / `-` | Volume up / down |
| `Tab` | Cycle views |
| `1`—`5` | Jump to view |
| `s` | Toggle shuffle |
| `r` | Toggle repeat |
| `q` | Quit |

## Run

```bash
source .venv/bin/activate
yt-music-cli
```
