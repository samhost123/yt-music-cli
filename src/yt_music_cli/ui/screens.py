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
from yt_music_cli.ui.art import render_album_art


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
            album_part = f"  —  [{track.album}]" if track.album else ""
            item = ListItem(Label(f"  {track.title} - {track.artist_string}{album_part}  [{track.duration_str}]"))
            item.track = track
            list_view.append(item)


class LibraryScreen(Screen):
    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("1", "tab_songs", "Songs"),
        ("2", "tab_albums", "Albums"),
        ("3", "tab_playlists", "Playlists"),
    ]

    def __init__(self, bus: MessageBus, api: object) -> None:
        super().__init__()
        self._bus = bus
        self._api = api
        self._current_tab = "songs"
        self._songs: list[Track] = []
        self._albums: list = []
        self._playlists: list[Playlist] = []
        self._loaded = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="library-tabs"):
            yield Static("[Songs]", classes="tab")
            yield Static("[Albums]", classes="tab")
            yield Static("[Playlists]", classes="tab")
        yield ListView(id="library-list")
        yield Static("Loading...", id="library-status")

    async def on_mount(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        await self._load_library()

    async def _load_library(self) -> None:
        try:
            self._songs = await self._api.get_library_songs()
        except Exception:
            self._songs = []
        try:
            self._albums = await self._api.get_library_albums()
        except Exception:
            self._albums = []
        try:
            self._playlists = await self._api.get_library_playlists()
        except Exception:
            self._playlists = []

        self.query_one("#library-status", Static).update(
            f"  Songs: {len(self._songs)}  |  Albums: {len(self._albums)}  |  Playlists: {len(self._playlists)}"
        )
        self._show_tab()

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
            for track in self._songs[:200]:
                item = ListItem(Label(f"  {track.title}  —  {track.artist_string}  [{track.duration_str}]"))
                item.track = track
                list_view.append(item)
            if not self._songs:
                list_view.append(ListItem(Label("  No songs in library")))
        elif self._current_tab == "albums":
            if self._albums:
                for album in self._albums[:200]:
                    title = album.get("title", "Unknown Album")
                    artists = album.get("artists", "Unknown Artist")
                    if isinstance(artists, list):
                        artists = ", ".join(a.get("name", "?") for a in artists)
                    elif isinstance(artists, str):
                        pass
                    else:
                        artists = str(artists)
                    item = ListItem(Label(f"  {title}  —  {artists}"))
                    list_view.append(item)
            else:
                list_view.append(ListItem(Label("  Albums coming soon")))
        elif self._current_tab == "playlists":
            for pl in self._playlists[:200]:
                item = ListItem(Label(f"  {pl.title}  ({pl.track_count} tracks)"))
                item.playlist = pl
                list_view.append(item)
            if not self._playlists:
                list_view.append(ListItem(Label("  No playlists in library")))

    async def on_library_update(self, event: LibraryUpdateEvent) -> None:
        if event.category == "songs":
            self._songs = event.items
        elif event.category == "playlists":
            self._playlists = event.items
        self.query_one("#library-status", Static).update(
            f"  Songs: {len(self._songs)}  |  Albums: {len(self._albums)}  |  Playlists: {len(self._playlists)}"
        )
        self._show_tab()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is not None:
            if hasattr(event.item, "track"):
                await self._bus.publish(PlayRequestEvent(track=event.item.track, context="library"))
            elif hasattr(event.item, "playlist"):
                pass  # Could navigate to playlist in future


class PlaylistScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back")]

    def __init__(self, bus: MessageBus, api: object) -> None:
        super().__init__()
        self._bus = bus
        self._api = api
        self._playlists: list[Playlist] = []
        self._tracks: list[Track] = []
        self._loaded = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ListView(id="playlist-list")
            yield ListView(id="playlist-tracks")
        yield Static("Select a playlist to view tracks", id="playlist-status")

    async def on_mount(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        await self._load_playlists()

    async def _load_playlists(self) -> None:
        try:
            self._playlists = await self._api.get_library_playlists()
        except Exception:
            self._playlists = []
        self._show_playlists()

    def _show_playlists(self) -> None:
        list_view = self.query_one("#playlist-list", ListView)
        list_view.clear()
        if not self._playlists:
            list_view.append(ListItem(Label("  No playlists found")))
            return
        for pl in self._playlists:
            item = ListItem(Label(f"  {pl.title}  ({pl.track_count} tracks)"))
            item.playlist_id = pl.id
            list_view.append(item)
        self.query_one("#playlist-status", Static).update(
            f"  {len(self._playlists)} playlists  —  select one to view tracks"
        )

    async def _load_tracks(self, playlist_id: str) -> None:
        self.query_one("#playlist-status", Static).update("  Loading tracks...")
        try:
            self._tracks = await self._api.get_playlist_tracks(playlist_id)
        except Exception:
            self._tracks = []
        self._show_tracks()

    def show_playlists(self, playlists: list[Playlist]) -> None:
        self._playlists = playlists
        self._show_playlists()

    def show_tracks(self, tracks: list[Track]) -> None:
        self._tracks = tracks
        self._show_tracks()

    def _show_tracks(self) -> None:
        list_view = self.query_one("#playlist-tracks", ListView)
        list_view.clear()
        if not self._tracks:
            list_view.append(ListItem(Label("  No tracks in this playlist")))
            self.query_one("#playlist-status", Static).update("  0 tracks")
            return
        for track in self._tracks:
            item = ListItem(Label(f"  {track.title}  —  {track.artist_string}  [{track.duration_str}]"))
            item.track = track
            list_view.append(item)
        self.query_one("#playlist-status", Static).update(f"  {len(self._tracks)} tracks")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "playlist-list":
            if event.item is not None and hasattr(event.item, "playlist_id"):
                await self._load_tracks(event.item.playlist_id)
        elif event.control.id == "playlist-tracks":
            if event.item is not None and hasattr(event.item, "track"):
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


class HelpScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        help_text = """\
  Keybindings
  ───────────
  /          Focus search
  Enter      Play selected track
  Space      Play / Pause
  n / p      Next / Previous track
  ← / →      Seek backward / forward
  + / -      Volume up / down
  s          Toggle shuffle
  r          Toggle repeat (off → one → all)
  a          Add to queue
  d          Remove from queue/playlist
  1-5        Jump to view (Search/Library/Playlists/Queue/Now Playing)
  Tab        Cycle views
  ?          This help
  q          Quit"""
        yield Static(help_text, id="help-text")


class NowPlayingScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._track: Track | None = None
        self._is_playing: bool = False
        self._position_s: float = 0.0
        self._duration_s: float = 0.0
        self._volume: int = 100
        self._shuffle: bool = False
        self._repeat: str = "off"

    def compose(self) -> ComposeResult:
        yield Static("", id="np-art")
        yield Static("No track playing", id="np-title")
        yield Static("", id="np-artist")
        yield Static("", id="np-progress")
        yield Static("", id="np-flags")
        yield Static("", id="np-volume")
        yield Static("", id="np-controls")

    def update_track(self, track: Track | None, is_playing: bool = False,
                     position_s: float = 0.0, duration_s: float = 0.0,
                     volume: int = 100, shuffle: bool = False, repeat: str = "off") -> None:
        self._track = track
        self._is_playing = is_playing
        self._position_s = position_s
        self._duration_s = duration_s
        self._volume = volume
        self._shuffle = shuffle
        self._repeat = repeat

        if track is None:
            self.query_one("#np-art", Static).update("")
            self.query_one("#np-title", Static).update("No track playing")
            self.query_one("#np-artist", Static).update("")
            self.query_one("#np-progress", Static).update("")
            self.query_one("#np-flags", Static).update("")
            self.query_one("#np-volume", Static).update("")
            self.query_one("#np-controls", Static).update("")
            return

        art = ""
        if track.thumbnail_url:
            art = render_album_art(track.thumbnail_url, 40, 12)
        self.query_one("#np-art", Static).update(art if art else "")
        self.query_one("#np-title", Static).update(f"  [bold]{track.title}[/bold]")
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

        flags = []
        if self._shuffle:
            flags.append("\U0001f500 Shuffle")
        if self._repeat == "one":
            flags.append("\U0001f502 Repeat One")
        elif self._repeat == "all":
            flags.append("\U0001f501 Repeat All")
        self.query_one("#np-flags", Static).update("  " + "  |  ".join(flags) if flags else "")

        vol_filled = int(self._volume / 100 * 20)
        vol_bar = "[" + "\u25ac" * vol_filled + "\u2500" * (20 - vol_filled) + "]"
        self.query_one("#np-volume", Static).update(f"  Vol: {vol_bar} {self._volume}%")

        self.query_one("#np-controls", Static).update(
            "  Space:Pause  n/p:Skip  \u2190/\u2192:Seek  +/-:Vol"
        )

    @staticmethod
    def _fmt(seconds: float) -> str:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"
