# YouTube Music TUI — Design Spec

**Date:** 2026-05-03
**Status:** Approved — awaiting implementation plan

## Overview

A terminal-based YouTube Music client (TUI) that authenticates via OAuth using the user's own Google account (with YT Music subscription), browses and searches the full YT Music catalog, manages library and playlists, and plays audio locally through mpv.

## Requirements

### Functional

- OAuth authentication via ytmusicapi with persistent token storage
- Full-text search across YT Music catalog (songs, albums, artists, videos)
- Browse user's library: liked songs, albums, artists, playlists
- View and manage YouTube Music playlists
- Queue management: add/remove/reorder tracks
- Local audio playback via mpv with play/pause/skip/seek/volume
- Shuffle and repeat modes (off/one/all)
- Now-playing display with track info and progress

### Non-Functional

- Terminal-based UI using Textual framework (Python)
- Event-driven modular architecture for parallel development
- Responsive: API calls and playback must not block the UI
- Graceful error handling: network failures, auth expiry, unplayable tracks
- XDG-compliant config/data storage
- Cross-platform: Linux primary, macOS compatible

### Out of Scope (for now)

- Downloads/offline playback
- Lyrics display
- Multi-account
- Cast/remote device control
- Audio visualization
- Podcast support

## Architecture

### Pattern: Event-Driven Modular

A central MessageBus routes typed events between independent modules. No module imports another directly — all coupling is through events. This allows subagents to build modules in parallel.

### Modules

| Module | Responsibility |
|--------|---------------|
| **MessageBus** | Async pub/sub event routing. `publish(event)`, `subscribe(EventType, handler)`. Deterministic handler order. |
| **AuthModule** | OAuth flow via ytmusicapi. Reads/writes `~/.config/yt-music-cli/oauth.json`. Publishes `AuthReadyEvent` or `AuthErrorEvent`. Handles token refresh. |
| **APIClient** | Wraps ytmusicapi. Handles search, library fetching, playlist CRUD. Rate limiting, retry with exponential backoff. Activated on `AuthReadyEvent`. |
| **PlayerModule** | Controls mpv via python-mpv bindings. Manages internal queue, playback state, seek, volume, shuffle/repeat. Publishes `TrackChangedEvent`, `PlaybackStateEvent`, `QueueUpdatedEvent`. |
| **UIModule** | Textual app with 5 screens. Handles keybindings and navigation. Publishes user actions (`SearchRequestEvent`, `PlayRequestEvent`). Subscribes to results and state changes. |

### Event Catalog

| Event | Publisher | Subscriber | Payload |
|-------|-----------|------------|---------|
| `AuthReadyEvent` | AuthModule | API, UI | — |
| `AuthErrorEvent` | AuthModule | UI | `error_msg: str` |
| `SearchRequestEvent` | UI | APIClient | `query: str, filter: str` |
| `SearchResultsEvent` | APIClient | UI | `results: list[Track]` |
| `PlayRequestEvent` | UI | Player | `track_id: str, context: str` |
| `TrackChangedEvent` | Player | UI, API | `track: Track` |
| `PlaybackStateEvent` | Player | UI | `state: str, position_s: float` |
| `QueueUpdatedEvent` | Player | UI | `queue: list[Track]` |
| `LibraryUpdateEvent` | APIClient | UI | `tracks/albums/artists` |
| `ErrorEvent` | Any | UI | `source: str, message: str` |

All events are typed dataclasses. Handlers are async. `bus.publish()` is fire-and-forget from the publisher's perspective.

### Data Flow Example: Search & Play

1. User types in Search screen → UI publishes `SearchRequestEvent(query)`
2. APIClient receives it, calls `ytmusicapi.search(query)`, publishes `SearchResultsEvent(results)`
3. UI renders results list
4. User presses Enter → UI publishes `PlayRequestEvent(track_id)`
5. Player receives it, fetches stream URL via ytmusicapi, starts mpv, publishes `TrackChangedEvent(track)`
6. UI updates Now Playing bar

## UI Design

### Layout

```
+------------------------------------------------------------------+
| [Search] [Library] [Playlists] [Queue]              yt-music-cli  |  <- Tab bar
+------------------------------------------------------------------+
|                                                                  |
|   > search query...                                              |  <- Main content area
|                                                                  |     (switches per tab)
|   1. Track Name — Artist                                         |
|   2. Another Track — Artist                                      |
|   ...                                                            |
|                                                                  |
+------------------------------------------------------------------+
| ▶ Track Name — Artist     [====●========] 1:23 / 3:45    ⏸      |  <- Now Playing bar
+------------------------------------------------------------------+
| q:quit  /:search  Space:play/pause  n:next  p:prev  Tab:view    |  <- Keybinding hints
+------------------------------------------------------------------+
```

### Screens

1. **Search** — Live-as-you-type search. Results grouped: top/songs/albums/artists. Enter to play, `a` to queue.
2. **Library** — Tabs for Songs, Albums, Artists, Playlists, Liked. Enter drills into album/artist.
3. **Playlists** — Two-pane: playlist list on left, selected playlist tracks on right. `a` to queue all.
4. **Queue** — Ordered upcoming tracks. Ctrl+Up/Down reorder, `d` to remove. Shows currently playing at top.
5. **Now Playing (full)** — Expanded view with album art placeholder, track details, large progress bar, volume, shuffle/repeat toggles.

### Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `/` | Focus search |
| `Space` | Play / Pause |
| `n` / `p` | Next / Previous track |
| `←` / `→` | Seek backward / forward |
| `+` / `-` | Volume up / down |
| `Tab` | Cycle views |
| `1`..`5` | Jump to view directly |
| `s` | Toggle shuffle |
| `r` | Toggle repeat (off → one → all) |
| `a` | Add to queue |
| `d` | Remove from queue/playlist |
| `Enter` | Play selected / drill into item |
| `Esc` | Go back / close overlay |

## Auth Flow

1. **First launch:** No cached token → UI shows login prompt → user triggers OAuth → ytmusicapi opens browser → user approves → token saved to `~/.config/yt-music-cli/oauth.json` → `AuthReadyEvent` published.
2. **Subsequent launches:** Load cached token → ytmusicapi validates/refreshes transparently → `AuthReadyEvent`. If refresh fails → clear token → show login prompt.
3. **Runtime expiry:** APIClient catches 401 → requests token refresh → retries. If refresh fails → `AuthErrorEvent` → UI shows re-auth prompt.

## Error Handling

| Error | Recovery | User Sees |
|-------|----------|-----------|
| Network timeout | Retry x3 with exponential backoff | Spinner in status bar |
| HTTP 401/403 | Attempt token refresh, retry | "Re-authenticating..." |
| Auth expired (fatal) | Clear token, show login | Login prompt screen |
| Stream fetch failed | Skip to next track in queue | "Skipping unplayable track" |
| mpv crash | Restart mpv, resume queue | Brief "Reconnecting..." |
| Rate limit (429) | Wait and retry | "Rate limited, retrying..." |

All errors flow through `ErrorEvent` → UI status bar + logged to `~/.local/share/yt-music-cli/errors.log`.

## Persistent Data

| Path | Contents |
|------|----------|
| `~/.config/yt-music-cli/oauth.json` | OAuth tokens |
| `~/.config/yt-music-cli/config.toml` | User preferences (keybindings, defaults) |
| `~/.local/share/yt-music-cli/cache/` | API response cache |
| `~/.local/share/yt-music-cli/errors.log` | Error log (rotating) |
| `~/.local/share/yt-music-cli/history.json` | Playback history |

## Dependencies

- **Python 3.11+** — async support, dataclasses
- **textual** — TUI framework
- **ytmusicapi** — YouTube Music API wrapper with OAuth
- **python-mpv** — mpv bindings for audio playback
- **mpv** (system) — audio player backend

## Testing Strategy

- Each module tested independently with mocked dependencies
- APIClient tested with recorded YT Music API responses
- Player tested with mock mpv instance
- UI tested via Textual's `pilot` test framework
- Integration tests for event flow across modules
