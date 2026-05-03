import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from yt_music_cli.bus import MessageBus
from yt_music_cli.auth import AuthModule
from yt_music_cli.events import AuthReadyEvent, AuthErrorEvent


@pytest.fixture
def tmp_auth_file(tmp_path):
    return tmp_path / "headers.json"


@pytest.mark.asyncio
async def test_auth_ready_when_file_exists(tmp_auth_file):
    tmp_auth_file.write_text("{}")

    with patch("yt_music_cli.auth.YTMusic", return_value=MagicMock()):
        bus = MessageBus()
        received = []
        bus.subscribe(AuthReadyEvent, lambda e: received.append(e) or AsyncMock()())

        module = AuthModule(bus, auth_path=tmp_auth_file)
        await module.initialize()

        assert len(received) == 1
        assert isinstance(received[0], AuthReadyEvent)


@pytest.mark.asyncio
async def test_auth_error_when_no_file(tmp_auth_file):
    bus = MessageBus()
    received = []
    bus.subscribe(AuthErrorEvent, lambda e: received.append(e) or AsyncMock()())

    module = AuthModule(bus, auth_path=tmp_auth_file)
    await module.initialize()

    assert len(received) == 1
    assert isinstance(received[0], AuthErrorEvent)
    assert "Not authenticated" in received[0].error_msg


@pytest.mark.asyncio
async def test_run_setup_saves_file(tmp_auth_file):
    def _setup_side_effect(filepath=None, headers_raw=None):
        Path(filepath).write_text("{}")
        return "{}"

    with patch("yt_music_cli.auth.ytm_setup", side_effect=_setup_side_effect) as mock_setup:
        with patch("yt_music_cli.auth.YTMusic", return_value=MagicMock()):
            bus = MessageBus()
            module = AuthModule(bus, auth_path=tmp_auth_file)
            result = module.run_setup()

            assert result is True
            assert mock_setup.call_args.kwargs.get("filepath") == str(tmp_auth_file)
            assert tmp_auth_file.exists()


@pytest.mark.asyncio
async def test_is_authenticated_after_init(tmp_auth_file):
    tmp_auth_file.write_text("{}")

    with patch("yt_music_cli.auth.YTMusic", return_value=MagicMock()):
        bus = MessageBus()
        module = AuthModule(bus, auth_path=tmp_auth_file)
        await module.initialize()

        assert module.is_authenticated() is True


@pytest.mark.asyncio
async def test_is_authenticated_false_without_init(tmp_auth_file):
    bus = MessageBus()
    module = AuthModule(bus, auth_path=tmp_auth_file)
    assert module.is_authenticated() is False
