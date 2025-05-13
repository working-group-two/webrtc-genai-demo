# Copyright (C) 2025 Cisco Systems, Inc.

import asyncio
import base64
import os
from typing import AsyncGenerator
from typing import Literal

import numpy as np
from common import logger
from fastrtc import AsyncStreamHandler
from fastrtc import wait_for_item
from google import genai
from google.genai.types import LiveConnectConfig
from google.genai.types import PrebuiltVoiceConfig
from google.genai.types import SpeechConfig
from google.genai.types import VoiceConfig


class GeminiHandler(AsyncStreamHandler):
    """Handler for the Gemini API."""

    def __init__(
        self,
        api_key: str,
        expected_layout: Literal["mono"] = "mono",
        output_sample_rate: int = 24000,
        output_frame_size: int = 480,
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            output_frame_size,
            input_sample_rate=16000,
        )
        self.api_key = api_key
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.quit: asyncio.Event = asyncio.Event()
        self.channel_set.set()

    def copy(self) -> "GeminiHandler":
        return GeminiHandler(
            api_key=self.api_key,
            expected_layout="mono",
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )

    async def start_up(self):
        """Start the Gemini session."""
        logger.info("Starting Gemini session.")
        voice_name = "Puck"

        client = genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1alpha"},
        )

        config = LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

        async with client.aio.live.connect(
            model="gemini-2.0-flash-exp", config=config
        ) as session:
            async for audio in session.start_stream(
                stream=self.stream(), mime_type="audio/pcm"
            ):
                if audio.data:
                    array = np.frombuffer(audio.data, dtype=np.int16)
                    self.output_queue.put_nowait((self.output_sample_rate, array))

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Stream audio data."""
        while not self.quit.is_set():
            try:
                audio = await asyncio.wait_for(self.input_queue.get(), 0.1)
                yield audio
            except asyncio.TimeoutError:
                pass

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        """Receive audio frames."""
        _, array = frame
        audio_message = encode_audio(array.squeeze())
        self.input_queue.put_nowait(audio_message)
        logger.info("Received audio frame.")

    async def emit(self) -> tuple[int, np.ndarray] | None:
        """Emit audio frames."""
        return await wait_for_item(self.output_queue)

    def shutdown(self) -> None:
        """Shutdown the handler."""
        logger.info("Gemini handler shutting down.")
        self.quit.set()


def encode_audio(data: np.ndarray) -> str:
    """Encode audio data to send to the server."""
    return base64.b64encode(data.tobytes()).decode("UTF-8")
