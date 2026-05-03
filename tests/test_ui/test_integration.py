import pytest
import asyncio
from yt_music_cli.bus import MessageBus
from yt_music_cli.events import (
    AuthReadyEvent,
    SearchRequestEvent,
    SearchResultsEvent,
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    LibraryUpdateEvent,
    ErrorEvent,
)
from yt_music_cli.models import Track


@pytest.mark.asyncio
async def test_full_event_flow_search_to_play():
    bus = MessageBus()
    search_results = []
    play_requests = []
    track_changes = []
    playback_states = []

    async def on_search_results(event):
        search_results.append(event)

    async def on_play_request(event):
        play_requests.append(event)

    async def on_track_changed(event):
        track_changes.append(event)

    async def on_playback_state(event):
        playback_states.append(event)

    bus.subscribe(SearchResultsEvent, on_search_results)
    bus.subscribe(PlayRequestEvent, on_play_request)
    bus.subscribe(TrackChangedEvent, on_track_changed)
    bus.subscribe(PlaybackStateEvent, on_playback_state)

    await bus.publish(SearchRequestEvent(query="queen"))
    track = Track(id="v1", title="Bohemian Rhapsody", artists=["Queen"])
    await bus.publish(SearchResultsEvent(results=[track], query="queen"))

    assert len(search_results) == 1
    assert search_results[0].results[0].title == "Bohemian Rhapsody"

    await bus.publish(PlayRequestEvent(track=track, context="search"))
    assert len(play_requests) == 1

    await bus.publish(TrackChangedEvent(track=track))
    assert len(track_changes) == 1

    await bus.publish(PlaybackStateEvent(is_playing=True, position_s=10.0, duration_s=354.0))
    assert len(playback_states) == 1
    assert playback_states[0].is_playing is True


@pytest.mark.asyncio
async def test_error_event_flow():
    bus = MessageBus()
    errors = []

    async def capture(event):
        errors.append(event)

    bus.subscribe(ErrorEvent, capture)

    await bus.publish(ErrorEvent(source="api", message="Network timeout"))
    assert len(errors) == 1
    assert errors[0].source == "api"

    await bus.publish(ErrorEvent(source="player", message="mpv crashed"))
    assert len(errors) == 2
    assert errors[1].source == "player"


@pytest.mark.asyncio
async def test_auth_to_library_flow():
    bus = MessageBus()
    lib_events = []

    async def capture(event):
        lib_events.append(event)

    bus.subscribe(LibraryUpdateEvent, capture)

    async def on_auth(e):
        await bus.publish(LibraryUpdateEvent(category="tracks", items=[]))

    bus.subscribe(AuthReadyEvent, on_auth)

    await bus.publish(AuthReadyEvent())
    await asyncio.sleep(0)

    assert len(lib_events) >= 1
