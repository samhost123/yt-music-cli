import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from yt_music_cli.bus import MessageBus
from yt_music_cli.api import APIClient
from yt_music_cli.events import (
    SearchRequestEvent,
    SearchResultsEvent,
    LibraryUpdateEvent,
    AuthReadyEvent,
    ErrorEvent,
    TrackChangedEvent,
)
from yt_music_cli.models import Track


@pytest.fixture
def mock_ytmusic():
    ytm = MagicMock()
    ytm.search.return_value = [
        {
            "videoId": "vid1",
            "title": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "duration_seconds": 180,
            "thumbnails": [{"url": "http://t.jpg"}],
            "resultType": "song",
        },
        {
            "videoId": "vid2",
            "title": "Other Song",
            "artists": [{"name": "Other Artist"}],
            "duration_seconds": 240,
            "thumbnails": [{"url": "http://o.jpg"}],
            "resultType": "song",
        },
    ]
    ytm.get_library_songs.return_value = []
    ytm.get_library_albums.return_value = []
    ytm.get_library_playlists.return_value = []
    return ytm


@pytest.fixture
def api_client(mock_ytmusic):
    bus = MessageBus()
    client = APIClient(bus)
    client._ytmusic = mock_ytmusic
    return bus, client


@pytest.mark.asyncio
async def test_search_request_publishes_results(api_client):
    bus, client = api_client
    results = []

    async def capture(event):
        results.append(event)

    bus.subscribe(SearchResultsEvent, capture)

    await bus.publish(SearchRequestEvent(query="test"))
    await asyncio.sleep(0)

    assert len(results) == 1
    assert len(results[0].results) == 2
    assert results[0].results[0].title == "Test Song"
    assert results[0].results[0].artists == ["Test Artist"]


@pytest.mark.asyncio
async def test_search_converts_empty_artists(api_client):
    bus, client = api_client
    client._ytmusic.search.return_value = [{
        "videoId": "v1",
        "title": "Song",
        "duration_seconds": 100,
        "thumbnails": [],
        "resultType": "song",
    }]
    results = []

    async def capture(event):
        results.append(event)

    bus.subscribe(SearchResultsEvent, capture)

    await bus.publish(SearchRequestEvent(query="x"))
    await asyncio.sleep(0)

    assert results[0].results[0].artists == ["Unknown Artist"]
    assert results[0].results[0].duration_ms == 100000


@pytest.mark.asyncio
async def test_search_error_publishes_error_event(api_client):
    bus, client = api_client
    client._ytmusic.search.side_effect = Exception("Network error")
    errors = []

    async def capture(event):
        errors.append(event)

    bus.subscribe(ErrorEvent, capture)

    await bus.publish(SearchRequestEvent(query="x"))
    await asyncio.sleep(0)

    assert len(errors) == 1
    assert errors[0].source == "api"
    assert "Network error" in errors[0].message


@pytest.mark.asyncio
async def test_library_fetch_on_auth_ready(api_client):
    bus, client = api_client
    lib_events = []

    async def capture(event):
        lib_events.append(event)

    bus.subscribe(LibraryUpdateEvent, capture)

    await bus.publish(AuthReadyEvent())
    await asyncio.sleep(0)

    assert len(lib_events) == 3  # songs, albums, playlists


@pytest.mark.asyncio
async def test_get_track_url(api_client):
    bus, client = api_client
    client._ytmusic.get_song.return_value = {
        "videoDetails": {"videoId": "vid1", "title": "Song", "author": "Artist"},
        "streamingData": {
            "adaptiveFormats": [
                {"mimeType": "audio/mp4", "url": "http://stream.url"},
            ]
        },
    }
    url = await client.get_stream_url("vid1")
    assert url is not None


@pytest.mark.asyncio
async def test_get_track_url_error(api_client):
    bus, client = api_client
    client._ytmusic.get_song.side_effect = Exception("fail")
    errors = []

    async def capture(event):
        errors.append(event)

    bus.subscribe(ErrorEvent, capture)

    url = await client.get_stream_url("vid1")
    await asyncio.sleep(0)

    assert url is None
    assert len(errors) == 1
