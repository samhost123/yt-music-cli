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
        bus.subscribe(SearchRequestEvent, self._on_search_request)
        bus.subscribe(AuthReadyEvent, self._on_auth_ready)

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
