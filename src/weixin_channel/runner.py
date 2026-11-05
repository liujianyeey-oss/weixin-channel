"""Runner for a standalone WeChat channel."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .channel import WeixinChannel, WeixinConfig
from .core import MessageProcessor
from .media_backend import FileSystemMediaBackend, MediaBackend
from .models import ChannelSubject, ContentPart, InboundMessage

ContextTokenListener = Any
PreLockHandler = Callable[[Any], Awaitable[None]]

logger = logging.getLogger(__name__)


class WeixinChannelRunner:
    """Own queue/worker lifecycle for WeChat channel instances."""

    def __init__(
        self,
        *,
        config: WeixinConfig | None = None,
        processor: MessageProcessor | None = None,
        channel: WeixinChannel | None = None,
        media_backend: MediaBackend | None = None,
        channel_id: str | None = None,
        workers_per_channel: int = 1,
        queue_maxsize: int = 1000,
        context_token_listener: ContextTokenListener | None = None,
        pre_lock_handler: PreLockHandler | None = None,
    ) -> None:
        if channel is not None and (config is not None or processor is not None):
            raise ValueError("provide either channel= or config= plus processor=, not both")
        if channel is None:
            if config is None or processor is None:
                raise ValueError("provide either channel= or config= plus processor=")
            channel = WeixinChannel(
                processor,
                config=config,
                channel_id=channel_id,
            )
        self._channel = channel
        self._media_backend = media_backend or FileSystemMediaBackend(
            Path(channel.media_dir).expanduser()
        )
        self._workers_per_channel = workers_per_channel
        self._queue_maxsize = queue_maxsize
        self._pre_lock_handler = pre_lock_handler
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_maxsize)
        self._workers: list[asyncio.Task[None]] = []
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._channel.set_enqueue_callback(
            lambda payload: self.enqueue(payload)
        )
        if context_token_listener is not None:
            self._channel.set_context_token_listener(context_token_listener)

    def set_pre_lock_handler(self, handler: PreLockHandler | None) -> None:
        """Install or clear a hook called before the inbound session lock."""
        self._pre_lock_handler = handler

    @property
    def channel(self) -> WeixinChannel:
        return self._channel

    @property
    def channel_id(self) -> str:
        return self._channel.channel_id

    @property
    def running(self) -> bool:
        return self._running

    @property
    def channel_type(self) -> str:
        return self._channel.channel_type

    @property
    def tenant_id(self) -> str | None:
        return self._channel.tenant_id

    @property
    def session_status(self) -> dict[str, dict[str, Any]]:
        return self._channel.session_status()

    def set_media_backend(self, backend: MediaBackend) -> None:
        self._media_backend = backend
        self._channel.set_media_backend(backend)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._channel.set_media_backend(self._media_backend)
        try:
            await self._channel.start()
            for index in range(self._workers_per_channel):
                task = asyncio.create_task(
                    self._worker_loop(),
                    name=f"weixin-runner-{self.channel_id}-{index}",
                )
                self._workers.append(task)
        except BaseException:
            self._running = False
            for task in self._workers:
                task.cancel()
            if self._workers:
                await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
            try:
                await self._channel.stop()
            except Exception:
                logger.exception("Weixin runner cleanup after start failure failed")
            raise

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for task in self._workers:
            task.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        await self._channel.stop()
        self._queue = asyncio.Queue(maxsize=self._queue_maxsize)
        self._session_locks.clear()

    def enqueue(self, payload: Any) -> None:
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._put, payload)
        else:
            self._put(payload)

    def _put(self, payload: Any) -> None:
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.error("Weixin runner queue full; dropping payload")

    async def push_text(self, subject: ChannelSubject, text: str) -> None:
        await self._channel.push_text(subject, text)

    async def push_content(self, subject: ChannelSubject, parts: list[ContentPart]) -> None:
        await self._channel.push_message(subject, parts)

    async def push_to_all(self, text: str) -> None:
        for subject in self._channel.list_subjects():
            try:
                await self._channel.push_text(subject, text)
            except Exception:
                logger.exception("Failed to push to subject %s", subject.subject_id)

    def list_subjects(self) -> list[ChannelSubject]:
        return self._channel.list_subjects()

    async def run_in_session(self, session_key: str, operation: Any) -> Any:
        key = session_key.strip()
        if not key:
            raise ValueError("session_key must not be empty")
        async with self._session_lock(key):
            return await operation

    def _session_lock(self, session_key: str) -> asyncio.Lock:
        lock_key = f"{self._channel.channel_id}:{session_key}"
        return self._session_locks.setdefault(lock_key, asyncio.Lock())

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                try:
                    payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                message = (
                    payload
                    if isinstance(payload, InboundMessage)
                    else self._channel.parse_inbound(payload)
                )
                session_key = self._channel.get_debounce_key(message)
                batch = [message]
                if self._channel.should_batch_inbound(message):
                    batch.extend(self._drain_same_session(session_key))
                merged = self._channel.merge_inbound(batch) if len(batch) > 1 else batch[0]
                if self._pre_lock_handler is not None:
                    try:
                        await self._pre_lock_handler(merged)
                    except Exception:
                        logger.exception("Weixin runner pre-lock handler error")
                async with self._session_lock(session_key):
                    await self._channel.handle_inbound(merged)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Weixin runner worker error")

    def _drain_same_session(self, session_key: str) -> list[InboundMessage]:
        drained: list[InboundMessage] = []
        for _ in range(20):
            try:
                payload = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                message = (
                    payload
                    if isinstance(payload, InboundMessage)
                    else self._channel.parse_inbound(payload)
                )
            except Exception:
                logger.exception("Failed to parse queued Weixin payload")
                break
            if self._channel.get_debounce_key(message) != session_key:
                try:
                    self._queue.put_nowait(payload)
                except asyncio.QueueFull:
                    logger.warning(
                        "Weixin runner queue full when re-enqueuing payload, dropping"
                    )
                break
            drained.append(message)
        return drained
