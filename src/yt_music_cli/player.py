import logging
import asyncio
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
        self._stream_urls: dict[str, str] = {}
        self._shuffle: bool = False
        self._repeat: str = "off"
        self._lock = asyncio.Lock()

        bus.subscribe(PlayRequestEvent, self._on_play_request)

    @property
    def queue(self) -> list[QueueItem]:
        return list(self._queue)

    @property
    def current_track(self) -> Optional[Track]:
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index].track
        return None

    def add_to_queue(self, track: Track, source: str = "") -> None:
        self._queue.append(QueueItem(track=track, source=source))
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._bus.publish(QueueUpdatedEvent(
                queue=[item.track for item in self._queue],
                current_index=self._current_index,
            )))
        except RuntimeError:
            pass

    def remove_from_queue(self, index: int) -> None:
        if 0 <= index < len(self._queue):
            self._queue.pop(index)
            if self._current_index >= len(self._queue):
                self._current_index = max(0, len(self._queue) - 1)

    def clear_queue(self) -> None:
        self._queue.clear()
        self._current_index = 0

    def play_pause(self) -> None:
        if self._mpv:
            try:
                self._mpv._set_property("pause", not self._mpv.pause)
            except Exception:
                pass

    def next_track(self) -> None:
        if not self._queue:
            return
        self._current_index = (self._current_index + 1) % len(self._queue)

    def prev_track(self) -> None:
        if not self._queue:
            return
        self._current_index = (self._current_index - 1) % len(self._queue)

    def set_volume(self, volume: int) -> None:
        if self._mpv:
            try:
                self._mpv._set_property("volume", max(0, min(100, volume)))
            except Exception:
                pass

    def seek(self, position_s: float) -> None:
        if self._mpv:
            try:
                self._mpv._set_property("time-pos", position_s)
            except Exception:
                pass

    def play(self) -> None:
        if not self._queue:
            return
        if not self._mpv:
            mpv_cls = _mpv_safe()
            if mpv_cls:
                self._mpv = mpv_cls()
        self._play_current()

    def _play_current(self) -> None:
        track = self.current_track
        if not track:
            return

    async def _on_play_request(self, event: PlayRequestEvent) -> None:
        if event.track.id not in self._stream_urls:
            await self._bus.publish(ErrorEvent(
                source="player",
                message=f"Track id '{event.track.id}' not found",
            ))
            return
        self.add_to_queue(event.track, source=event.context)
        await self._bus.publish(TrackChangedEvent(track=event.track))

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
