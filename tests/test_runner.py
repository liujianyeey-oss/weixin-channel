import asyncio
from pathlib import Path

import pytest

from weixin_channel.channel import WeixinChannel, WeixinConfig
from weixin_channel.models import MessageEvent
from weixin_channel.runner import WeixinChannelRunner


async def echo(message):
    yield MessageEvent.text(message.text)


def test_runner_preserves_channel_instance() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    runner = WeixinChannelRunner(channel=channel)
    assert runner.channel_id == "fixed"


def test_runner_expands_default_media_dir() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    runner = WeixinChannelRunner(channel=channel)

    assert channel.media_dir == "~/.weixin-channel/media"
    assert runner._media_backend.root_path == Path(
        channel.media_dir
    ).expanduser()


def test_runner_rejects_multiple_channel_arguments() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    with pytest.raises(ValueError, match="provide either channel="):
        WeixinChannelRunner(channel=channel, config=config, processor=echo)


async def test_runner_run_in_session_requires_key() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    runner = WeixinChannelRunner(config=config, processor=echo)

    async def operation() -> None:
        return None

    with pytest.raises(ValueError, match="session_key must not be empty"):
        await runner.run_in_session(" ", operation)


async def test_runner_processes_queued_message() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    runner = WeixinChannelRunner(channel=channel, workers_per_channel=1)
    original_start, original_stop = channel.start, channel.stop
    try:
        async def offline_start() -> None:
            channel._running = True

        async def offline_stop() -> None:
            channel._running = False

        channel.start = offline_start  # type: ignore[method-assign]
        channel.stop = offline_stop  # type: ignore[method-assign]
        await runner.start()
        runner.enqueue(
            {
                "_account_id": "a",
                "from_user_id": "user",
                "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
            }
        )
        await asyncio.sleep(0.1)
        assert runner._queue.qsize() == 0
        assert channel.parse_inbound(
            {
                "_account_id": "a",
                "from_user_id": "user",
                "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
            }
        ).text == "hello"
    finally:
        channel.start, channel.stop = original_start, original_stop
        await runner.stop()


async def test_runner_calls_processor_for_queued_message() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    runner = WeixinChannelRunner(channel=channel, workers_per_channel=1)
    recorded: list[object] = []
    original_handle = channel.handle_inbound
    original_start, original_stop = channel.start, channel.stop

    async def handle(message):
        recorded.append(message)

    channel.handle_inbound = handle  # type: ignore[method-assign]
    try:
        async def offline_start() -> None:
            channel._running = True

        async def offline_stop() -> None:
            channel._running = False

        channel.start = offline_start  # type: ignore[method-assign]
        channel.stop = offline_stop  # type: ignore[method-assign]
        await runner.start()
        runner.enqueue(
            {
                "_account_id": "a",
                "from_user_id": "user",
                "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
            }
        )
        await asyncio.sleep(0.1)
        assert len(recorded) == 1
        assert recorded[0].text == "hello"
    finally:
        channel.handle_inbound = original_handle  # type: ignore[method-assign]
        channel.start, channel.stop = original_start, original_stop
        await runner.stop()


async def test_runner_calls_pre_lock_handler() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    seen: list[str] = []
    runner = WeixinChannelRunner(channel=channel, pre_lock_handler=lambda message: seen.append(message.text))
    original_handle = channel.handle_inbound
    original_start, original_stop = channel.start, channel.stop

    async def handle(message):
        seen.append("locked:" + message.text)

    channel.handle_inbound = handle  # type: ignore[method-assign]
    try:
        async def offline_start() -> None:
            channel._running = True

        async def offline_stop() -> None:
            channel._running = False

        channel.start = offline_start  # type: ignore[method-assign]
        channel.stop = offline_stop  # type: ignore[method-assign]
        await runner.start()
        runner.enqueue(
            {
                "_account_id": "a",
                "from_user_id": "user",
                "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
            }
        )
        await asyncio.sleep(0.1)
        assert seen == ["hello", "locked:hello"]
    finally:
        channel.handle_inbound = original_handle  # type: ignore[method-assign]
        channel.start, channel.stop = original_start, original_stop
        await runner.stop()


async def test_runner_start_failure_resets_running_state() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    runner = WeixinChannelRunner(channel=channel)

    async def failing_start() -> None:
        raise RuntimeError("start failed")

    channel.start = failing_start  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="start failed"):
        await runner.start()
    assert runner.running is False


async def test_runner_does_not_merge_group_context_messages() -> None:
    config = WeixinConfig.from_dict(
        {"accounts": [{"account_id": "a", "token": "secret"}]}
    )
    channel = WeixinChannel(echo, config=config, channel_id="fixed")
    runner = WeixinChannelRunner(channel=channel, workers_per_channel=1)
    seen_batches: list[list[object]] = []

    original_should_batch = channel.should_batch_inbound
    original_merge = channel.merge_inbound
    original_start, original_stop = channel.start, channel.stop

    def should_batch(message) -> bool:
        seen_batches.append([message])
        return False

    def merge(messages):
        seen_batches[-1] = messages
        return original_merge(messages)

    channel.should_batch_inbound = should_batch  # type: ignore[method-assign]
    channel.merge_inbound = merge  # type: ignore[method-assign]
    try:
        async def offline_start() -> None:
            channel._running = True

        async def offline_stop() -> None:
            channel._running = False

        channel.start = offline_start  # type: ignore[method-assign]
        channel.stop = offline_stop  # type: ignore[method-assign]
        await runner.start()
        payload = {
            "_account_id": "a",
            "from_user_id": "user",
            "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
        }
        runner.enqueue(payload)
        runner.enqueue(dict(payload))
        await asyncio.sleep(0.1)
        assert len(seen_batches) == 2
        assert all(isinstance(batch, list) and len(batch) == 1 for batch in seen_batches)
    finally:
        channel.should_batch_inbound = original_should_batch  # type: ignore[method-assign]
        channel.merge_inbound = original_merge  # type: ignore[method-assign]
        channel.start, channel.stop = original_start, original_stop
        await runner.stop()
