import asyncio
import logging
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import Screen

from yt_music_cli.bus import MessageBus
from yt_music_cli.config import OAUTH_FILE, ensure_dirs, ERROR_LOG
from yt_music_cli.models import Track, PlaybackState
from yt_music_cli.auth import AuthModule
from yt_music_cli.api import APIClient
from yt_music_cli.player import PlayerModule
from yt_music_cli.events import (
    AuthReadyEvent,
    AuthErrorEvent,
    SearchRequestEvent,
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
    Screen { layout: vertical; }
    #now-playing-bar {
        dock: bottom; height: 3; background: $panel;
        color: $text; padding: 0 1;
    }
    #status-bar {
        dock: bottom; height: 1; background: $boost;
        color: $text-disabled;
    }
    #search-input { dock: top; margin: 1 2; }
    #search-status, #library-status, #queue-status, #playlist-status {
        height: 1; color: $text-disabled; padding: 0 2;
    }
    ListView { height: 1fr; }
    #library-tabs { dock: top; height: 1; }
    .tab { width: auto; padding: 0 2; }
    #playlist-list { width: 30%; }
    #playlist-tracks { width: 70%; }
    #np-title { content-align: center middle; text-style: bold; height: 3; }
    #np-artist { content-align: center middle; height: 2; }
    #np-progress { content-align: center middle; height: 3; }
    #np-details { content-align: center middle; height: 2; }
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

        self._bus.subscribe(AuthReadyEvent, self._on_auth_ready)
        self._bus.subscribe(AuthErrorEvent, self._on_auth_error)
        self._bus.subscribe(SearchResultsEvent, self._on_search_results)
        self._bus.subscribe(PlayRequestEvent, self._on_play_request)
        self._bus.subscribe(TrackChangedEvent, self._on_track_changed)
        self._bus.subscribe(PlaybackStateEvent, self._on_playback_state)
        self._bus.subscribe(QueueUpdatedEvent, self._on_queue_updated)
        self._bus.subscribe(LibraryUpdateEvent, self._on_library_update)
        self._bus.subscribe(ErrorEvent, self._on_error)

        self._screens: dict[str, Screen] = {}

    def compose(self) -> ComposeResult:
        yield Container(id="screen-container")
        yield NowPlayingBar()
        yield StatusBar()

    async def on_mount(self) -> None:
        ensure_dirs()

        self._screens["search"] = SearchScreen(self._bus)
        self._screens["library"] = LibraryScreen(self._bus)
        self._screens["playlists"] = PlaylistScreen(self._bus)
        self._screens["queue"] = QueueScreen(self._bus)
        self._screens["now_playing"] = NowPlayingScreen()

        await self.push_screen(self._screens["now_playing"])
        await self.push_screen(self._screens["queue"])
        await self.push_screen(self._screens["playlists"])
        await self.push_screen(self._screens["library"])
        await self.push_screen(self._screens["search"])

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

    async def _on_track_changed(self, event: TrackChangedEvent) -> None:
        state = self._player.get_state()
        self._update_now_playing_bar(state)
        np_screen = self._screens.get("now_playing")
        if np_screen and hasattr(np_screen, "update_track"):
            np_screen.update_track(event.track, state.is_playing, state.position_s, state.duration_s)
        self._status_msg(f"Now playing: {event.track.title}")

    async def _on_playback_state(self, event: PlaybackStateEvent) -> None:
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

    # --- Actions ---

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
        if screen is None or self.screen == screen:
            return
        asyncio.create_task(self.push_screen(screen))


def main() -> None:
    import os
    os.environ.setdefault("TEXTUAL", "1")
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
