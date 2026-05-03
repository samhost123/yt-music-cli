import logging
from pathlib import Path

from ytmusicapi import YTMusic, setup_oauth, OAuthCredentials

from yt_music_cli.bus import MessageBus
from yt_music_cli.events import AuthReadyEvent, AuthErrorEvent

logger = logging.getLogger(__name__)


class AuthModule:
    def __init__(self, bus: MessageBus, oauth_path: Path | None = None) -> None:
        self._bus = bus
        self._oauth_path = oauth_path
        self._ytmusic: YTMusic | None = None

    async def initialize(self) -> None:
        if self._oauth_path and self._oauth_path.exists():
            try:
                self._ytmusic = YTMusic(
                    auth=str(self._oauth_path),
                    oauth_credentials=OAuthCredentials("", ""),
                )
                await self._bus.publish(AuthReadyEvent())
                logger.info("Authenticated from saved credentials")
            except Exception as e:
                logger.warning("Failed to load saved credentials: %s", e)
                await self._bus.publish(
                    AuthErrorEvent(error_msg="Failed to load saved credentials")
                )
        else:
            await self._bus.publish(
                AuthErrorEvent(error_msg="No saved credentials. Run login to authenticate.")
            )

    async def start_oauth(self) -> None:
        try:
            if self._oauth_path:
                self._oauth_path.parent.mkdir(parents=True, exist_ok=True)
                setup_oauth(
                    client_id="",
                    client_secret="",
                    filepath=str(self._oauth_path),
                )
                self._ytmusic = YTMusic(
                    auth=str(self._oauth_path),
                    oauth_credentials=OAuthCredentials("", ""),
                )
            else:
                self._ytmusic = YTMusic()

            logger.info("OAuth flow completed")
            await self._bus.publish(AuthReadyEvent())
        except Exception as e:
            logger.exception("OAuth flow failed")
            await self._bus.publish(AuthErrorEvent(error_msg=str(e)))

    def is_authenticated(self) -> bool:
        return self._ytmusic is not None

    @property
    def client(self) -> YTMusic | None:
        return self._ytmusic
