import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from yt_music_cli.bus import MessageBus
from yt_music_cli.auth import AuthModule
from yt_music_cli.events import AuthReadyEvent, AuthErrorEvent


@pytest.fixture
def tmp_oauth_file(tmp_path):
    return tmp_path / "oauth.json"


@pytest.mark.asyncio
async def test_auth_ready_when_token_exists(tmp_oauth_file):
    token_data = {"access_token": "fake", "refresh_token": "fake2", "expires_at": "9999999999"}
    tmp_oauth_file.write_text(json.dumps(token_data))

    with patch("yt_music_cli.auth.YTMusic", return_value=MagicMock()):
        bus = MessageBus()
        received = []
        bus.subscribe(AuthReadyEvent, lambda e: received.append(e) or AsyncMock()())

        module = AuthModule(bus, oauth_path=tmp_oauth_file)
        await module.initialize()

        assert len(received) == 1
        assert isinstance(received[0], AuthReadyEvent)


@pytest.mark.asyncio
async def test_auth_error_when_no_token(tmp_oauth_file):
    bus = MessageBus()
    received = []
    bus.subscribe(AuthErrorEvent, lambda e: received.append(e) or AsyncMock()())

    module = AuthModule(bus, oauth_path=tmp_oauth_file)
    await module.initialize()

    assert len(received) == 1
    assert isinstance(received[0], AuthErrorEvent)
    assert "No saved credentials" in received[0].error_msg


@pytest.mark.asyncio
async def test_start_oauth_flow_saves_token(tmp_oauth_file):
    def _setup_side_effect(client_id="", client_secret="", filepath=None, open_browser=False):
        Path(filepath).write_text("{}")

    with patch("yt_music_cli.auth.setup_oauth", side_effect=_setup_side_effect) as mock_setup:
        with patch("yt_music_cli.auth.YTMusic", return_value=MagicMock()):
            bus = MessageBus()
            received = []
            bus.subscribe(AuthReadyEvent, lambda e: received.append(e) or AsyncMock()())

            module = AuthModule(bus, oauth_path=tmp_oauth_file)
            await module.start_oauth()

            mock_setup.assert_called_once()
            assert mock_setup.call_args.kwargs.get("filepath") == str(tmp_oauth_file)
            assert tmp_oauth_file.exists()
            assert len(received) == 1
            assert isinstance(received[0], AuthReadyEvent)


@pytest.mark.asyncio
async def test_is_authenticated_after_init(tmp_oauth_file):
    token_data = {"access_token": "fake", "refresh_token": "fake2", "expires_at": "9999999999"}
    tmp_oauth_file.write_text(json.dumps(token_data))

    with patch("yt_music_cli.auth.YTMusic", return_value=MagicMock()):
        bus = MessageBus()
        module = AuthModule(bus, oauth_path=tmp_oauth_file)
        await module.initialize()

        assert module.is_authenticated() is True


@pytest.mark.asyncio
async def test_is_authenticated_false_without_init(tmp_oauth_file):
    bus = MessageBus()
    module = AuthModule(bus, oauth_path=tmp_oauth_file)
    assert module.is_authenticated() is False
