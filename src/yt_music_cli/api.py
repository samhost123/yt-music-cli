import logging

from ytmusicapi import YTMusic

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import (
    SearchRequestEvent,
    SearchResultsEvent,
    AuthReadyEvent,
    ErrorEvent,
    LibraryUpdateEvent,
)
from yt_music_cli.models import Track, Playlist

logger = logging.getLogger(__name__)


def _parse_artists(raw: dict) -> list[str]:
    artists = []
    if "artists" in raw and raw["artists"]:
        artists = [a.get("name", "Unknown Artist") for a in raw["artists"]]
    if not artists and raw.get("artist"):
        artists = [raw["artist"]]
    if not artists and raw.get("byline"):
        artists = [raw["byline"]]
    if not artists:
        artists = ["Unknown Artist"]
    return artists


def _parse_duration(raw: dict) -> int:
    if raw.get("duration_seconds"):
        return raw["duration_seconds"] * 1000
    if raw.get("duration"):
        try:
            parts = str(raw["duration"]).split(":")
            if len(parts) == 3:
                return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
            return (int(parts[0]) * 60 + int(parts[1])) * 1000
        except (ValueError, IndexError):
            pass
    return 0


def _parse_thumbnail(raw: dict) -> str:
    if raw.get("thumbnails"):
        return raw["thumbnails"][0].get("url", "")
    return ""


def _parse_track(raw: dict) -> Track:
    album = None
    if isinstance(raw.get("album"), dict):
        album = raw["album"].get("name")

    return Track(
        id=raw.get("videoId", ""),
        title=raw.get("title", "Unknown"),
        artists=_parse_artists(raw),
        album=album,
        duration_ms=_parse_duration(raw),
        thumbnail_url=_parse_thumbnail(raw),
    )


def _parse_library_song(raw: dict) -> Track:
    return _parse_track(raw)


def _parse_playlist_track(raw: dict) -> Track:
    inner = raw.copy()
    if isinstance(inner.get("track"), dict):
        inner = inner["track"]
    if isinstance(inner.get("video"), dict):
        inner = inner["video"]
    inner.setdefault("videoId", inner.get("videoId") or "")
    inner.setdefault("title", inner.get("title") or "Unknown")
    return _parse_track(inner)


class APIClient:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._ytmusic: YTMusic | None = None
        bus.subscribe(SearchRequestEvent, self._on_search_request)
        bus.subscribe(AuthReadyEvent, self._on_auth_ready)

    def set_client(self, ytmusic: YTMusic) -> None:
        self._ytmusic = ytmusic

    async def _on_auth_ready(self, event: AuthReadyEvent) -> None:
        try:
            songs = await self.get_library_songs()
            await self._bus.publish(LibraryUpdateEvent(category="songs", items=songs))
        except Exception:
            await self._bus.publish(LibraryUpdateEvent(category="songs", items=[]))
        try:
            playlists = await self.get_library_playlists()
            await self._bus.publish(LibraryUpdateEvent(category="playlists", items=playlists))
        except Exception:
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

    async def get_library_songs(self) -> list[Track]:
        raw = await self.fetch_library_songs()
        tracks = []
        for item in raw:
            try:
                tracks.append(_parse_library_song(item))
            except Exception:
                logger.exception("Failed to parse library song")
        return tracks

    async def get_library_playlists(self) -> list[Playlist]:
        if not self._ytmusic:
            return []
        try:
            raw = self._ytmusic.get_library_playlists(limit=9999)
            playlists = []
            for item in raw:
                playlists.append(Playlist(
                    id=item.get("playlistId", ""),
                    title=item.get("title", "Unknown"),
                    track_count=item.get("count", 0),
                    thumbnail_url=_parse_thumbnail(item),
                ))
            return playlists
        except Exception as e:
            logger.exception("Library playlists fetch failed")
            return []

    async def get_library_albums(self) -> list:
        if not self._ytmusic:
            return []
        try:
            raw = self._ytmusic.get_library_albums(limit=9999)
            return raw
        except Exception:
            logger.exception("Library albums fetch failed")
            return []

    async def get_playlist_tracks(self, playlist_id: str) -> list[Track]:
        raw = await self.fetch_playlist_tracks(playlist_id)
        tracks = []
        for item in raw:
            try:
                tracks.append(_parse_playlist_track(item))
            except Exception:
                logger.exception("Failed to parse playlist track")
        return tracks

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
