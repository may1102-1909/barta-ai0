import io
import math
import wave
import logging
import httpx
from typing import Optional
from app.config import settings
from app.services.audio_converter import AudioConverter

logger = logging.getLogger(__name__)

class GnaniTimbreTTS:
    """
    Synthesizes speech using Gnani AI Timbre TTS model (v2.0)
    and formats it into 8 kHz μ-law audio ready for Twilio streaming.
    """

    def __init__(self):
        self.api_key = settings.GNANI_API_KEY
        self.api_url = settings.GNANI_TTS_API_URL or "https://api.vachana.ai/api/v1/tts/inference"
        self.voice = settings.GNANI_TTS_VOICE or "Shubham"

    async def synthesize(self, text: str, voice: Optional[str] = None, language: str = "hi") -> bytes:
        """
        Synthesizes text into 8 kHz μ-law audio bytes using Gnani Timbre TTS (Voice: Shubham).
        """
        if not text or not text.strip():
            return b""

        # If Gnani API key is set, call the official Timbre TTS endpoint
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    headers = {
                        "X-API-Key-ID": self.api_key,
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "text": text.strip(),
                        "model": "timbre-v3.0",
                        "voice": voice or self.voice or "Shubham",
                        "language": "hi",
                        "audio_config": {
                            "encoding": "linear_pcm",
                            "container": "wav",
                            "num_channels": 1,
                            "sample_rate": 8000,
                            "sample_width": 2
                        }
                    }
                    response = await client.post(self.api_url, json=payload, headers=headers)
                    if response.status_code == 200:
                        audio_data = response.content
                        # If the server returned WAV container, extract raw PCM samples
                        if audio_data.startswith(b"RIFF"):
                            pcm_data = self._extract_pcm_from_wav(audio_data)
                        else:
                            pcm_data = audio_data
                        
                        # Convert 16-bit PCM to 8-bit μ-law
                        ulaw_data = AudioConverter.pcm16_to_ulaw(pcm_data)
                        return ulaw_data
                    else:
                        logger.warning(
                            f"Gnani Timbre API returned {response.status_code}: {response.text}. Using fallback synthesis."
                        )
            except Exception as e:
                logger.error(f"Error calling Gnani Timbre TTS API: {e}")

        # Local development / simulation fallback: generate synthetic natural tone / silence frames
        return self._generate_fallback_audio(text)

    def _extract_pcm_from_wav(self, wav_bytes: bytes) -> bytes:
        """Extracts linear PCM data from WAV format and ensures 8kHz 16-bit mono."""
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                sample_rate = wf.getframerate()
                sampwidth = wf.getsampwidth()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())

                # If needed, resample to 8000 Hz
                if sample_rate != 8000:
                    frames = AudioConverter.resample_pcm(frames, sample_rate, 8000, sampwidth, channels)
                return frames
        except Exception as e:
            logger.warning(f"Could not parse WAV header, attempting direct slice: {e}")
            return wav_bytes[44:] if len(wav_bytes) > 44 else wav_bytes

    def _generate_fallback_audio(self, text: str, duration_sec: Optional[float] = None) -> bytes:
        """
        Generates pleasant synthetic test audio (8kHz μ-law) representing the spoken text duration.
        Approximates speech at ~15 characters per second so audio timing in tests is realistic.
        """
        if duration_sec is None:
            # roughly 15 chars per second, minimum 1.0 second, max 6.0 seconds
            duration_sec = max(1.0, min(6.0, len(text) / 15.0))

        sample_rate = 8000
        num_samples = int(sample_rate * duration_sec)
        pcm_bytes = bytearray()

        # Generate a mild harmonic acoustic pulse (440Hz + 880Hz soft chime)
        for i in range(num_samples):
            t = i / sample_rate
            # Mild modulated hum so it's audible on phone simulator
            sample_val = int(1200 * math.sin(2 * math.pi * 320 * t) * math.exp(-t * 0.8))
            # clamp to 16-bit signed
            sample_val = max(-32768, min(32767, sample_val))
            pcm_bytes.extend(sample_val.to_bytes(2, byteorder="little", signed=True))

        return AudioConverter.pcm16_to_ulaw(bytes(pcm_bytes))

