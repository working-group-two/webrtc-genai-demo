# Copyright (C) 2025 Cisco Systems, Inc.

import asyncio

import numpy as np
from common import logger
from fastrtc import AsyncStreamHandler
from fastrtc import wait_for_item


class AsyncEchoHandler(AsyncStreamHandler):
    """Echo handler for testing purposes."""

    def __init__(self) -> None:
        super().__init__()
        self.queue = asyncio.Queue()
        self.channel_set.set()
        logger.info("Echo handler started.")

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        """Receive audio frames."""
        self.queue.put_nowait(frame)
        logger.debug("Received audio frame.")

    async def emit(self) -> tuple[int, np.ndarray] | None:
        """Emit audio frames."""
        return await wait_for_item(self.queue)

    def copy(self) -> "AsyncEchoHandler":
        """Create a copy of the handler."""
        return AsyncEchoHandler()

    async def shutdown(self) -> None:
        """Shutdown the handler."""
        logger.info("Echo handler shutting down.")

    async def start_up(self) -> None:
        """Start up the handler."""
        pass
