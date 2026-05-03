import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Awaitable

from yt_music_cli.events import ErrorEvent

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class MessageBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
        if not handlers:
            self._handlers.pop(event_type, None)

    async def publish(self, event: Any) -> None:
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            return

        for handler in list(handlers):
            try:
                await handler(event)
            except Exception as e:
                logger.exception(
                    "Handler %s raised for event %s",
                    handler.__name__,
                    event_type.__name__,
                )
                # Publish error to any error handlers (skip if we're already handling an error)
                if not isinstance(event, ErrorEvent):
                    error_handlers = self._handlers.get(ErrorEvent, [])
                    for eh in error_handlers:
                        await eh(ErrorEvent(
                            source=event_type.__name__,
                            message=str(e)[:120],
                        ))
