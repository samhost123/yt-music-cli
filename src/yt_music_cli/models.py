from dataclasses import dataclass
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
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
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
