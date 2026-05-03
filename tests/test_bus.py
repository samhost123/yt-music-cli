import pytest
from yt_music_cli.bus import MessageBus
from yt_music_cli.events import SearchRequestEvent, SearchResultsEvent, ErrorEvent
from yt_music_cli.models import Track


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = MessageBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(SearchRequestEvent, handler)
    evt = SearchRequestEvent(query="test")
    await bus.publish(evt)

    assert len(received) == 1
    assert received[0].query == "test"


@pytest.mark.asyncio
async def test_multiple_subscribers():
    bus = MessageBus()
    results = []

    async def handler_a(event):
        results.append("a")

    async def handler_b(event):
        results.append("b")

    bus.subscribe(SearchResultsEvent, handler_a)
    bus.subscribe(SearchResultsEvent, handler_b)
    await bus.publish(SearchResultsEvent(results=[]))

    assert sorted(results) == ["a", "b"]


@pytest.mark.asyncio
async def test_handler_order_is_preserved():
    bus = MessageBus()
    order = []

    async def h1(event):
        order.append(1)

    async def h2(event):
        order.append(2)

    bus.subscribe(ErrorEvent, h1)
    bus.subscribe(ErrorEvent, h2)
    await bus.publish(ErrorEvent(source="test", message="msg"))

    assert order == [1, 2]


@pytest.mark.asyncio
async def test_unrelated_event_not_received():
    bus = MessageBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(SearchRequestEvent, handler)
    await bus.publish(ErrorEvent(source="x", message="y"))

    assert len(received) == 0


@pytest.mark.asyncio
async def test_handler_exception_does_not_block_others():
    bus = MessageBus()
    results = []

    async def failing_handler(event):
        raise RuntimeError("boom")

    async def ok_handler(event):
        results.append("ok")

    bus.subscribe(ErrorEvent, failing_handler)
    bus.subscribe(ErrorEvent, ok_handler)
    await bus.publish(ErrorEvent(source="x", message="y"))

    assert results == ["ok"]


@pytest.mark.asyncio
async def test_publish_non_subscribed_event_does_nothing():
    bus = MessageBus()
    # Should not raise — just no-op
    await bus.publish(SearchRequestEvent(query="x"))


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = MessageBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(SearchRequestEvent, handler)
    bus.unsubscribe(SearchRequestEvent, handler)
    await bus.publish(SearchRequestEvent(query="x"))

    assert len(received) == 0
