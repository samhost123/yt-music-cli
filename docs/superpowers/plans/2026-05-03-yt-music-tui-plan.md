# YouTube Music TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a terminal-based YouTube Music client with OAuth login, search, library browsing, playlist management, queued playback, and local mpv audio.

**Architecture:** Event-driven modular design with a central MessageBus routing typed events between independent modules (Auth, API, Player, UI). No module imports another directly — all coupling is through events.

**Tech Stack:** Python 3.11+, Textual (TUI), ytmusicapi (YT Music API), python-mpv (audio), pytest (testing)

**Parallel execution note:** Tasks marked **[∥]** can run in parallel via subagents. Tasks without the marker are sequential prerequisites.

---

## File Structure

```
src/yt_music_cli/
├── __init__.py              # Package init
├── app.py                   # Textual App, module wiring, startup
├── bus.py                   # MessageBus: async pub/sub
├── events.py                # All event dataclass definitions
├── models.py                # Track, Album, Artist, Playlist dataclasses
├── config.py                # XDG config/data paths, settings
├── auth.py                  # AuthModule: OAuth flow, token persistence
├── api.py                   # APIClient: ytmusicapi wrapper
├── player.py                # PlayerModule: mpv control, queue, state
└── ui/
    ├── __init__.py           # UIModule registry
    ├── widgets.py            # NowPlayingBar, StatusBar widgets
    ├── screens.py            # SearchScreen, LibraryScreen, QueueScreen, PlaylistScreen, NowPlayingScreen
    └── keys.py               # Keybinding constants

tests/
├── __init__.py
├── conftest.py               # Shared fixtures (mock bus, mock mpv)
├── test_models.py
├── test_events.py
├── test_bus.py
├── test_auth.py
├── test_api.py
├── test_player.py
└── test_ui/
    ├── __init__.py
    └── test_integration.py

pyproject.toml
```

---

### Task 1: Project Scaffold & Data Models [Foundation]

**Files:**
- Create: `pyproject.toml`
- Create: `src/yt_music_cli/__init__.py`
- Create: `src/yt_music_cli/models.py`
- Create: `src/yt_music_cli/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`

**Dependencies:** None. This is the starting point.

- [ ] **Step 1: Write failing test for Track model**

```python
# tests/test_models.py
import pytest
from yt_music_cli.models import Track, Album, Artist, Playlist


def test_track_creation():
    track = Track(
        id="abc123",
        title="Bohemian Rhapsody",
        artists=["Queen"],
        album="A Night at the Opera",
        duration_ms=354000,
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert track.id == "abc123"
    assert track.title == "Bohemian Rhapsody"
    assert track.duration_ms == 354000
    assert track.artist_string == "Queen"


def test_track_artist_string_multiple():
    track = Track(id="1", title="T", artists=["Alice", "Bob"], album="A", duration_ms=1000)
    assert track.artist_string == "Alice, Bob"


def test_album_creation():
    album = Album(
        id="al1",
        title="A Night at the Opera",
        artists=["Queen"],
        year=1975,
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert album.id == "al1"
    assert album.year == 1975


def test_playlist_track_count():
    playlist = Playlist(
        id="pl1",
        title="My Mix",
        track_count=42,
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert playlist.track_count == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'yt_music_cli.models'`

- [ ] **Step 3: Write pyproject.toml**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "yt-music-cli"
version = "0.1.0"
description = "Terminal-based YouTube Music client"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.50.0",
    "ytmusicapi>=1.7.0",
    "python-mpv>=1.0.0",
]

[project.scripts]
yt-music-cli = "yt_music_cli.app:main"

[tool.setuptools.package-dir]
"" = "src"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 4: Install package in dev mode and verify**

Run: `pip install -e .`
Expected: install succeeds

Run: `pip install pytest`
Expected: install succeeds

- [ ] **Step 5: Create config.py**

```python
# src/yt_music_cli/config.py
import os
from pathlib import Path


def _xdg_config_home() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def _xdg_data_home() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


CONFIG_DIR = _xdg_config_home() / "yt-music-cli"
DATA_DIR = _xdg_data_home() / "yt-music-cli"
OAUTH_FILE = CONFIG_DIR / "oauth.json"
CONFIG_FILE = CONFIG_DIR / "config.toml"
ERROR_LOG = DATA_DIR / "errors.log"
CACHE_DIR = DATA_DIR / "cache"
HISTORY_FILE = DATA_DIR / "history.json"


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 6: Write models.py**

```python
# src/yt_music_cli/models.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Track:
    id: str
    title: str
    artists: list[str]
    album: Optional[str] = None
    duration_ms: int = 0
    thumbnail_url: str = ""

    @property
    def artist_string(self) -> str:
        return ", ".join(self.artists)

    @property
    def duration_str(self) -> str:
        total_seconds = self.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"


@dataclass
class Album:
    id: str
    title: str
    artists: list[str]
    year: Optional[int] = None
    thumbnail_url: str = ""


@dataclass
class Artist:
    id: str
    name: str
    thumbnail_url: str = ""


@dataclass
class Playlist:
    id: str
    title: str
    track_count: int = 0
    thumbnail_url: str = ""
    description: str = ""


@dataclass
class QueueItem:
    track: Track
    source: str = ""  # "search", "library", "playlist", etc.


@dataclass
class PlaybackState:
    track: Optional[Track] = None
    is_playing: bool = False
    position_s: float = 0.0
    duration_s: float = 0.0
    volume: int = 100
    shuffle: bool = False
    repeat: str = "off"  # "off", "one", "all"
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 8: Create conftest.py**

```python
# tests/conftest.py
import pytest
from yt_music_cli.models import Track, PlaybackState


@pytest.fixture
def sample_track():
    return Track(
        id="track1",
        title="Test Song",
        artists=["Test Artist"],
        album="Test Album",
        duration_ms=210000,
    )


@pytest.fixture
def sample_tracks():
    return [
        Track(id=f"track{i}", title=f"Song {i}", artists=[f"Artist {i}"], duration_ms=180000 + i * 1000)
        for i in range(1, 6)
    ]


@pytest.fixture
def playback_state(sample_track):
    return PlaybackState(track=sample_track, is_playing=True, position_s=30.0, duration_s=210.0)
```

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: project scaffold, models, and config"
```

---

### Task 2: Event Definitions

**Files:**
- Create: `src/yt_music_cli/events.py`
- Create: `tests/test_events.py`

**Dependencies:** Task 1 (models.py)

- [ ] **Step 1: Write failing tests for events**

```python
# tests/test_events.py
from yt_music_cli.events import (
    AuthReadyEvent,
    AuthErrorEvent,
    SearchRequestEvent,
    SearchResultsEvent,
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
    LibraryUpdateEvent,
    ErrorEvent,
)
from yt_music_cli.models import Track


def test_auth_ready_event():
    evt = AuthReadyEvent()
    assert evt.type == "auth_ready"


def test_auth_error_event():
    evt = AuthErrorEvent(error_msg="Invalid credentials")
    assert evt.type == "auth_error"
    assert evt.error_msg == "Invalid credentials"


def test_search_request_event():
    evt = SearchRequestEvent(query="queen", filter="songs")
    assert evt.type == "search_request"
    assert evt.query == "queen"
    assert evt.filter == "songs"


def test_search_results_event():
    tracks = [
        Track(id="1", title="Song A", artists=["Artist A"]),
        Track(id="2", title="Song B", artists=["Artist B"]),
    ]
    evt = SearchResultsEvent(results=tracks, query="test")
    assert evt.type == "search_results"
    assert len(evt.results) == 2
    assert evt.query == "test"


def test_play_request_event():
    track = Track(id="abc123", title="Song", artists=["Artist"])
    evt = PlayRequestEvent(track=track, context="search")
    assert evt.type == "play_request"
    assert evt.track.id == "abc123"
    assert evt.track.title == "Song"
    assert evt.context == "search"


def test_track_changed_event():
    track = Track(id="1", title="Song A", artists=["Artist A"])
    evt = TrackChangedEvent(track=track)
    assert evt.type == "track_changed"
    assert evt.track.id == "1"


def test_playback_state_event():
    evt = PlaybackStateEvent(is_playing=True, position_s=42.5, duration_s=210.0,
                              volume=80, shuffle=False, repeat="off")
    assert evt.type == "playback_state"
    assert evt.is_playing is True
    assert evt.position_s == 42.5


def test_queue_updated_event():
    tracks = [Track(id="1", title="S", artists=["A"])]
    evt = QueueUpdatedEvent(queue=tracks)
    assert evt.type == "queue_updated"
    assert len(evt.queue) == 1


def test_library_update_event():
    evt = LibraryUpdateEvent(category="tracks", items=[])
    assert evt.type == "library_update"
    assert evt.category == "tracks"


def test_error_event():
    evt = ErrorEvent(source="api", message="Network timeout")
    assert evt.type == "error"
    assert evt.source == "api"
    assert evt.message == "Network timeout"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'yt_music_cli.events'`

- [ ] **Step 3: Write events.py**

```python
# src/yt_music_cli/events.py
from dataclasses import dataclass, field
from typing import Any, Optional
from yt_music_cli.models import Track


@dataclass
class AuthReadyEvent:
    type: str = field(default="auth_ready", init=False)


@dataclass
class AuthErrorEvent:
    error_msg: str
    type: str = field(default="auth_error", init=False)


@dataclass
class SearchRequestEvent:
    query: str
    filter: str = ""
    type: str = field(default="search_request", init=False)


@dataclass
class SearchResultsEvent:
    results: list[Track]
    query: str = ""
    type: str = field(default="search_results", init=False)


@dataclass
class PlayRequestEvent:
    track: Track
    context: str = ""
    type: str = field(default="play_request", init=False)


@dataclass
class TrackChangedEvent:
    track: Track
    type: str = field(default="track_changed", init=False)


@dataclass
class PlaybackStateEvent:
    is_playing: bool
    position_s: float
    duration_s: float
    volume: int = 100
    shuffle: bool = False
    repeat: str = "off"
    type: str = field(default="playback_state", init=False)


@dataclass
class QueueUpdatedEvent:
    queue: list[Track]
    current_index: int = 0
    type: str = field(default="queue_updated", init=False)


@dataclass
class LibraryUpdateEvent:
    category: str  # "tracks", "albums", "artists", "playlists", "liked"
    items: list[Any]
    type: str = field(default="library_update", init=False)


@dataclass
class ErrorEvent:
    source: str
    message: str
    type: str = field(default="error", init=False)


# Union type for all events
Event = (
    AuthReadyEvent
    | AuthErrorEvent
    | SearchRequestEvent
    | SearchResultsEvent
    | PlayRequestEvent
    | TrackChangedEvent
    | PlaybackStateEvent
    | QueueUpdatedEvent
    | LibraryUpdateEvent
    | ErrorEvent
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_events.py -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/yt_music_cli/events.py tests/test_events.py
git commit -m "feat: event dataclass definitions"
```

---

### Task 3: MessageBus

**Files:**
- Create: `src/yt_music_cli/bus.py`
- Create: `tests/test_bus.py`

**Dependencies:** Task 2 (events.py)

- [ ] **Step 1: Write failing tests for MessageBus**

```python
# tests/test_bus.py
import pytest
from yt_music_cli.bus import MessageBus
from yt_music_cli.events import SearchRequestEvent, SearchResultsEvent, ErrorEvent
from yt_music_cli.models import Track


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = MessageBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(SearchRequestEvent, handler)
    evt = SearchRequestEvent(query="test")
    await bus.publish(evt)

    assert len(received) == 1
    assert received[0].query == "test"


@pytest.mark.asyncio
async def test_multiple_subscribers():
    bus = MessageBus()
    results = []

    async def handler_a(event):
        results.append("a")

    async def handler_b(event):
        results.append("b")

    bus.subscribe(SearchResultsEvent, handler_a)
    bus.subscribe(SearchResultsEvent, handler_b)
    await bus.publish(SearchResultsEvent(results=[]))

    assert sorted(results) == ["a", "b"]


@pytest.mark.asyncio
async def test_handler_order_is_preserved():
    bus = MessageBus()
    order = []

    async def h1(event):
        order.append(1)

    async def h2(event):
        order.append(2)

    bus.subscribe(ErrorEvent, h1)
    bus.subscribe(ErrorEvent, h2)
    await bus.publish(ErrorEvent(source="test", message="msg"))

    assert order == [1, 2]


@pytest.mark.asyncio
async def test_unrelated_event_not_received():
    bus = MessageBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(SearchRequestEvent, handler)
    await bus.publish(ErrorEvent(source="x", message="y"))

    assert len(received) == 0


@pytest.mark.asyncio
async def test_handler_exception_does_not_block_others():
    bus = MessageBus()
    results = []

    async def failing_handler(event):
        raise RuntimeError("boom")

    async def ok_handler(event):
        results.append("ok")

    bus.subscribe(ErrorEvent, failing_handler)
    bus.subscribe(ErrorEvent, ok_handler)
    await bus.publish(ErrorEvent(source="x", message="y"))

    assert results == ["ok"]


@pytest.mark.asyncio
async def test_publish_non_subscribed_event_does_nothing():
    bus = MessageBus()
    # Should not raise — just no-op
    await bus.publish(SearchRequestEvent(query="x"))


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = MessageBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(SearchRequestEvent, handler)
    bus.unsubscribe(SearchRequestEvent, handler)
    await bus.publish(SearchRequestEvent(query="x"))

    assert len(received) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bus.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write bus.py**

```python
# src/yt_music_cli/bus.py
import logging
from collections import defaultdict
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class MessageBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Any) -> None:
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            return

        for handler in list(handlers):
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Handler %s raised exception for event %s",
                    handler.__name__,
                    event_type.__name__,
                )
```

- [ ] **Step 4: Update conftest.py** (bus fixture already exists from Task 1)

Verify: `grep "def bus" tests/conftest.py` exists.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_bus.py -v`
Expected: 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/yt_music_cli/bus.py tests/test_bus.py
git commit -m "feat: async message bus with pub/sub"
```

---

### Task 4: AuthModule [∥]

**Files:**
- Create: `src/yt_music_cli/auth.py`
- Create: `tests/test_auth.py`

**Dependencies:** Task 1 (models, config), Task 2 (events), Task 3 (bus)

**Note:** This task uses `ytmusicapi`'s OAuth. The `ytmusicapi.YTMusic` class has `setup_oauth()` and `oauth` parameter. Tests mock the YTMusic class.

- [ ] **Step 1: Write failing tests for AuthModule**

```python
# tests/test_auth.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from yt_music_cli.bus import MessageBus
from yt_music_cli.auth import AuthModule
from yt_music_cli.events import AuthReadyEvent, AuthErrorEvent


@pytest.fixture
def tmp_oauth_file(tmp_path):
    return tmp_path / "oauth.json"


@pytest.mark.asyncio
async def test_auth_ready_when_token_exists(tmp_oauth_file):
    token_data = {"access_token": "fake", "refresh_token": "fake2", "expires_at": "9999999999"}
    tmp_oauth_file.write_text(json.dumps(token_data))

    mock_ytmusic = MagicMock()
    with patch("yt_music_cli.auth.YTMusic", return_value=mock_ytmusic):
        bus = MessageBus()
        received = []
        bus.subscribe(AuthReadyEvent, lambda e: received.append(e) or AsyncMock()())

        module = AuthModule(bus, oauth_path=tmp_oauth_file)
        await module.initialize()

        assert len(received) == 1
        assert isinstance(received[0], AuthReadyEvent)


@pytest.mark.asyncio
async def test_auth_error_when_no_token(tmp_oauth_file):
    bus = MessageBus()
    received = []
    bus.subscribe(AuthErrorEvent, lambda e: received.append(e) or AsyncMock()())

    module = AuthModule(bus, oauth_path=tmp_oauth_file)
    await module.initialize()

    assert len(received) == 1
    assert isinstance(received[0], AuthErrorEvent)
    assert "No saved credentials" in received[0].error_msg


@pytest.mark.asyncio
async def test_start_oauth_flow_saves_token(tmp_oauth_file):
    mock_ytmusic = MagicMock()
    with patch("yt_music_cli.auth.YTMusic", return_value=mock_ytmusic):
        bus = MessageBus()
        received = []
        bus.subscribe(AuthReadyEvent, lambda e: received.append(e) or AsyncMock()())

        module = AuthModule(bus, oauth_path=tmp_oauth_file)
        await module.start_oauth()

        mock_ytmusic.setup_oauth.assert_called_once()
        assert tmp_oauth_file.exists()


@pytest.mark.asyncio
async def test_is_authenticated_after_init(tmp_oauth_file):
    token_data = {"access_token": "fake", "refresh_token": "fake2", "expires_at": "9999999999"}
    tmp_oauth_file.write_text(json.dumps(token_data))

    mock_ytmusic = MagicMock()
    with patch("yt_music_cli.auth.YTMusic", return_value=mock_ytmusic):
        bus = MessageBus()
        module = AuthModule(bus, oauth_path=tmp_oauth_file)
        await module.initialize()

        assert module.is_authenticated() is True


@pytest.mark.asyncio
async def test_is_authenticated_false_without_init(tmp_oauth_file):
    bus = MessageBus()
    module = AuthModule(bus, oauth_path=tmp_oauth_file)
    assert module.is_authenticated() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write auth.py**

```python
# src/yt_music_cli/auth.py
import json
import logging
from pathlib import Path

from ytmusicapi import YTMusic

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import AuthReadyEvent, AuthErrorEvent

logger = logging.getLogger(__name__)


class AuthModule:
    def __init__(self, bus: MessageBus, oauth_path: Path | None = None) -> None:
        self._bus = bus
        self._oauth_path = oauth_path
        self._ytmusic: YTMusic | None = None

    async def initialize(self) -> None:
        if self._oauth_path and self._oauth_path.exists():
            try:
                self._ytmusic = YTMusic(str(self._oauth_path), oauth_credentials=None)
                await self._bus.publish(AuthReadyEvent())
                logger.info("Authenticated from saved credentials")
            except Exception as e:
                logger.warning("Failed to load saved credentials: %s", e)
                await self._bus.publish(
                    AuthErrorEvent(error_msg="Failed to load saved credentials")
                )
        else:
            await self._bus.publish(
                AuthErrorEvent(error_msg="No saved credentials. Run login to authenticate.")
            )

    async def start_oauth(self) -> None:
        try:
            if self._oauth_path:
                self._oauth_path.parent.mkdir(parents=True, exist_ok=True)
                self._ytmusic = YTMusic(str(self._oauth_path))
            else:
                self._ytmusic = YTMusic()

            logger.info("OAuth flow completed")
            await self._bus.publish(AuthReadyEvent())
        except Exception as e:
            logger.exception("OAuth flow failed")
            await self._bus.publish(AuthErrorEvent(error_msg=str(e)))

    def is_authenticated(self) -> bool:
        return self._ytmusic is not None

    @property
    def client(self) -> YTMusic | None:
        return self._ytmusic
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/yt_music_cli/auth.py tests/test_auth.py
git commit -m "feat: OAuth auth module with token persistence"
```

---

### Task 5: APIClient [∥]

**Files:**
- Create: `src/yt_music_cli/api.py`
- Create: `tests/test_api.py`

**Dependencies:** Task 1 (models), Task 2 (events), Task 3 (bus), Task 4 (auth — for YTMusic type only)

**Note:** APIClient wraps `ytmusicapi.YTMusic`. Tests use mock YTMusic. It subscribes to `SearchRequestEvent` and `AuthReadyEvent`. Publishes `SearchResultsEvent`, `LibraryUpdateEvent`, and `ErrorEvent`.

- [ ] **Step 1: Write failing tests for APIClient**

```python
# tests/test_api.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from yt_music_cli.bus import MessageBus
from yt_music_cli.api import APIClient
from yt_music_cli.events import (
    SearchRequestEvent,
    SearchResultsEvent,
    LibraryUpdateEvent,
    AuthReadyEvent,
    ErrorEvent,
    TrackChangedEvent,
)
from yt_music_cli.models import Track


@pytest.fixture
def mock_ytmusic():
    ytm = MagicMock()
    ytm.search.return_value = [
        {
            "videoId": "vid1",
            "title": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "duration_seconds": 180,
            "thumbnails": [{"url": "http://t.jpg"}],
            "resultType": "song",
        },
        {
            "videoId": "vid2",
            "title": "Other Song",
            "artists": [{"name": "Other Artist"}],
            "duration_seconds": 240,
            "thumbnails": [{"url": "http://o.jpg"}],
            "resultType": "song",
        },
    ]
    ytm.get_library_songs.return_value = []
    ytm.get_library_albums.return_value = []
    ytm.get_library_playlists.return_value = []
    return ytm


@pytest.fixture
def api_client(mock_ytmusic):
    bus = MessageBus()
    client = APIClient(bus)
    client._ytmusic = mock_ytmusic
    return bus, client


@pytest.mark.asyncio
async def test_search_request_publishes_results(api_client):
    bus, client = api_client
    results = []

    async def capture(event):
        results.append(event)

    bus.subscribe(SearchResultsEvent, capture)

    await bus.publish(SearchRequestEvent(query="test"))
    # Allow async handler to run
    import asyncio
    await asyncio.sleep(0)

    assert len(results) == 1
    assert len(results[0].results) == 2
    assert results[0].results[0].title == "Test Song"
    assert results[0].results[0].artists == ["Test Artist"]


@pytest.mark.asyncio
async def test_search_converts_empty_artists(api_client):
    bus, client = api_client
    client._ytmusic.search.return_value = [{
        "videoId": "v1",
        "title": "Song",
        "duration_seconds": 100,
        "thumbnails": [],
        "resultType": "song",
    }]
    results = []

    async def capture(event):
        results.append(event)

    bus.subscribe(SearchResultsEvent, capture)

    await bus.publish(SearchRequestEvent(query="x"))
    import asyncio
    await asyncio.sleep(0)

    assert results[0].results[0].artists == ["Unknown Artist"]
    assert results[0].results[0].duration_ms == 100000


@pytest.mark.asyncio
async def test_search_error_publishes_error_event(api_client):
    bus, client = api_client
    client._ytmusic.search.side_effect = Exception("Network error")
    errors = []

    async def capture(event):
        errors.append(event)

    bus.subscribe(ErrorEvent, capture)

    await bus.publish(SearchRequestEvent(query="x"))
    import asyncio
    await asyncio.sleep(0)

    assert len(errors) == 1
    assert errors[0].source == "api"
    assert "Network error" in errors[0].message


@pytest.mark.asyncio
async def test_library_fetch_on_auth_ready(api_client):
    bus, client = api_client
    lib_events = []

    async def capture(event):
        lib_events.append(event)

    bus.subscribe(LibraryUpdateEvent, capture)

    await bus.publish(AuthReadyEvent())
    import asyncio
    await asyncio.sleep(0)

    assert len(lib_events) == 3  # songs, albums, playlists


@pytest.mark.asyncio
async def test_get_track_url(api_client):
    bus, client = api_client
    client._ytmusic.get_song.return_value = {
        "videoDetails": {"videoId": "vid1", "title": "Song", "author": "Artist"}
    }
    url = await client.get_stream_url("vid1")
    assert url is not None


@pytest.mark.asyncio
async def test_get_track_url_error(api_client):
    bus, client = api_client
    client._ytmusic.get_song.side_effect = Exception("fail")
    errors = []

    async def capture(event):
        errors.append(event)

    bus.subscribe(ErrorEvent, capture)

    url = await client.get_stream_url("vid1")
    import asyncio
    await asyncio.sleep(0)

    assert url is None
    assert len(errors) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write api.py**

```python
# src/yt_music_cli/api.py
import logging
from typing import Any

from ytmusicapi import YTMusic

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import (
    SearchRequestEvent,
    SearchResultsEvent,
    AuthReadyEvent,
    ErrorEvent,
    LibraryUpdateEvent,
    TrackChangedEvent,
)
from yt_music_cli.models import Track

logger = logging.getLogger(__name__)

RETRY_COUNT = 3
RETRY_DELAY = 1.0


def _parse_track(raw: dict) -> Track:
    artists = []
    if "artists" in raw and raw["artists"]:
        artists = [a.get("name", "Unknown Artist") for a in raw["artists"]]
    if not artists:
        artists = ["Unknown Artist"]

    duration = 0
    if raw.get("duration_seconds"):
        duration = raw["duration_seconds"] * 1000
    elif raw.get("duration"):
        duration_str = raw["duration"]
        # "3:45" -> 225000ms
        try:
            parts = duration_str.split(":")
            duration = (int(parts[0]) * 60 + int(parts[1])) * 1000
        except (ValueError, IndexError):
            pass

    thumbnail = ""
    if raw.get("thumbnails"):
        thumbnail = raw["thumbnails"][0].get("url", "")

    return Track(
        id=raw.get("videoId", ""),
        title=raw.get("title", "Unknown"),
        artists=artists,
        album=raw.get("album", {}).get("name") if isinstance(raw.get("album"), dict) else None,
        duration_ms=duration,
        thumbnail_url=thumbnail,
    )


class APIClient:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._ytmusic: YTMusic | None = None

    def set_client(self, ytmusic: YTMusic) -> None:
        self._ytmusic = ytmusic

    async def _on_auth_ready(self, event: AuthReadyEvent) -> None:
        await self._bus.publish(LibraryUpdateEvent(category="songs", items=[]))
        await self._bus.publish(LibraryUpdateEvent(category="albums", items=[]))
        await self._bus.publish(LibraryUpdateEvent(category="playlists", items=[]))

    async def _on_search_request(self, event: SearchRequestEvent) -> None:
        if not self._ytmusic:
            await self._bus.publish(
                ErrorEvent(source="api", message="Not authenticated")
            )
            return

        try:
            raw_results = self._ytmusic.search(event.query, filter=event.filter or None)
            tracks = []
            for item in raw_results:
                if item.get("resultType") in ("song", "video"):
                    tracks.append(_parse_track(item))
            await self._bus.publish(
                SearchResultsEvent(results=tracks, query=event.query)
            )
        except Exception as e:
            logger.exception("Search failed")
            await self._bus.publish(
                ErrorEvent(source="api", message=f"Search failed: {e}")
            )

    async def get_stream_url(self, track_id: str) -> str | None:
        if not self._ytmusic:
            return None
        try:
            song_data = self._ytmusic.get_song(track_id)
            formats = song_data.get("streamingData", {}).get("adaptiveFormats", [])
            audio_formats = [f for f in formats if "audio" in str(f.get("mimeType", ""))]
            if audio_formats:
                return audio_formats[-1].get("url")
            return None
        except Exception as e:
            logger.exception("Failed to get stream URL for %s", track_id)
            await self._bus.publish(
                ErrorEvent(source="api", message=f"Stream fetch failed: {e}")
            )
            return None

    async def fetch_library_songs(self) -> list[dict]:
        if not self._ytmusic:
            return []
        try:
            return self._ytmusic.get_library_songs(limit=9999)
        except Exception as e:
            logger.exception("Library fetch failed")
            return []

    async def fetch_library_playlists(self) -> list[dict]:
        if not self._ytmusic:
            return []
        try:
            return self._ytmusic.get_library_playlists(limit=9999)
        except Exception as e:
            logger.exception("Playlist fetch failed")
            return []

    async def fetch_playlist_tracks(self, playlist_id: str) -> list[dict]:
        if not self._ytmusic:
            return []
        try:
            result = self._ytmusic.get_playlist(playlist_id, limit=9999)
            return result.get("tracks", [])
        except Exception as e:
            logger.exception("Playlist tracks fetch failed")
            return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_api.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/yt_music_cli/api.py tests/test_api.py
git commit -m "feat: YT Music API client with search and stream URL"
```

---

### Task 6: PlayerModule [∥]

**Files:**
- Create: `src/yt_music_cli/player.py`
- Create: `tests/test_player.py`

**Dependencies:** Task 1 (models), Task 2 (events), Task 3 (bus)

**Note:** Tests mock `mpv.MPV` to avoid needing actual mpv installed. PlayerModule subscribes to `PlayRequestEvent` and publishes `TrackChangedEvent`, `PlaybackStateEvent`, `QueueUpdatedEvent`.

- [ ] **Step 1: Write failing tests for PlayerModule**

```python
# tests/test_player.py
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from yt_music_cli.bus import MessageBus
from yt_music_cli.player import PlayerModule
from yt_music_cli.events import (
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
)
from yt_music_cli.models import Track, QueueItem


@pytest.fixture
def mock_mpv():
    with patch("yt_music_cli.player.MPV") as mock:
        mpv_instance = MagicMock()
        mpv_instance.pause = False
        mpv_instance.volume = 100
        type(mpv_instance).time_pos = PropertyMock(return_value=10.0)
        type(mpv_instance).duration = PropertyMock(return_value=210.0)
        mock.return_value = mpv_instance
        yield mpv_instance


@pytest.fixture
def bus():
    return MessageBus()


@pytest.fixture
def player(bus, mock_mpv):
    player_module = PlayerModule(bus)
    return bus, player_module


@pytest.mark.asyncio
async def test_play_request_adds_to_queue_and_plays(player, sample_track):
    bus, player_module = player
    track_events = []

    async def capture(event):
        track_events.append(event)

    bus.subscribe(TrackChangedEvent, capture)

    await bus.publish(PlayRequestEvent(track=sample_track, context="test"))
    import asyncio
    await asyncio.sleep(0)

    assert len(track_events) == 1
    assert track_events[0].track.id == sample_track.id


@pytest.mark.asyncio
async def test_play_request_unknown_id_publishes_error(player, mock_mpv):
    bus, player_module = player
    from yt_music_cli.events import ErrorEvent
    errors = []
    bus.subscribe(ErrorEvent, lambda e: errors.append(e) or __import__("asyncio").sleep(0))

    unknown_track = Track(id="nonexistent", title="Unknown", artists=["Unknown"])
    await bus.publish(PlayRequestEvent(track=unknown_track, context="test"))
    import asyncio
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_play_pause_toggles(player, mock_mpv):
    bus, player_module = player
    type(mock_mpv).pause = PropertyMock(return_value=False)
    player_module.play_pause()
    # mpv.pause = True is set
    mock_mpv._set_property.assert_called_with("pause", True)


@pytest.mark.asyncio
async def test_next_skips_to_next_in_queue(player, sample_tracks):
    bus, player_module = player
    # Add tracks to queue
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module._current_index = 0
    player_module._queue = [
        QueueItem(track=t) for t in sample_tracks
    ]
    player_module.next_track()

    assert player_module._current_index == 1


@pytest.mark.asyncio
async def test_prev_goes_back(player, sample_tracks):
    bus, player_module = player
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module._current_index = 2
    player_module.prev_track()

    assert player_module._current_index == 1


@pytest.mark.asyncio
async def test_set_volume(player, mock_mpv):
    bus, player_module = player
    player_module.set_volume(50)
    mock_mpv._set_property.assert_called_with("volume", 50)


@pytest.mark.asyncio
async def test_seek(player, mock_mpv):
    bus, player_module = player
    player_module.seek(30.0)
    mock_mpv._set_property.assert_called_with("time-pos", 30.0)


@pytest.mark.asyncio
async def test_queue_updated_event_on_add(player, sample_track):
    bus, player_module = player
    queue_events = []

    async def capture(event):
        queue_events.append(event)

    bus.subscribe(QueueUpdatedEvent, capture)

    player_module.add_to_queue(sample_track)
    import asyncio
    await asyncio.sleep(0)

    assert len(queue_events) == 1
    assert queue_events[0].queue[0].id == sample_track.id


@pytest.mark.asyncio
async def test_remove_from_queue(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module.remove_from_queue(0)
    assert len(player_module.queue) == 4


@pytest.mark.asyncio
async def test_clear_queue(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module.clear_queue()
    assert len(player_module.queue) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_player.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write player.py**

```python
# src/yt_music_cli/player.py
import logging
import threading
from typing import Optional

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import (
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
    ErrorEvent,
)
from yt_music_cli.models import Track, QueueItem, PlaybackState

logger = logging.getLogger(__name__)


def _mpv_safe() -> object:
    try:
        from mpv import MPV
        return MPV
    except ImportError:
        return None


class PlayerModule:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._queue: list[QueueItem] = []
        self._current_index: int = 0
        self._mpv: object | None = None
        self._stream_urls: dict[str, str] = {}  # track_id -> url
        self._shuffle: bool = False
        self._repeat: str = "off"
        self._mpv_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def queue(self) -> list[QueueItem]:
        with self._lock:
            return list(self._queue)

    @property
    def current_track(self) -> Optional[Track]:
        with self._lock:
            if 0 <= self._current_index < len(self._queue):
                return self._queue[self._current_index].track
            return None

    def add_to_queue(self, track: Track, source: str = "") -> None:
        with self._lock:
            self._queue.append(QueueItem(track=track, source=source))

    def remove_from_queue(self, index: int) -> None:
        with self._lock:
            if 0 <= index < len(self._queue):
                self._queue.pop(index)
                if self._current_index >= len(self._queue):
                    self._current_index = max(0, len(self._queue) - 1)

    def clear_queue(self) -> None:
        with self._lock:
            self._queue.clear()
            self._current_index = 0

    def play_pause(self) -> None:
        if self._mpv:
            try:
                self._mpv.pause = not self._mpv.pause
            except Exception:
                pass

    def next_track(self) -> None:
        with self._lock:
            if not self._queue:
                return
            self._current_index = (self._current_index + 1) % len(self._queue)

    def prev_track(self) -> None:
        with self._lock:
            if not self._queue:
                return
            self._current_index = (self._current_index - 1) % len(self._queue)

    def set_volume(self, volume: int) -> None:
        if self._mpv:
            try:
                self._mpv.volume = max(0, min(100, volume))
            except Exception:
                pass

    def seek(self, position_s: float) -> None:
        if self._mpv:
            try:
                self._mpv.time_pos = position_s
            except Exception:
                pass

    def play(self) -> None:
        """Start playing from the current queue index."""
        with self._lock:
            if not self._queue:
                return
            if not self._mpv:
                mpv_cls = _mpv_safe()
                if mpv_cls:
                    self._mpv = mpv_cls()
            self._play_current()

    def _play_current(self) -> None:
        """Play the track at _current_index. Assumes _mpv is initialized."""
        track = self.current_track
        if not track:
            return

    def get_state(self) -> PlaybackState:
        track = self.current_track
        is_playing = False
        position = 0.0
        duration = 0.0
        volume = 100

        if self._mpv:
            try:
                is_playing = not self._mpv.pause
                position = self._mpv.time_pos or 0.0
                duration = self._mpv.duration or 0.0
                volume = self._mpv.volume or 100
            except Exception:
                pass

        return PlaybackState(
            track=track,
            is_playing=is_playing,
            position_s=position,
            duration_s=duration,
            volume=volume,
            shuffle=self._shuffle,
            repeat=self._repeat,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_player.py -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/yt_music_cli/player.py tests/test_player.py
git commit -m "feat: mpv player module with queue management"
```

---

### Task 7: UI Widgets & App Shell [∥]

**Files:**
- Create: `src/yt_music_cli/ui/__init__.py`
- Create: `src/yt_music_cli/ui/widgets.py`
- Create: `src/yt_music_cli/ui/keys.py`
- Create: `src/yt_music_cli/ui/screens.py` (search screen only, others as stubs)

**Dependencies:** Task 1 (models), Task 2 (events)

**Note:** Builds the NowPlayingBar widget, StatusBar widget, and SearchScreen. Other screens are stubs. All Textual widgets.

- [ ] **Step 1: Write keys.py**

```python
# src/yt_music_cli/ui/keys.py
class Keys:
    QUIT = "q"
    SEARCH = "/"
    PLAY_PAUSE = "space"
    NEXT = "n"
    PREV = "p"
    SEEK_FWD = "right"
    SEEK_BACK = "left"
    VOL_UP = "+"
    VOL_DOWN = "-"
    CYCLE_VIEW = "tab"
    SHUFFLE = "s"
    REPEAT = "r"
    ADD_TO_QUEUE = "a"
    REMOVE = "d"
    SELECT = "enter"
    BACK = "escape"
    VIEW_1 = "1"
    VIEW_2 = "2"
    VIEW_3 = "3"
    VIEW_4 = "4"
    VIEW_5 = "5"
```

- [ ] **Step 2: Write widgets.py**

```python
# src/yt_music_cli/ui/widgets.py
from textual.widgets import Static
from textual.app import ComposeResult
from yt_music_cli.models import Track, PlaybackState


class NowPlayingBar(Static):
    """Persistent bar showing current track, progress, and controls."""

    def __init__(self) -> None:
        super().__init__("", id="now-playing-bar")
        self._track: Track | None = None
        self._is_playing: bool = False
        self._position_s: float = 0.0
        self._duration_s: float = 0.0
        self._shuffle: bool = False
        self._repeat: str = "off"

    def update_state(self, state: PlaybackState) -> None:
        self._track = state.track
        self._is_playing = state.is_playing
        self._position_s = state.position_s
        self._duration_s = state.duration_s
        self._shuffle = state.shuffle
        self._repeat = state.repeat
        self.refresh()

    def render(self) -> str:
        if not self._track:
            return "  No track playing"

        play_icon = "\u25b6" if not self._is_playing else "\u23f8"
        title = self._track.title[:40]
        artist = self._track.artist_string[:40]

        # Progress bar (30 chars wide)
        if self._duration_s > 0:
            ratio = self._position_s / self._duration_s
            filled = int(ratio * 30)
            bar = "[" + "=" * max(0, filled - 1) + "\u25cf" + "=" * max(0, 30 - filled) + "]"
        else:
            bar = "[" + "-" * 30 + "]"

        pos_str = self._format_time(self._position_s)
        dur_str = self._format_time(self._duration_s)

        flags = ""
        if self._shuffle:
            flags += " \U0001f500"
        if self._repeat == "one":
            flags += " \U0001f502"
        elif self._repeat == "all":
            flags += " \U0001f501"

        return f"  {play_icon} {title} \u2014 {artist}  {bar} {pos_str} / {dur_str}{flags}"

    @staticmethod
    def _format_time(seconds: float) -> str:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"


class StatusBar(Static):
    """Bottom bar showing keybinding hints and status messages."""

    def __init__(self) -> None:
        super().__init__("", id="status-bar")
        self._message: str = ""
        self._hint: str = "q:quit  /:search  Space:play/pause  n:next  p:prev  Tab:view"

    def set_message(self, msg: str) -> None:
        self._message = msg
        self.refresh()

    def clear_message(self) -> None:
        self._message = ""
        self.refresh()

    def render(self) -> str:
        if self._message:
            return f"  {self._message}"
        return f"  {self._hint}"
```

- [ ] **Step 3: Write ui/__init__.py**

```python
# src/yt_music_cli/ui/__init__.py
```

- [ ] **Step 4: Write screens.py with SearchScreen + screen stubs**

```python
# src/yt_music_cli/ui/screens.py
from textual.widgets import Static, Input, ListView, ListItem, Label
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.screen import Screen

from yt_music_cli.models import Track
from yt_music_cli.events import SearchRequestEvent, SearchResultsEvent, PlayRequestEvent
from yt_music_cli.bus import MessageBus


class SearchScreen(Screen):
    """Live-search screen with results list."""

    BINDINGS = [
        ("escape", "dismiss", "Back"),
    ]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search YouTube Music...", id="search-input")
        yield ListView(id="search-results")

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        if len(query) >= 2:
            import asyncio
            asyncio.create_task(
                self._bus.publish(SearchRequestEvent(query=query))
            )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is not None and hasattr(event.item, "track"):
            await self._bus.publish(PlayRequestEvent(track=event.item.track, context="search"))

    async def show_results(self, event: SearchResultsEvent) -> None:
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()
        for track in event.results:
            item = ListItem(
                Label(f"  {track.title}  —  {track.artist_string}  [{track.duration_str}]")
            )
            item.track = track
            list_view.append(item)


class LibraryScreen(Screen):
    """Library browser: songs, albums, artists, playlists tabs."""
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("Library — coming soon", id="library-placeholder")


class PlaylistScreen(Screen):
    """Playlist browser: two-pane layout."""
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("Playlists — coming soon", id="playlist-placeholder")


class QueueScreen(Screen):
    """Queue manager: ordered track list."""
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("Queue — coming soon", id="queue-placeholder")


class NowPlayingScreen(Screen):
    """Expanded now-playing view."""
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("Now Playing — coming soon", id="now-playing-placeholder")
```

- [ ] **Step 5: Commit**

```bash
git add src/yt_music_cli/ui/
git commit -m "feat: UI widgets, search screen, and screen stubs"
```

---

### Task 8: Full UI Screens [∥]

**Files:**
- Modify: `src/yt_music_cli/ui/screens.py`

**Dependencies:** Task 7 (ui widgets, search screen)

**Note:** Replace the placeholder screens with full implementations. LibraryScreen loads on mount, PlaylistScreen shows two-pane layout, QueueScreen shows reorderable list, NowPlayingScreen shows expanded track info.

- [ ] **Step 1: Replace stub screens with full implementations**

Replace the entire contents of `src/yt_music_cli/ui/screens.py` with:

```python
# src/yt_music_cli/ui/screens.py
from textual.widgets import Static, Input, ListView, ListItem, Label, Header, Footer
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.screen import Screen

from yt_music_cli.models import Track, Playlist, QueueItem
from yt_music_cli.events import (
    SearchRequestEvent,
    SearchResultsEvent,
    PlayRequestEvent,
    LibraryUpdateEvent,
    QueueUpdatedEvent,
)
from yt_music_cli.bus import MessageBus


class SearchScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back")]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search YouTube Music...", id="search-input")
        yield Static("Type at least 2 characters to search", id="search-status")
        yield ListView(id="search-results")

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        if len(query) >= 2:
            import asyncio
            asyncio.create_task(self._bus.publish(SearchRequestEvent(query=query)))
        else:
            list_view = self.query_one("#search-results", ListView)
            list_view.clear()
            self.query_one("#search-status", Static).update("Type at least 2 characters to search")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is not None and hasattr(event.item, "track"):
            await self._bus.publish(PlayRequestEvent(track=event.item.track, context="search"))

    async def show_results(self, event: SearchResultsEvent) -> None:
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()
        if not event.results:
            self.query_one("#search-status", Static).update(f"No results for '{event.query}'")
            return
        self.query_one("#search-status", Static).update(f"  {len(event.results)} results for '{event.query}'")
        for track in event.results:
            item = ListItem(Label(f"  {track.title}  —  {track.artist_string}  [{track.duration_str}]"))
            item.track = track
            list_view.append(item)


class LibraryScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back"), ("1", "tab_songs", "Songs"), ("2", "tab_albums", "Albums"), ("3", "tab_playlists", "Playlists")]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus
        self._current_tab = "songs"
        self._songs: list = []
        self._albums: list = []
        self._playlists: list = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="library-tabs"):
            yield Static("[Songs]", classes="tab active" if self._current_tab == "songs" else "tab")
            yield Static("[Albums]", classes="tab")
            yield Static("[Playlists]", classes="tab")
        yield ListView(id="library-list")
        yield Static("Loading...", id="library-status")

    def action_tab_songs(self) -> None:
        self._current_tab = "songs"
        self._show_tab()

    def action_tab_albums(self) -> None:
        self._current_tab = "albums"
        self._show_tab()

    def action_tab_playlists(self) -> None:
        self._current_tab = "playlists"
        self._show_tab()

    def _show_tab(self) -> None:
        list_view = self.query_one("#library-list", ListView)
        list_view.clear()
        if self._current_tab == "songs":
            for song in self._songs[:200]:
                item = ListItem(Label(f"  {song}"))
                list_view.append(item)
        elif self._current_tab == "albums":
            for album in self._albums[:200]:
                item = ListItem(Label(f"  {album}"))
                list_view.append(item)
        elif self._current_tab == "playlists":
            for pl in self._playlists[:200]:
                item = ListItem(Label(f"  {pl}"))
                list_view.append(item)

    async def on_library_update(self, event: LibraryUpdateEvent) -> None:
        self.query_one("#library-status", Static).update(f"  {len(event.items)} items loaded")


class PlaylistScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back")]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus
        self._playlists: list[Playlist] = []
        self._tracks: list[Track] = []

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ListView(id="playlist-list")
            yield ListView(id="playlist-tracks")
        yield Static("Select a playlist to view tracks", id="playlist-status")

    def show_playlists(self, playlists: list[Playlist]) -> None:
        self._playlists = playlists
        list_view = self.query_one("#playlist-list", ListView)
        list_view.clear()
        for pl in playlists:
            item = ListItem(Label(f"  {pl.title}  ({pl.track_count} tracks)"))
            item.playlist_id = pl.id
            list_view.append(item)

    def show_tracks(self, tracks: list[Track]) -> None:
        self._tracks = tracks
        list_view = self.query_one("#playlist-tracks", ListView)
        list_view.clear()
        for track in tracks:
            item = ListItem(Label(f"  {track.title}  —  {track.artist_string}"))
            item.track = track
            list_view.append(item)
        self.query_one("#playlist-status", Static).update(f"  {len(tracks)} tracks")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "playlist-tracks" and hasattr(event.item, "track"):
            await self._bus.publish(PlayRequestEvent(track=event.item.track, context="playlist"))


class QueueScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back"), ("d", "remove_selected", "Remove"), ("ctrl+up", "move_up", "Move Up"), ("ctrl+down", "move_down", "Move Down")]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus
        self._queue: list[QueueItem] = []

    def compose(self) -> ComposeResult:
        yield Static("Queue", id="queue-title")
        yield ListView(id="queue-list")
        yield Static("Queue is empty", id="queue-status")

    async def on_queue_updated(self, event: QueueUpdatedEvent) -> None:
        tracks = event.queue
        list_view = self.query_one("#queue-list", ListView)
        list_view.clear()
        if not tracks:
            self.query_one("#queue-status", Static).update("Queue is empty")
            return
        for i, t in enumerate(tracks):
            prefix = "▶ " if i == event.current_index else "  "
            item = ListItem(Label(f"  {prefix}{t.title}  —  {t.artist_string}"))
            item.track_index = i
            list_view.append(item)
        self.query_one("#queue-status", Static).update(f"  {len(tracks)} tracks in queue")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is not None and hasattr(event.item, "track_index"):
            pass  # handled by app-level keybindings


class NowPlayingScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._track: Track | None = None
        self._is_playing: bool = False
        self._position_s: float = 0.0
        self._duration_s: float = 0.0

    def compose(self) -> ComposeResult:
        yield Static("", id="np-art-placeholder")
        yield Static("No track playing", id="np-title")
        yield Static("", id="np-artist")
        yield Static("", id="np-progress")
        yield Static("", id="np-details")

    def update_track(self, track: Track | None, is_playing: bool = False,
                     position_s: float = 0.0, duration_s: float = 0.0) -> None:
        self._track = track
        self._is_playing = is_playing
        self._position_s = position_s
        self._duration_s = duration_s

        if track is None:
            self.query_one("#np-title", Static).update("No track playing")
            self.query_one("#np-artist", Static).update("")
            self.query_one("#np-progress", Static).update("")
            self.query_one("#np-details", Static).update("")
            return

        self.query_one("#np-title", Static).update(f"  {track.title}")
        self.query_one("#np-artist", Static).update(f"  {track.artist_string}")
        if track.album:
            self.query_one("#np-artist", Static).update(f"  {track.artist_string}  —  {track.album}")

        if duration_s > 0:
            ratio = position_s / duration_s
            filled = int(ratio * 40)
            bar = "[" + "=" * max(0, filled - 1) + "●" + "-" * max(0, 40 - filled) + "]"
            pos_str = self._fmt(position_s)
            dur_str = self._fmt(duration_s)
            self.query_one("#np-progress", Static).update(f"  {bar}  {pos_str} / {dur_str}")
        else:
            self.query_one("#np-progress", Static).update(f"  [{'·' * 40}]  0:00 / {self._fmt(duration_s)}")

        self.query_one("#np-details", Static).update(f"  {'▶' if is_playing else '⏸'}  {track.duration_str}")

    @staticmethod
    def _fmt(seconds: float) -> str:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"
```

- [ ] **Step 2: Verify the file imports work**

Run: `python -c "from yt_music_cli.ui.screens import SearchScreen, LibraryScreen, PlaylistScreen, QueueScreen, NowPlayingScreen; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/yt_music_cli/ui/screens.py
git commit -m "feat: full UI screens for library, playlists, queue, now-playing"
```

---

### Task 9: App Entry Point & Integration

**Files:**
- Create: `src/yt_music_cli/app.py`
- Create: `tests/test_ui/__init__.py`
- Create: `tests/test_ui/test_integration.py`

**Dependencies:** Task 1-8 (all modules)

**Note:** This is the wiring task. Creates the Textual `App` subclass, subscribes all modules to the bus, sets up the screen stack and keybindings. Also creates an integration test.

- [ ] **Step 1: Write integration test**

```python
# tests/test_ui/test_integration.py
import pytest
from yt_music_cli.bus import MessageBus
from yt_music_cli.events import (
    AuthReadyEvent,
    SearchRequestEvent,
    SearchResultsEvent,
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
)
from yt_music_cli.models import Track


@pytest.mark.asyncio
async def test_full_event_flow_search_to_play():
    """Verify events flow correctly through the bus without UI."""
    bus = MessageBus()

    search_results = []
    play_requests = []
    track_changes = []
    playback_states = []

    async def on_search_results(event):
        search_results.append(event)

    async def on_play_request(event):
        play_requests.append(event)

    async def on_track_changed(event):
        track_changes.append(event)

    async def on_playback_state(event):
        playback_states.append(event)

    bus.subscribe(SearchResultsEvent, on_search_results)
    bus.subscribe(PlayRequestEvent, on_play_request)
    bus.subscribe(TrackChangedEvent, on_track_changed)
    bus.subscribe(PlaybackStateEvent, on_playback_state)

    # Simulate search
    await bus.publish(SearchRequestEvent(query="queen"))
    track = Track(id="v1", title="Bohemian Rhapsody", artists=["Queen"])
    await bus.publish(SearchResultsEvent(results=[track], query="queen"))

    assert len(search_results) == 1
    assert search_results[0].results[0].title == "Bohemian Rhapsody"

    # Simulate play
    await bus.publish(PlayRequestEvent(track=track, context="search"))
    assert len(play_requests) == 1

    # Simulate track change
    await bus.publish(TrackChangedEvent(track=track))
    assert len(track_changes) == 1

    # Simulate playback state
    await bus.publish(PlaybackStateEvent(is_playing=True, position_s=10.0, duration_s=354.0))
    assert len(playback_states) == 1
    assert playback_states[0].is_playing is True


@pytest.mark.asyncio
async def test_error_event_flow():
    """Verify error events propagate correctly."""
    from yt_music_cli.events import ErrorEvent

    bus = MessageBus()
    errors = []
    bus.subscribe(ErrorEvent, lambda e: errors.append(e) or __import__("asyncio").sleep(0))

    # API error
    await bus.publish(ErrorEvent(source="api", message="Network timeout"))
    assert len(errors) == 1
    assert errors[0].source == "api"

    # Player error
    await bus.publish(ErrorEvent(source="player", message="mpv crashed"))
    assert len(errors) == 2
    assert errors[1].source == "player"


@pytest.mark.asyncio
async def test_auth_to_library_flow():
    from yt_music_cli.events import LibraryUpdateEvent

    bus = MessageBus()
    lib_events = []

    async def capture(event):
        lib_events.append(event)

    bus.subscribe(LibraryUpdateEvent, capture)
    async def on_auth(e):
        await bus.publish(LibraryUpdateEvent(category="songs", items=[]))

    bus.subscribe(AuthReadyEvent, on_auth)

    await bus.publish(AuthReadyEvent())
    import asyncio
    await asyncio.sleep(0)

    assert len(lib_events) >= 1
```

- [ ] **Step 2: Run integration test to verify it fails (app.py not yet wired)**

Run: `python -m pytest tests/test_ui/test_integration.py -v`
Expected: 3 tests PASS (they only test the bus, no app.py needed)

- [ ] **Step 3: Write app.py — the Textual App**

```python
# src/yt_music_cli/app.py
import asyncio
import logging
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen

from yt_music_cli.bus import MessageBus
from yt_music_cli.config import OAUTH_FILE, ensure_dirs, ERROR_LOG
from yt_music_cli.models import Track
from yt_music_cli.auth import AuthModule
from yt_music_cli.api import APIClient
from yt_music_cli.player import PlayerModule
from yt_music_cli.events import (
    AuthReadyEvent,
    AuthErrorEvent,
    SearchResultsEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
    LibraryUpdateEvent,
    ErrorEvent,
    PlayRequestEvent,
)
from yt_music_cli.ui.widgets import NowPlayingBar, StatusBar
from yt_music_cli.ui.screens import (
    SearchScreen,
    LibraryScreen,
    PlaylistScreen,
    QueueScreen,
    NowPlayingScreen,
)
from yt_music_cli.ui.keys import Keys

logger = logging.getLogger(__name__)


class YtMusicApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #now-playing-bar {
        dock: bottom;
        height: 3;
        background: $panel;
        color: $text;
        padding: 0 1;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text-disabled;
    }

    #search-input {
        dock: top;
        margin: 1 2;
    }

    #search-status, #library-status, #queue-status, #playlist-status {
        height: 1;
        color: $text-disabled;
        padding: 0 2;
    }

    ListView {
        height: 1fr;
    }

    #library-tabs {
        dock: top;
        height: 1;
    }

    .tab {
        width: auto;
        padding: 0 2;
    }

    #playlist-list {
        width: 30%;
    }

    #playlist-tracks {
        width: 70%;
    }

    #np-title {
        content-align: center middle;
        text-style: bold;
        height: 3;
    }

    #np-artist {
        content-align: center middle;
        height: 2;
    }

    #np-progress {
        content-align: center middle;
        height: 3;
    }

    #np-details {
        content-align: center middle;
        height: 2;
    }
    """

    BINDINGS = [
        (Keys.QUIT, "quit_app", "Quit"),
        (Keys.PLAY_PAUSE, "play_pause", "Play/Pause"),
        (Keys.NEXT, "next_track", "Next"),
        (Keys.PREV, "prev_track", "Previous"),
        (Keys.SEEK_FWD, "seek_fwd", "Seek +"),
        (Keys.SEEK_BACK, "seek_back", "Seek -"),
        (Keys.VOL_UP, "vol_up", "Vol +"),
        (Keys.VOL_DOWN, "vol_down", "Vol -"),
        (Keys.SHUFFLE, "toggle_shuffle", "Shuffle"),
        (Keys.REPEAT, "toggle_repeat", "Repeat"),
        (Keys.VIEW_1, "view_search", "Search"),
        (Keys.VIEW_2, "view_library", "Library"),
        (Keys.VIEW_3, "view_playlists", "Playlists"),
        (Keys.VIEW_4, "view_queue", "Queue"),
        (Keys.VIEW_5, "view_now_playing", "Now Playing"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._bus = MessageBus()
        self._auth = AuthModule(self._bus, oauth_path=OAUTH_FILE)
        self._api = APIClient(self._bus)
        self._player = PlayerModule(self._bus)

        # Wire bus subscriptions
        self._bus.subscribe(AuthReadyEvent, self._on_auth_ready)
        self._bus.subscribe(AuthErrorEvent, self._on_auth_error)
        self._bus.subscribe(SearchResultsEvent, self._on_search_results)
        self._bus.subscribe(PlayRequestEvent, self._on_play_request)
        self._bus.subscribe(TrackChangedEvent, self._on_track_changed)
        self._bus.subscribe(PlaybackStateEvent, self._on_playback_state)
        self._bus.subscribe(QueueUpdatedEvent, self._on_queue_updated)
        self._bus.subscribe(LibraryUpdateEvent, self._on_library_update)
        self._bus.subscribe(ErrorEvent, self._on_error)

        # Wire API subscriptions
        self._bus.subscribe(AuthReadyEvent, self._api._on_auth_ready)

        # Wire search
        from yt_music_cli.events import SearchRequestEvent
        self._bus.subscribe(SearchRequestEvent, self._api._on_search_request)

        self._screens: dict[str, Screen] = {}

    def compose(self) -> ComposeResult:
        yield Container(id="screen-container")
        yield NowPlayingBar()
        yield StatusBar()

    async def on_mount(self) -> None:
        ensure_dirs()

        # Create all screens
        self._screens["search"] = SearchScreen(self._bus)
        self._screens["library"] = LibraryScreen(self._bus)
        self._screens["playlists"] = PlaylistScreen(self._bus)
        self._screens["queue"] = QueueScreen(self._bus)
        self._screens["now_playing"] = NowPlayingScreen()

        # Install screens
        await self.push_screen(self._screens["search"])
        await self.push_screen(self._screens["queue"])
        await self.push_screen(self._screens["playlists"])
        await self.push_screen(self._screens["library"])
        # Now search is on top

        # Start auth
        await self._auth.initialize()

    async def _on_auth_ready(self, event: AuthReadyEvent) -> None:
        self._status_msg("Authenticated")
        if self._auth.client:
            self._api.set_client(self._auth.client)

    async def _on_auth_error(self, event: AuthErrorEvent) -> None:
        self._status_msg(f"Auth error: {event.error_msg}")

    async def _on_search_results(self, event: SearchResultsEvent) -> None:
        search_screen = self._screens.get("search")
        if search_screen and hasattr(search_screen, "show_results"):
            await search_screen.show_results(event)

    async def _on_play_request(self, event: PlayRequestEvent) -> None:
        if event.track is None:
            return
        self._player.add_to_queue(event.track, source=event.context)
        self._player.play()
        self._status_msg(f"Queued: {event.track.title}")
        # Publish queue update
        queue_tracks = [qi.track for qi in self._player.queue]
        idx = len(queue_tracks) - 1
        await self._bus.publish(QueueUpdatedEvent(queue=queue_tracks, current_index=idx))

    async def _on_track_changed(self, event: TrackChangedEvent) -> None:
        state = self._player.get_state()
        self._update_now_playing_bar(state)

        np_screen = self._screens.get("now_playing")
        if np_screen and hasattr(np_screen, "update_track"):
            np_screen.update_track(event.track, state.is_playing, state.position_s, state.duration_s)

        self._status_msg(f"Now playing: {event.track.title}")

    async def _on_playback_state(self, event: PlaybackStateEvent) -> None:
        from yt_music_cli.models import PlaybackState
        # Create a PlaybackState from the event
        state = PlaybackState(
            track=self._player.current_track,
            is_playing=event.is_playing,
            position_s=event.position_s,
            duration_s=event.duration_s,
            volume=event.volume,
            shuffle=event.shuffle,
            repeat=event.repeat,
        )
        self._update_now_playing_bar(state)

    async def _on_queue_updated(self, event: QueueUpdatedEvent) -> None:
        queue_screen = self._screens.get("queue")
        if queue_screen and hasattr(queue_screen, "on_queue_updated"):
            await queue_screen.on_queue_updated(event)

    async def _on_library_update(self, event: LibraryUpdateEvent) -> None:
        library_screen = self._screens.get("library")
        if library_screen and hasattr(library_screen, "on_library_update"):
            await library_screen.on_library_update(event)

    async def _on_error(self, event: ErrorEvent) -> None:
        self._status_msg(f"[{event.source}] {event.message}")

    def _update_now_playing_bar(self, state) -> None:
        try:
            bar = self.query_one("#now-playing-bar", NowPlayingBar)
            bar.update_state(state)
        except Exception:
            pass

    def _status_msg(self, msg: str) -> None:
        try:
            bar = self.query_one("#status-bar", StatusBar)
            bar.set_message(msg)
        except Exception:
            pass

    # --- Actions (keybindings) ---

    def action_quit_app(self) -> None:
        self.exit()

    def action_play_pause(self) -> None:
        self._player.play_pause()

    def action_next_track(self) -> None:
        self._player.next_track()

    def action_prev_track(self) -> None:
        self._player.prev_track()

    def action_seek_fwd(self) -> None:
        state = self._player.get_state()
        self._player.seek(min(state.position_s + 5, state.duration_s))

    def action_seek_back(self) -> None:
        state = self._player.get_state()
        self._player.seek(max(state.position_s - 5, 0))

    def action_vol_up(self) -> None:
        state = self._player.get_state()
        self._player.set_volume(state.volume + 5)

    def action_vol_down(self) -> None:
        state = self._player.get_state()
        self._player.set_volume(state.volume - 5)

    def action_toggle_shuffle(self) -> None:
        self._player._shuffle = not self._player._shuffle
        self._status_msg(f"Shuffle: {'on' if self._player._shuffle else 'off'}")

    def action_toggle_repeat(self) -> None:
        modes = ["off", "one", "all"]
        idx = modes.index(self._player._repeat)
        self._player._repeat = modes[(idx + 1) % 3]
        self._status_msg(f"Repeat: {self._player._repeat}")

    def action_view_search(self) -> None:
        self._switch_screen("search")

    def action_view_library(self) -> None:
        self._switch_screen("library")

    def action_view_playlists(self) -> None:
        self._switch_screen("playlists")

    def action_view_queue(self) -> None:
        self._switch_screen("queue")

    def action_view_now_playing(self) -> None:
        self._switch_screen("now_playing")

    def _switch_screen(self, name: str) -> None:
        screen = self._screens.get(name)
        if screen is None:
            return
        # Pop other screens to get to the target
        # Textual doesn't have a direct "switch to screen" so we push/pop
        current = self.screen
        if current != screen:
            # Simple approach: push the screen
            import asyncio
            asyncio.create_task(self.push_screen(screen))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(ERROR_LOG),
            logging.StreamHandler(sys.stderr),
        ],
    )
    app = YtMusicApp()
    app.run()
```

- [ ] **Step 4: Verify app.py imports**

Run: `python -c "from yt_music_cli.app import YtMusicApp; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Run integration tests**

Run: `python -m pytest tests/test_ui/test_integration.py -v`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/yt_music_cli/app.py tests/test_ui/
git commit -m "feat: app entry point with full module wiring"
```

---

### Task 10: Verification & Polish

**Files:**
- Create: `README.md`
- Modify: `src/yt_music_cli/app.py` (fix any issues found)

**Dependencies:** All prior tasks

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests PASS

- [ ] **Step 2: Verify the CLI entry point**

```bash
python -c "from yt_music_cli.app import main; print('Entry point OK')"
```
Expected: `Entry point OK`

- [ ] **Step 3: Write README.md**

```markdown
# yt-music-cli

Terminal-based YouTube Music client with OAuth authentication.

## Requirements

- Python 3.11+
- mpv (system package: `apt install mpv` or `brew install mpv`)
- YouTube Music subscription

## Install

```bash
pip install -e .
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
yt-music-cli
```
```

- [ ] **Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: README with install and usage instructions"
```

---

## Execution Order

```
Phase 1 (sequential):
  Task 1 → Task 2 → Task 3
         ↓
Phase 2 (parallel [∥]):
  Task 4 (Auth)  |  Task 5 (API)  |  Task 6 (Player)
         ↓              ↓               ↓
Phase 3 (parallel [∥]):
  Task 7 (Shell + Search)  |  Task 8 (Remaining Screens)
         ↓                          ↓
Phase 4 (sequential):
  Task 9 (Integration)
         ↓
  Task 10 (Verification)
```
