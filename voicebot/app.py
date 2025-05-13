# Copyright (C) 2025 Cisco Systems, Inc.

import argparse
import asyncio
import os

import grpc
import uvicorn
from common import logger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastrtc import Stream
from gradio.utils import get_space
from pydantic import BaseModel
from wgtwo.webterminal.v0 import webterminal_pb2
from wgtwo.webterminal.v0 import webterminal_pb2_grpc

import auth
import handlers.chatgpt
import handlers.echo
import handlers.gem

load_dotenv()

def arg(parser, name, env_var, required=False, help_text=None):
    value_from_env = os.environ.get(env_var)
    parser.add_argument(
        f"--{name.replace('_', '-')}",
        default=value_from_env,
        required=required and not value_from_env,
        help=help_text,
    )

parser = argparse.ArgumentParser(description="RTC Application")
arg(parser, "grpc_target", "GRPC_TARGET", required=True, help_text="WG2 API Gateway endpoint")
arg(parser, "client_id", "CLIENT_ID", required=True, help_text="WG2 Client ID")
arg(parser, "client_secret", "CLIENT_SECRET", required=True, help_text="WG2 Client Secret")
arg(parser, "msisdn", "MSISDN", required=True, help_text="MSISDN of subscription")
arg(parser, "openai_api_key", "OPENAI_API_KEY", required=False, help_text="OpenAI API Key")
arg(parser, "gemini_api_key", "GEMINI_API_KEY", required=False, help_text="Gemini API Key")
args = parser.parse_args()

grpcTarget = args.grpc_target
clientId = args.client_id
clientSecret = args.client_secret
msisdn = args.msisdn
openai_api_key = args.openai_api_key
gemini_api_key = args.gemini_api_key

class Body(BaseModel):
    sdp: str
    type: str
    webrtc_id: str

def initialize_handler():
    """Initialize the appropriate handler based on environment variables or arguments."""
    if openai_api_key:
        logger.info("Using OpenAI handler.")
        return handlers.chatgpt.OpenAIHandler(api_key=openai_api_key)
    elif gemini_api_key:
        logger.info("Using Gemini handler.")
        return handlers.gem.GeminiHandler(api_key=gemini_api_key)
    else:
        logger.info("Using Echo handler.")
        return handlers.echo.AsyncEchoHandler()

def initialize_stream(handler):
    """Initialize the Stream object."""
    return Stream(
        modality="audio",
        mode="send-receive",
        handler=handler,
        rtc_configuration={
            "iceServers": [],  # Disables STUN/TURN by providing an empty list
            "iceTransportPolicy": "all",  # Allows direct connections only (no STUN/TURN)
        },
        concurrency_limit=5 if get_space() else None,
        time_limit=90 if get_space() else None,
    )

def initialize_app():
    """Initialize the FastAPI app and mount the stream."""
    app = FastAPI()
    stream.mount(app)
    return app

async def handle_offer(offer, call_id):
    """Async function to process the offer and generate an answer."""
    logger.info(f"Received Offer for call_id {call_id}: SDP = {offer.sdp}, MSISDN = {offer.msisdn.e164}")

    o = Body(
        webrtc_id=call_id,
        sdp = offer.sdp.replace("a=rtcp:", "a=notrtcp:"),
        type = "offer"
    )
    logger.info(f"Created Body Offer {o}")
    # Generate answer (replace with actual SDP generation logic)
    answer_sdp = await stream.offer(o)
    logger.info(f"Generated Answer SDP: {answer_sdp}")
    answer = webterminal_pb2.Answer()
    answer.sdp = answer_sdp["sdp"]

    # Return the answer message
    return webterminal_pb2.WebTerminalMessage(
        answer=answer,
        call_id=call_id
    )

class BiDirectionalStreamHandler:
    def __init__(self):
        self.message_queue = asyncio.Queue()
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.closed:
            raise StopAsyncIteration

        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return webterminal_pb2.WebTerminalMessage()

    def put_message(self, message):
        """Add a message to the queue to be sent over the stream."""
        logger.info(f"Queueing message for call_id {message.call_id}")
        self.message_queue.put_nowait(message)

    def close(self):
        """Mark the stream as closed."""
        self.closed = True


async def run_async():
    channel = grpc.aio.secure_channel(grpcTarget, grpc.ssl_channel_credentials())

    credentials = call_credentials(clientId, clientSecret)

    stub = webterminal_pb2_grpc.WebTerminalServiceStub(channel)

    # Create the bidirectional stream handler
    stream_handler = BiDirectionalStreamHandler()

    metadata = [
        ("wg2-msisdn", msisdn),
    ]

    # Start the bidirectional streaming RPC
    response_stream = stub.MultiPipe(stream_handler, metadata=metadata, credentials=credentials)

    # Process incoming messages asynchronously
    async for response in response_stream:
        message_type = response.WhichOneof("message")
        if message_type == "bye":
            logger.warning(f"Received BYE for call_id {response.call_id}")
            stream.clean_up(response.call_id)

        if message_type == "offer":
            offer = response.offer
            call_id = response.call_id

            # Process the offer asynchronously
            answer_msg = await handle_offer(offer, call_id)

            # Queue the answer to be sent over the same stream
            logger.info(f"Sending Answer for call_id {call_id}: {answer_msg.answer.sdp}")
            stream_handler.put_message(answer_msg)

async def start_uvicorn(app):
    """Run FastAPI inside the asyncio event loop."""
    config = uvicorn.Config(app, host="localhost", port=54543, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    logger.info("Starting application...")

    """Run both FastAPI and gRPC together in the same asyncio event loop."""
    handler = initialize_handler()
    global stream  # Declare as global to use in other functions
    stream = initialize_stream(handler)
    app = initialize_app()

    # Create tasks explicitly
    tasks = [
        asyncio.create_task(start_uvicorn(app)),  # Pass the app to FastAPI
        asyncio.create_task(run_async()),  # Run gRPC logic
    ]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Cancellation received. Cleaning up...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)  # Ensure all tasks are cancelled
    finally:
        logger.info("Shutdown complete.")

def call_credentials(client_id, client_secret):
    auth_plugin = auth.AccessTokenCallCredentials(client_id, client_secret)
    return grpc.metadata_call_credentials(auth_plugin)

if __name__ == '__main__':
    asyncio.run(main())
