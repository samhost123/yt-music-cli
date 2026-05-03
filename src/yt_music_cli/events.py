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
