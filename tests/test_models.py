import pytest
from yt_music_cli.models import Track, Album, Artist, Playlist


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
