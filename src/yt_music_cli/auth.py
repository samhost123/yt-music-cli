import logging
import sys
from pathlib import Path

from ytmusicapi import YTMusic
from ytmusicapi.setup import setup as ytm_setup

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import AuthReadyEvent, AuthErrorEvent

logger = logging.getLogger(__name__)


class AuthModule:
    def __init__(self, bus: MessageBus, auth_path: Path) -> None:
        self._bus = bus
        self._auth_path = auth_path
        self._ytmusic: YTMusic | None = None

    async def initialize(self) -> None:
        if self._auth_path.exists():
            try:
                self._ytmusic = YTMusic(str(self._auth_path))
                await self._bus.publish(AuthReadyEvent())
                logger.info("Authenticated from %s", self._auth_path)
            except Exception as e:
                logger.warning("Failed to load credentials: %s", e)
                await self._bus.publish(
                    AuthErrorEvent(error_msg=f"Failed to load credentials: {e}")
                )
        else:
            await self._bus.publish(
                AuthErrorEvent(
                    error_msg="Not authenticated. Run 'yt-music-cli --setup' first."
                )
            )

    def run_setup(self) -> bool:
        """Run interactive browser header setup. Returns True on success."""
        try:
            self._auth_path.parent.mkdir(parents=True, exist_ok=True)
            ytm_setup(filepath=str(self._auth_path))
            self._ytmusic = YTMusic(str(self._auth_path))
            logger.info("Setup completed, credentials saved to %s", self._auth_path)
            return True
        except Exception as e:
            logger.exception("Setup failed")
            print(f"Setup failed: {e}", file=sys.stderr)
            return False

    def is_authenticated(self) -> bool:
        return self._ytmusic is not None

    @property
    def client(self) -> YTMusic | None:
        return self._ytmusic
