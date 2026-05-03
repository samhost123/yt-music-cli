from textual.widgets import Static
from yt_music_cli.models import PlaybackState


class NowPlayingBar(Static):
    """Persistent bar showing current track, progress, and controls."""

    def __init__(self) -> None:
        super().__init__("", id="now-playing-bar")
        self._track = None
        self._is_playing: bool = False
        self._position_s: float = 0.0
        self._duration_s: float = 0.0
        self._volume: int = 100
        self._shuffle: bool = False
        self._repeat: str = "off"

    def update_state(self, state: PlaybackState) -> None:
        self._track = state.track
        self._is_playing = state.is_playing
        self._position_s = state.position_s
        self._duration_s = state.duration_s
        self._volume = state.volume
        self._shuffle = state.shuffle
        self._repeat = state.repeat
        self.refresh()

    def render(self) -> str:
        if not self._track:
            return "  No track playing"

        play_icon = "\u25b6" if not self._is_playing else "\u23f8"
        title = self._track.title[:40]
        artist = self._track.artist_string[:40]

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

        vol_str = f" Vol:{self._volume}%"

        return f"  {play_icon} {title} \u2014 {artist}  {bar} {pos_str} / {dur_str}{flags}{vol_str}"

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
