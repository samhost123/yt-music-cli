import logging
from collections import defaultdict
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class MessageBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Any) -> None:
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            return

        for handler in list(handlers):
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Handler %s raised exception for event %s",
                    handler.__name__,
                    event_type.__name__,
                )
