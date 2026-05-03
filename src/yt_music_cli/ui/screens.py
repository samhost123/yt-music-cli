import asyncio

from textual.widgets import Static, Input, ListView, ListItem, Label
from textual.containers import Horizontal
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
        self._debounce_timer: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search YouTube Music...", id="search-input")
        yield Static("Type at least 2 characters to search", id="search-status")
        yield ListView(id="search-results")

    def on_input_changed(self, event: Input.Changed) -> None:
        import asyncio
        query = event.value.strip()
        if len(query) < 2:
            list_view = self.query_one("#search-results", ListView)
            list_view.clear()
            self.query_one("#search-status", Static).update("Type at least 2 characters to search")
            return
        if self._debounce_timer and not self._debounce_timer.done():
            self._debounce_timer.cancel()
        self._debounce_timer = asyncio.create_task(self._debounced_search(query))

    async def _debounced_search(self, query: str) -> None:
        import asyncio
        await asyncio.sleep(0.3)
        await self._bus.publish(SearchRequestEvent(query=query))

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
    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("1", "tab_songs", "Songs"),
        ("2", "tab_albums", "Albums"),
        ("3", "tab_playlists", "Playlists"),
    ]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus
        self._current_tab = "songs"
        self._songs: list = []
        self._albums: list = []
        self._playlists: list = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="library-tabs"):
            yield Static("[Songs]", classes="tab")
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
        items = {
            "songs": self._songs,
            "albums": self._albums,
            "playlists": self._playlists,
        }.get(self._current_tab, [])
        for item in items[:200]:
            list_view.append(ListItem(Label(f"  {item}")))

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
    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("d", "remove_selected", "Remove"),
    ]

    def __init__(self, bus: MessageBus) -> None:
        super().__init__()
        self._bus = bus

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
            prefix = "\u25b6 " if i == event.current_index else "  "
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

    def compose(self) -> ComposeResult:
        yield Static("", id="np-art-placeholder")
        yield Static("No track playing", id="np-title")
        yield Static("", id="np-artist")
        yield Static("", id="np-progress")
        yield Static("", id="np-details")

    def update_track(self, track: Track | None, is_playing: bool = False,
                     position_s: float = 0.0, duration_s: float = 0.0) -> None:
        self._track = track
        if track is None:
            self.query_one("#np-title", Static).update("No track playing")
            self.query_one("#np-artist", Static).update("")
            self.query_one("#np-progress", Static).update("")
            self.query_one("#np-details", Static).update("")
            return

        self.query_one("#np-title", Static).update(f"  {track.title}")
        self.query_one("#np-artist", Static).update(
            f"  {track.artist_string}" + (f"  —  {track.album}" if track.album else "")
        )
        if duration_s > 0:
            ratio = position_s / duration_s
            filled = int(ratio * 40)
            bar = "[" + "=" * max(0, filled - 1) + "\u25cf" + "-" * max(0, 40 - filled) + "]"
            self.query_one("#np-progress", Static).update(
                f"  {bar}  {self._fmt(position_s)} / {self._fmt(duration_s)}"
            )
        else:
            self.query_one("#np-progress", Static).update(f"  [{'\u00b7' * 40}]  0:00 / {self._fmt(duration_s)}")
        self.query_one("#np-details", Static).update(f"  {'\u25b6' if is_playing else '\u23f8'}  {track.duration_str}")

    @staticmethod
    def _fmt(seconds: float) -> str:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"
