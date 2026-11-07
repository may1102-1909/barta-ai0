import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional
import websockets
from app.config import settings

logger = logging.getLogger(__name__)

class GnaniPrismaSTT:
    """
    Streams raw 16-bit PCM audio (8 kHz, mono) to Gnani Prisma STT 
    over WebSocket at wss://api.vachana.ai/stt/v3/stream.
    """

    def __init__(
        self,
        on_transcript: Callable[[str, bool, Optional[str]], Awaitable[None]],
        sample_rate: int = 8000,
        language: str = "hin-eng"
    ):
        self.on_transcript = on_transcript
        self.sample_rate = sample_rate
        self.language = language
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self.is_connected = False
        self.api_key = settings.GNANI_API_KEY

    async def connect(self):
        """Connects to Gnani Prisma streaming WebSocket endpoint."""
        if not self.api_key:
            logger.info("Gnani API key not configured. Gnani STT running in mock/offline mode.")
            self.is_connected = True
            return

        headers = {
            "X-API-Key-ID": self.api_key,
            "x-sample-rate": str(self.sample_rate),
            "x-language": self.language,
            "x-encoding": "pcm"
        }

        try:
            self.ws = await websockets.connect(
                settings.GNANI_STT_WS_URL,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            self.is_connected = True
            self._receive_task = asyncio.create_task(self._listen_loop())
            logger.info("Connected to Gnani Prisma STT WebSocket.")
        except Exception as e:
            logger.error(f"Failed to connect to Gnani Prisma WebSocket: {e}")
            self.is_connected = False

    async def send_audio(self, pcm_bytes: bytes):
        """Sends raw 16-bit PCM audio chunk to Gnani STT."""
        if not self.is_connected or not pcm_bytes:
            return

        if self.ws and not self.ws.closed:
            try:
                await self.ws.send(pcm_bytes)
            except Exception as e:
                logger.error(f"Error streaming audio to Gnani Prisma: {e}")

    async def _listen_loop(self):
        """Continuously receives transcription events from Gnani Prisma STT."""
        try:
            while self.is_connected and self.ws and not self.ws.closed:
                message = await self.ws.recv()
                try:
                    data = json.loads(message)
                    # Gnani Prisma response structure
                    # transcript, is_final, language
                    text = data.get("transcript") or data.get("text") or data.get("asr_output", "")
                    is_final = data.get("is_final", False) or data.get("final", False) or data.get("type") == "final"
                    detected_lang = data.get("language") or data.get("lang")

                    if text and text.strip():
                        await self.on_transcript(text.strip(), is_final, detected_lang)
                except json.JSONDecodeError:
                    if isinstance(message, str) and message.strip():
                        await self.on_transcript(message.strip(), True, None)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Gnani Prisma WebSocket connection closed.")
        except Exception as e:
            logger.error(f"Error in Gnani Prisma listen loop: {e}")
        finally:
            self.is_connected = False

    async def close(self):
        """Closes the WebSocket connection."""
        self.is_connected = False
        if self._receive_task:
            self._receive_task.cancel()
        if self.ws and not self.ws.closed:
            await self.ws.close()
            logger.info("Gnani Prisma STT connection closed.")

