import asyncio
import logging
import random
from typing import Optional

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import (
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
    NeedStreamUrlEvent,
    ErrorEvent,
)
from yt_music_cli.models import Track, QueueItem, PlaybackState

logger = logging.getLogger(__name__)

REPEAT_MODES = ("off", "one", "all")


def _mpv_safe() -> object | None:
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
        self._progress_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._auto_advance: bool = False
        self._unshuffled_queue: list[QueueItem] | None = None

    @property
    def queue(self) -> list[QueueItem]:
        return list(self._queue)

    @property
    def current_track(self) -> Optional[Track]:
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index].track
        return None

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> str:
        return self._repeat

    def add_to_queue(self, track: Track, source: str = "") -> None:
        item = QueueItem(track=track, source=source)
        if self._shuffle and self._unshuffled_queue is not None:
            self._unshuffled_queue.append(item)
            if len(self._queue) <= 1:
                self._queue.append(item)
            else:
                pos = random.randint(1, len(self._queue))
                self._queue.insert(pos, item)
        else:
            self._queue.append(item)
        self._publish_queue_update()

    def remove_from_queue(self, index: int) -> None:
        if 0 <= index < len(self._queue):
            removed = self._queue.pop(index)
            if self._unshuffled_queue is not None:
                try:
                    self._unshuffled_queue.remove(removed)
                except ValueError:
                    pass
            if self._current_index >= len(self._queue):
                self._current_index = max(0, len(self._queue) - 1)
            self._publish_queue_update()

    def clear_queue(self) -> None:
        self._queue.clear()
        self._unshuffled_queue = None
        self._current_index = 0
        self._publish_queue_update()

    def play_pause(self) -> None:
        if self._mpv:
            try:
                self._mpv.pause = not self._mpv.pause
            except Exception:
                pass

    def next_track(self) -> None:
        if not self._queue:
            return
        self._auto_advance = False
        self._current_index = (self._current_index + 1) % len(self._queue)
        self._play_current()

    def prev_track(self) -> None:
        if not self._queue:
            return
        self._auto_advance = False
        self._current_index = (self._current_index - 1) % len(self._queue)
        self._play_current()

    def set_volume(self, volume: int) -> None:
        if self._mpv:
            try:
                self._mpv.volume = max(0, min(100, volume))
            except Exception:
                pass
        self._publish_state()

    def seek(self, position_s: float) -> None:
        if self._mpv:
            try:
                self._mpv.time_pos = position_s
            except Exception:
                pass

    def set_stream_url(self, track_id: str, url: str) -> None:
        self._stream_urls[track_id] = url

    def play(self) -> None:
        if not self._queue:
            return
        if not self._mpv:
            mpv_cls = _mpv_safe()
            if mpv_cls is None:
                self._publish_error("mpv is not installed. Install it with: apt install mpv libmpv-dev")
                return
            self._mpv = mpv_cls(ytdl=True, video=False)
            try:
                self._loop = asyncio.get_running_loop()
                self._mpv.observe_property("eof-reached", self._on_eof_reached)
            except Exception:
                self._loop = None
        self._play_current()

    def stop(self) -> None:
        self._auto_advance = False
        if self._mpv:
            try:
                self._mpv.command("stop")
            except Exception:
                pass
        if self._progress_task and not self._progress_task.done():
            self._progress_task.cancel()
            self._progress_task = None
        self._publish_event(PlaybackStateEvent(
            is_playing=False,
            position_s=0.0,
            duration_s=0.0,
            volume=self._mpv.volume if self._mpv else 100,
            shuffle=self._shuffle,
            repeat=self._repeat,
        ))

    def toggle_shuffle(self) -> None:
        self._shuffle = not self._shuffle
        if self._shuffle:
            self._unshuffled_queue = list(self._queue)
            if 0 <= self._current_index < len(self._queue):
                current = self._queue.pop(self._current_index)
                self._queue.insert(0, current)
            random.shuffle(self._queue[1:])
            self._current_index = 0
        else:
            if self._unshuffled_queue is not None:
                current_track_id = self.current_track.id if self.current_track else None
                self._queue = list(self._unshuffled_queue)
                self._unshuffled_queue = None
                if current_track_id:
                    for i, item in enumerate(self._queue):
                        if item.track.id == current_track_id:
                            self._current_index = i
                            break
                    else:
                        self._current_index = 0
        self._publish_queue_update()
        self._publish_state()

    def toggle_repeat(self) -> None:
        idx = REPEAT_MODES.index(self._repeat)
        self._repeat = REPEAT_MODES[(idx + 1) % 3]
        self._publish_state()

    def _play_current(self) -> None:
        track = self.current_track
        if not track or not self._mpv:
            return
        url = self._stream_urls.get(track.id)
        if not url:
            self._publish_event(NeedStreamUrlEvent(track_id=track.id))
            return
        try:
            self._mpv.play(url)
            self._auto_advance = True
            self._start_progress_reporting()
            self._publish_event(TrackChangedEvent(track=track))
        except Exception as e:
            self._publish_error(f"Playback failed: {e}")

    def _on_eof_reached(self, name: str, value: bool) -> None:
        if value and self._auto_advance:
            self._auto_advance = False
            if self._loop:
                self._loop.call_soon_threadsafe(self._handle_track_end)

    def _handle_track_end(self) -> None:
        if not self._queue:
            return
        if self._repeat == "one":
            track = self.current_track
            if not track or not self._mpv:
                return
            url = self._stream_urls.get(track.id)
            if not url:
                self._publish_event(NeedStreamUrlEvent(track_id=track.id))
                return
            try:
                self._mpv.play(url)
                self._auto_advance = True
            except Exception as e:
                self._publish_error(f"Replay failed: {e}")
        elif self._repeat == "all":
            self._current_index = (self._current_index + 1) % len(self._queue)
            self._play_current()
        else:
            if self._current_index + 1 < len(self._queue):
                self._current_index += 1
                self._play_current()
            else:
                self.stop()

    def _start_progress_reporting(self) -> None:
        if self._progress_task and not self._progress_task.done():
            self._progress_task.cancel()
        try:
            loop = asyncio.get_running_loop()
            self._progress_task = loop.create_task(self._progress_loop())
        except RuntimeError:
            pass

    async def _progress_loop(self) -> None:
        while self._mpv:
            try:
                state = self.get_state()
                if state.track:
                    await self._bus.publish(PlaybackStateEvent(
                        is_playing=state.is_playing,
                        position_s=state.position_s,
                        duration_s=state.duration_s,
                        volume=state.volume,
                        shuffle=state.shuffle,
                        repeat=state.repeat,
                    ))
            except Exception:
                pass
            await asyncio.sleep(0.5)

    def _publish_state(self) -> None:
        state = self.get_state()
        self._publish_event(PlaybackStateEvent(
            is_playing=state.is_playing,
            position_s=state.position_s,
            duration_s=state.duration_s,
            volume=state.volume,
            shuffle=state.shuffle,
            repeat=state.repeat,
        ))

    def _publish_queue_update(self) -> None:
        self._publish_event(QueueUpdatedEvent(
            queue=[item.track for item in self._queue],
            current_index=self._current_index,
        ))

    def _publish_error(self, msg: str) -> None:
        self._publish_event(ErrorEvent(source="player", message=msg))

    def _publish_event(self, event) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._bus.publish(event))
        except RuntimeError:
            pass

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
