import pytest
from yt_music_cli.models import Track, Album, Artist, Playlist, PlaybackState, QueueItem


def test_track_creation():
    track = Track(
        id="abc123",
        title="Bohemian Rhapsody",
        artists=["Queen"],
        album="A Night at the Opera",
        duration_ms=354000,
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert track.id == "abc123"
    assert track.title == "Bohemian Rhapsody"
    assert track.duration_ms == 354000
    assert track.artist_string == "Queen"


def test_track_artist_string_multiple():
    track = Track(id="1", title="T", artists=["Alice", "Bob"], album="A", duration_ms=1000)
    assert track.artist_string == "Alice, Bob"


def test_track_duration_str():
    assert Track(id="1", title="T", artists=["A"], duration_ms=210000).duration_str == "3:30"
    assert Track(id="1", title="T", artists=["A"], duration_ms=3600000).duration_str == "1:00:00"
    assert Track(id="1", title="T", artists=["A"], duration_ms=7500000).duration_str == "2:05:00"
    assert Track(id="1", title="T", artists=["A"], duration_ms=0).duration_str == "0:00"


def test_album_creation():
    album = Album(
        id="al1",
        title="A Night at the Opera",
        artists=["Queen"],
        year=1975,
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert album.id == "al1"
    assert album.year == 1975


def test_playlist_track_count():
    playlist = Playlist(
        id="pl1",
        title="My Mix",
        track_count=42,
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert playlist.track_count == 42


def test_playback_state_defaults():
    state = PlaybackState()
    assert state.track is None
    assert state.is_playing is False
    assert state.position_s == 0.0
    assert state.duration_s == 0.0
    assert state.volume == 100
    assert state.shuffle is False
    assert state.repeat == "off"


def test_playback_state_with_track():
    track = Track(id="t1", title="Song", artists=["Artist"])
    state = PlaybackState(track=track, is_playing=True, position_s=45.0, duration_s=200.0, volume=80)
    assert state.track == track
    assert state.is_playing is True
    assert state.position_s == 45.0
    assert state.duration_s == 200.0
    assert state.volume == 80


def test_queue_item_creation():
    track = Track(id="t1", title="Song", artists=["Artist"])
    item = QueueItem(track=track, source="search")
    assert item.track == track
    assert item.source == "search"


def test_queue_item_default_source():
    track = Track(id="t1", title="Song", artists=["Artist"])
    item = QueueItem(track=track)
    assert item.source == ""
