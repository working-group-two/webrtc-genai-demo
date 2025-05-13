# Copyright (C) 2025 Cisco Systems, Inc.

import asyncio
import base64
import numpy as np
import openai

from common import logger
from fastrtc import AdditionalOutputs
from fastrtc import AsyncStreamHandler
from fastrtc import wait_for_item
from openai.types.beta.realtime import ResponseAudioTranscriptDoneEvent

SAMPLE_RATE = 24000


class OpenAIHandler(AsyncStreamHandler):
    """Handler for OpenAI's real-time API."""

    def __init__(self, api_key: str) -> None:
        super().__init__(
            expected_layout="mono",
            output_sample_rate=SAMPLE_RATE,
            output_frame_size=480,
            input_sample_rate=16000,
        )
        self.api_key = api_key
        self.connection = None
        self.output_queue = asyncio.Queue()
        self.channel_set.set()

    def copy(self) -> "OpenAIHandler":
        """Create a copy of the handler."""
        return OpenAIHandler(api_key=self.api_key)

    async def start_up(self) -> None:
        """Connect to the real-time API."""
        logger.info("Connecting to OpenAI real-time API.")
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        async with self.client.beta.realtime.connect(
            model="gpt-4o-mini-realtime-preview-2024-12-17"
        ) as conn:
            await conn.session.update(
                session={"turn_detection": {"type": "server_vad"}}
            )
            self.connection = conn
            async for event in self.connection:
                if event.type == "response.audio_transcript.done":
                    await self.output_queue.put(AdditionalOutputs(event))
                elif event.type == "response.audio.delta":
                    await self.output_queue.put(
                        (
                            self.output_sample_rate,
                            np.frombuffer(
                                base64.b64decode(event.delta), dtype=np.int16
                            ).reshape(1, -1),
                        )
                    )

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        """Receive audio frames."""
        if not self.connection:
            return
        _, array = frame
        audio_message = base64.b64encode(array.squeeze().tobytes()).decode("utf-8")
        await self.connection.input_audio_buffer.append(audio=audio_message)  # type: ignore
        logger.info("Received audio frame.")

    async def emit(self) -> tuple[int, np.ndarray] | AdditionalOutputs | None:
        """Emit audio frames or additional outputs."""
        return await wait_for_item(self.output_queue)

    async def shutdown(self) -> None:
        """Shutdown the handler."""
        logger.info("Shutting down OpenAIHandler.")
        if self.connection:
            await self.connection.close()
            self.connection = None


def update_chatbot(chatbot: list[dict], response: ResponseAudioTranscriptDoneEvent):
    """Update the chatbot with a new response."""
    chatbot.append({"role": "assistant", "content": response.transcript})
    return chatbot
