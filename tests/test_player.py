import pytest
import asyncio
from unittest.mock import MagicMock, patch, PropertyMock

from yt_music_cli.bus import MessageBus
from yt_music_cli.player import PlayerModule
from yt_music_cli.events import (
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
    ErrorEvent,
)
from yt_music_cli.models import Track, QueueItem


@pytest.fixture
def bus():
    return MessageBus()


@pytest.fixture
def mock_mpv():
    with patch("mpv.MPV", create=True) as mock:
        mpv_instance = MagicMock()
        mpv_instance.pause = False
        mpv_instance.volume = 100
        type(mpv_instance).time_pos = PropertyMock(return_value=10.0)
        type(mpv_instance).duration = PropertyMock(return_value=210.0)
        mock.return_value = mpv_instance
        yield mpv_instance


@pytest.fixture
def player(bus, mock_mpv, sample_track):
    player_module = PlayerModule(bus)
    player_module._stream_urls[sample_track.id] = "https://example.com/test.mp3"
    for i in range(1, 6):
        player_module._stream_urls[f"track{i}"] = f"https://example.com/song{i}.mp3"
    return bus, player_module


@pytest.mark.asyncio
async def test_play_request_adds_to_queue_and_plays(player, sample_track):
    bus, player_module = player
    track_events = []

    async def capture(event):
        track_events.append(event)

    bus.subscribe(TrackChangedEvent, capture)

    await bus.publish(PlayRequestEvent(track=sample_track, context="test"))
    await asyncio.sleep(0)

    assert len(track_events) == 1
    assert track_events[0].track.id == sample_track.id


@pytest.mark.asyncio
async def test_play_request_unknown_id_publishes_error(player, mock_mpv):
    bus, player_module = player
    errors = []

    async def capture(event):
        errors.append(event)

    bus.subscribe(ErrorEvent, capture)

    unknown_track = Track(id="nonexistent", title="Unknown", artists=["Unknown"])
    await bus.publish(PlayRequestEvent(track=unknown_track, context="test"))
    await asyncio.sleep(0)

    assert len(errors) == 1
    assert errors[0].source == "player"
    assert "nonexistent" in errors[0].message


@pytest.mark.asyncio
async def test_play_pause_toggles(player, mock_mpv):
    bus, player_module = player
    type(mock_mpv).pause = PropertyMock(return_value=False)

    player_module._mpv = mock_mpv
    player_module.play_pause()
    mock_mpv._set_property.assert_called_with("pause", True)


@pytest.mark.asyncio
async def test_next_skips_to_next_in_queue(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module._current_index = 0
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module.next_track()

    assert player_module._current_index == 1


@pytest.mark.asyncio
async def test_prev_goes_back(player, sample_tracks):
    bus, player_module = player
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module._current_index = 2
    player_module.prev_track()

    assert player_module._current_index == 1


@pytest.mark.asyncio
async def test_set_volume(player, mock_mpv):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module.set_volume(50)
    mock_mpv._set_property.assert_called_with("volume", 50)


@pytest.mark.asyncio
async def test_seek(player, mock_mpv):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module.seek(30.0)
    mock_mpv._set_property.assert_called_with("time-pos", 30.0)


@pytest.mark.asyncio
async def test_queue_updated_event_on_add(player, sample_track):
    bus, player_module = player
    queue_events = []

    async def capture(event):
        queue_events.append(event)

    bus.subscribe(QueueUpdatedEvent, capture)

    player_module.add_to_queue(sample_track)
    await asyncio.sleep(0)

    assert len(queue_events) == 1
    assert queue_events[0].queue[0].id == sample_track.id


@pytest.mark.asyncio
async def test_remove_from_queue(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module.remove_from_queue(0)
    assert len(player_module.queue) == 4


@pytest.mark.asyncio
async def test_clear_queue(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module.clear_queue()
    assert len(player_module.queue) == 0
