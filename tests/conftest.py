import pytest
from yt_music_cli.models import Track, PlaybackState


@pytest.fixture
def sample_track():
    return Track(
        id="track1",
        title="Test Song",
        artists=["Test Artist"],
        album="Test Album",
        duration_ms=210000,
    )


@pytest.fixture
def sample_tracks():
    return [
        Track(id=f"track{i}", title=f"Song {i}", artists=[f"Artist {i}"], duration_ms=180000 + i * 1000)
        for i in range(1, 6)
    ]


@pytest.fixture
def playback_state(sample_track):
    return PlaybackState(track=sample_track, is_playing=True, position_s=30.0, duration_s=210.0)
