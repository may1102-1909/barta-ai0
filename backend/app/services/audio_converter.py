import audioop
import base64
from typing import List, Tuple

class AudioConverter:
    """
    Handles bidirectional audio transcoding between Twilio Programmable Voice 
    (8 kHz, 8-bit μ-law / PCMU) and Gnani AI Prisma/Timbre 
    (8 kHz or 16 kHz, 16-bit linear PCM, mono, little-endian).
    """

    @staticmethod
    def ulaw_to_pcm16(ulaw_bytes: bytes) -> bytes:
        """
        Converts 8 kHz 8-bit μ-law (Twilio) to 8 kHz 16-bit signed linear PCM (Prisma STT).
        Sample width is 2 bytes (16-bit).
        """
        if not ulaw_bytes:
            return b""
        return audioop.ulaw2lin(ulaw_bytes, 2)

    @staticmethod
    def pcm16_to_ulaw(pcm16_bytes: bytes) -> bytes:
        """
        Converts 8 kHz 16-bit signed linear PCM (Gnani Timbre TTS) to 8 kHz 8-bit μ-law (Twilio).
        """
        if not pcm16_bytes:
            return b""
        return audioop.lin2ulaw(pcm16_bytes, 2)

    @staticmethod
    def resample_pcm(pcm_bytes: bytes, in_rate: int, out_rate: int, width: int = 2, channels: int = 1) -> bytes:
        """
        Resamples PCM audio between different sample rates (e.g. 16kHz <-> 8kHz).
        """
        if in_rate == out_rate or not pcm_bytes:
            return pcm_bytes
        converted, _ = audioop.ratecv(pcm_bytes, width, channels, in_rate, out_rate, None)
        return converted

    @staticmethod
    def base64_to_bytes(b64_str: str) -> bytes:
        """Decodes base64 string from Twilio media event to raw bytes."""
        return base64.b64decode(b64_str)

    @staticmethod
    def bytes_to_base64(raw_bytes: bytes) -> str:
        """Encodes raw audio bytes to base64 string for Twilio media event."""
        return base64.b64encode(raw_bytes).decode("ascii")

    @staticmethod
    def chunk_ulaw(ulaw_bytes: bytes, frame_ms: int = 20, sample_rate: int = 8000) -> List[bytes]:
        """
        Splits μ-law audio into frames for Twilio streaming.
        At 8kHz, 1 byte = 1 sample. 20ms = 160 bytes.
        """
        bytes_per_frame = int((sample_rate * frame_ms) / 1000)
        chunks = []
        for i in range(0, len(ulaw_bytes), bytes_per_frame):
            chunks.append(ulaw_bytes[i:i + bytes_per_frame])
        return chunks

    @staticmethod
    def create_media_event(stream_sid: str, payload_b64: str) -> dict:
        """Constructs Twilio media stream event."""
        return {
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": payload_b64
            }
        }

    @staticmethod
    def create_clear_event(stream_sid: str) -> dict:
        """Constructs Twilio clear event to interrupt ongoing agent audio on barge-in."""
        return {
            "event": "clear",
            "streamSid": stream_sid
        }

    @staticmethod
    def create_mark_event(stream_sid: str, mark_name: str) -> dict:
        """Constructs Twilio mark event to track playback completion."""
        return {
            "event": "mark",
            "streamSid": stream_sid,
            "mark": {
                "name": mark_name
            }
        }

