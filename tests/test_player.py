import pytest
import asyncio
from unittest.mock import MagicMock, patch, PropertyMock

from yt_music_cli.bus import MessageBus
from yt_music_cli.player import PlayerModule, REPEAT_MODES
from yt_music_cli.events import (
    QueueUpdatedEvent,
    NeedStreamUrlEvent,
    ErrorEvent,
    PlaybackStateEvent,
    TrackChangedEvent,
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
        mpv_instance.time_pos = 10.0
        mpv_instance.duration = 210.0
        mock.return_value = mpv_instance
        yield mpv_instance


@pytest.fixture
def player(bus, mock_mpv, sample_track):
    player_module = PlayerModule(bus)
    return bus, player_module


# --- Queue management ---


@pytest.mark.asyncio
async def test_add_to_queue_and_play(player, sample_track):
    bus, player_module = player
    player_module.add_to_queue(sample_track, source="test")
    assert len(player_module.queue) == 1
    assert player_module.queue[0].track.id == sample_track.id


@pytest.mark.asyncio
async def test_play_pause_toggles(player, mock_mpv):
    bus, player_module = player
    mock_mpv.pause = False

    player_module._mpv = mock_mpv
    player_module.play_pause()
    assert mock_mpv.pause is True


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
    assert mock_mpv.volume == 50


@pytest.mark.asyncio
async def test_seek(player, mock_mpv):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module.seek(30.0)
    assert mock_mpv.time_pos == 30.0


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


# --- Shuffle ---


@pytest.mark.asyncio
async def test_toggle_shuffle_preserves_current_track(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module._current_index = 2
    current_track = player_module.current_track

    player_module.toggle_shuffle()
    assert player_module.shuffle is True
    assert player_module.current_track.id == current_track.id
    assert player_module._current_index == 0
    assert len(player_module.queue) == len(sample_tracks)


@pytest.mark.asyncio
async def test_toggle_shuffle_off_restores_order(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    original_ids = [t.id for t in sample_tracks]
    player_module.toggle_shuffle()
    player_module.toggle_shuffle()

    restored_ids = [item.track.id for item in player_module.queue]
    assert restored_ids == original_ids


@pytest.mark.asyncio
async def test_add_to_shuffled_queue_inserts_randomly(player, sample_tracks):
    bus, player_module = player
    for t in sample_tracks:
        player_module.add_to_queue(t)

    player_module._current_index = 0
    player_module.toggle_shuffle()

    new_track = Track(id="new", title="New Song", artists=["Artist"])
    player_module.add_to_queue(new_track)

    assert len(player_module.queue) == 6
    assert player_module._unshuffled_queue is not None
    assert len(player_module._unshuffled_queue) == 6


@pytest.mark.asyncio
async def test_shuffle_off_empty_queue(player):
    bus, player_module = player
    player_module.toggle_shuffle()
    assert player_module.shuffle is True
    assert len(player_module.queue) == 0


# --- Repeat ---


@pytest.mark.asyncio
async def test_toggle_repeat_cycles_modes(player):
    bus, player_module = player
    assert player_module.repeat == "off"
    player_module.toggle_repeat()
    assert player_module.repeat == "one"
    player_module.toggle_repeat()
    assert player_module.repeat == "all"
    player_module.toggle_repeat()
    assert player_module.repeat == "off"


# --- Stop ---


@pytest.mark.asyncio
async def test_stop_publishes_state_update(player, mock_mpv):
    bus, player_module = player
    player_module._mpv = mock_mpv

    events = []

    async def capture(event):
        events.append(event)

    bus.subscribe(PlaybackStateEvent, capture)

    player_module.stop()
    await asyncio.sleep(0)

    assert mock_mpv.command.called
    assert len(events) >= 1
    event = events[-1]
    assert event.is_playing is False
    assert event.position_s == 0.0


# --- NeedStreamUrlEvent ---


@pytest.mark.asyncio
async def test_play_current_without_url_publishes_need_stream(player, mock_mpv, sample_track):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module._queue = [QueueItem(track=sample_track)]
    player_module._current_index = 0

    events = []

    async def capture(event):
        events.append(event)

    bus.subscribe(NeedStreamUrlEvent, capture)

    player_module._play_current()
    await asyncio.sleep(0)

    assert len(events) == 1
    assert events[0].track_id == sample_track.id


@pytest.mark.asyncio
async def test_play_current_with_url_plays(player, mock_mpv, sample_track):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module._queue = [QueueItem(track=sample_track)]
    player_module._current_index = 0
    player_module.set_stream_url(sample_track.id, "http://example.com/stream")

    events = []

    async def capture(event):
        events.append(event)

    bus.subscribe(TrackChangedEvent, capture)

    player_module._play_current()
    await asyncio.sleep(0)

    mock_mpv.play.assert_called_once_with("http://example.com/stream")
    assert len(events) == 1


# --- Auto-advance ---


@pytest.mark.asyncio
async def test_handle_track_end_repeat_one_replays(player, mock_mpv, sample_track):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module._repeat = "one"
    player_module._queue = [QueueItem(track=sample_track)]
    player_module._current_index = 0
    player_module.set_stream_url(sample_track.id, "http://example.com/stream")

    player_module._handle_track_end()

    mock_mpv.play.assert_called_with("http://example.com/stream")


@pytest.mark.asyncio
async def test_handle_track_end_repeat_all_wraps(player, sample_tracks):
    bus, player_module = player
    player_module._repeat = "all"
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module._current_index = len(sample_tracks) - 1  # last track

    player_module._handle_track_end()

    assert player_module._current_index == 0


@pytest.mark.asyncio
async def test_handle_track_end_repeat_off_advances(player, sample_tracks):
    bus, player_module = player
    player_module._repeat = "off"
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module._current_index = 1

    player_module._handle_track_end()

    assert player_module._current_index == 2


@pytest.mark.asyncio
async def test_handle_track_end_repeat_off_last_stops(player, mock_mpv, sample_track):
    bus, player_module = player
    player_module._mpv = mock_mpv
    player_module._repeat = "off"
    player_module._queue = [QueueItem(track=sample_track)]
    player_module._current_index = 0

    player_module._handle_track_end()

    mock_mpv.command.assert_called_with("stop")


# --- next_track / prev_track disable auto-advance ---


@pytest.mark.asyncio
async def test_next_track_disables_auto_advance(player, sample_tracks):
    bus, player_module = player
    player_module._auto_advance = True
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module._current_index = 0

    player_module.next_track()
    assert player_module._auto_advance is False


@pytest.mark.asyncio
async def test_prev_track_disables_auto_advance(player, sample_tracks):
    bus, player_module = player
    player_module._auto_advance = True
    player_module._queue = [QueueItem(track=t) for t in sample_tracks]
    player_module._current_index = 2

    player_module.prev_track()
    assert player_module._auto_advance is False


# --- Properties ---


@pytest.mark.asyncio
async def test_shuffle_property(player):
    bus, player_module = player
    assert player_module.shuffle is False
    player_module.toggle_shuffle()
    assert player_module.shuffle is True


@pytest.mark.asyncio
async def test_repeat_property(player):
    bus, player_module = player
    assert player_module.repeat == "off"
