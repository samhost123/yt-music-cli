from yt_music_cli.events import (
    AuthReadyEvent,
    AuthErrorEvent,
    SearchRequestEvent,
    SearchResultsEvent,
    PlayRequestEvent,
    TrackChangedEvent,
    PlaybackStateEvent,
    QueueUpdatedEvent,
    LibraryUpdateEvent,
    ErrorEvent,
)
from yt_music_cli.models import Track


def test_auth_ready_event():
    evt = AuthReadyEvent()
    assert evt.type == "auth_ready"


def test_auth_error_event():
    evt = AuthErrorEvent(error_msg="Invalid credentials")
    assert evt.type == "auth_error"
    assert evt.error_msg == "Invalid credentials"


def test_search_request_event():
    evt = SearchRequestEvent(query="queen", filter="songs")
    assert evt.type == "search_request"
    assert evt.query == "queen"
    assert evt.filter == "songs"


def test_search_results_event():
    tracks = [
        Track(id="1", title="Song A", artists=["Artist A"]),
        Track(id="2", title="Song B", artists=["Artist B"]),
    ]
    evt = SearchResultsEvent(results=tracks, query="test")
    assert evt.type == "search_results"
    assert len(evt.results) == 2
    assert evt.query == "test"


def test_play_request_event():
    track = Track(id="abc123", title="Song", artists=["Artist"])
    evt = PlayRequestEvent(track=track, context="search")
    assert evt.type == "play_request"
    assert evt.track.id == "abc123"
    assert evt.track.title == "Song"
    assert evt.context == "search"


def test_track_changed_event():
    track = Track(id="1", title="Song A", artists=["Artist A"])
    evt = TrackChangedEvent(track=track)
    assert evt.type == "track_changed"
    assert evt.track.id == "1"


def test_playback_state_event():
    evt = PlaybackStateEvent(is_playing=True, position_s=42.5, duration_s=210.0,
                              volume=80, shuffle=False, repeat="off")
    assert evt.type == "playback_state"
    assert evt.is_playing is True
    assert evt.position_s == 42.5


def test_queue_updated_event():
    tracks = [Track(id="1", title="S", artists=["A"])]
    evt = QueueUpdatedEvent(queue=tracks)
    assert evt.type == "queue_updated"
    assert len(evt.queue) == 1


def test_library_update_event():
    evt = LibraryUpdateEvent(category="tracks", items=[])
    assert evt.type == "library_update"
    assert evt.category == "tracks"


def test_error_event():
    evt = ErrorEvent(source="api", message="Network timeout")
    assert evt.type == "error"
    assert evt.source == "api"
    assert evt.message == "Network timeout"
