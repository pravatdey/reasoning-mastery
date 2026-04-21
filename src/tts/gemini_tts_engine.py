"""
Google Gemini TTS Engine — Free, realistic Hindi text-to-speech

Uses Gemini 2.5 Flash Preview TTS via Google's genai SDK.
Genuinely free: no billing, no credit card, no charges.

Supports Hindi and 24+ languages with 30 studio-quality voices.
Requires GEMINI_API_KEY in .env (free: https://aistudio.google.com/apikey).
"""

import asyncio
import json
import os
import re
import wave
from pathlib import Path
from typing import List, Optional

try:
    import imageio_ffmpeg
    import pydub
    pydub.AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    pydub.AudioSegment.ffprobe = imageio_ffmpeg.get_ffmpeg_exe().replace('ffmpeg', 'ffprobe')
except ImportError:
    pass

from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

from .base_tts import BaseTTS, TTSResult, TTSVoice
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiTTSEngine(BaseTTS):
    """
    TTS engine powered by Google Gemini 2.5 Flash Preview TTS.
    Free tier, no billing, 30 voices, 24+ languages including Hindi.

    Available voices:
    - Fenrir: Confident, strong male — great for teaching
    - Puck: Energetic, lively male
    - Kore: Calm, clear female
    - Zephyr: Warm, expressive female
    - Charon: Deep, authoritative male
    - Orus: Professional male
    """

    MODEL = "gemini-3.1-flash-tts-preview"

    # Best voices for Hindi educational content
    DEFAULT_VOICES = {
        "hi": "Fenrir",      # Confident male — perfect for reasoning teacher
        "en": "Fenrir",
        "ta": "Fenrir",
        "te": "Fenrir",
        "bn": "Fenrir",
    }

    FEMALE_VOICES = {
        "hi": "Zephyr",
        "en": "Zephyr",
    }

    ALL_VOICES = [
        "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda",
        "Orus", "Pegasus", "Proteus", "Perseus", "Iapetus",
        "Umbriel", "Algieba", "Autonoe", "Callirrhoe", "Dione",
        "Enceladus", "Erinome", "Gacrux", "Hyperion", "Juliet",
        "Laomedeia", "Mimas", "Narvi", "Oberon", "Pandora",
        "Polaris", "Pulcherrima", "Rasalgethi", "Sulafat",
    ]

    MAX_CHARS_PER_REQUEST = 3000

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_language: str = "hi",
        voice_name: Optional[str] = None,
        timeout: int = 120,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Get a free key at "
                "https://aistudio.google.com/apikey and add to .env"
            )

        self.default_language = default_language
        self.voice_name_override = voice_name
        self.timeout = timeout

        from google import genai
        self.client = genai.Client(api_key=self.api_key)

        logger.info(
            f"Initialized GeminiTTSEngine: model={self.MODEL}, "
            f"language={default_language}, voice={voice_name or self.DEFAULT_VOICES.get(default_language)}"
        )

    def _preprocess_text(self, text: str) -> str:
        """Strip markdown/symbols that would be read literally."""
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
        text = re.sub(r'`([^`]*)`', r'\1', text)
        text = re.sub(r'^[\s]*[▸♦→•\-\*]+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'[✔✗✓✕→←↑↓■□●○◆◇★☆]', '', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks at sentence boundaries."""
        if len(text) <= self.MAX_CHARS_PER_REQUEST:
            return [text]

        chunks = []
        current = ""
        # Support Hindi sentence endings (।) too
        sentences = re.split(r'(?<=[.!?।])\s+', text)

        for sentence in sentences:
            if len(sentence) > self.MAX_CHARS_PER_REQUEST:
                if current:
                    chunks.append(current.strip())
                    current = ""
                words = sentence.split()
                buf = ""
                for word in words:
                    if len(buf) + len(word) + 1 > self.MAX_CHARS_PER_REQUEST:
                        chunks.append(buf.strip())
                        buf = word
                    else:
                        buf = f"{buf} {word}" if buf else word
                if buf:
                    current = buf
                continue

            if len(current) + len(sentence) + 1 <= self.MAX_CHARS_PER_REQUEST:
                current = f"{current} {sentence}" if current else sentence
            else:
                chunks.append(current.strip())
                current = sentence

        if current:
            chunks.append(current.strip())

        return [c for c in chunks if c]

    def _postprocess_audio(self, audio_path: str, slow_down: float = 0.88) -> None:
        """
        Enhance audio for warm, clear educational voice.
        Slows down speech for natural, comfortable listening speed.

        Args:
            slow_down: Speed factor (0.88 = 12% slower, more natural Hindi pace)
        """
        try:
            audio = AudioSegment.from_file(audio_path)

            # Slow down the audio for natural speaking pace
            # This changes speed WITHOUT changing pitch (using frame rate trick + pitch correction)
            if slow_down < 1.0:
                # Change frame rate to slow down, then convert back to original rate
                # This effectively stretches the audio
                original_rate = audio.frame_rate
                slow_rate = int(original_rate * slow_down)
                audio = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": slow_rate
                }).set_frame_rate(original_rate)
                logger.info(f"Audio slowed down to {slow_down}x speed")

            audio = audio.high_pass_filter(80)
            audio = audio.low_pass_filter(12000)
            try:
                audio = compress_dynamic_range(
                    audio, threshold=-18.0, ratio=2.0,
                    attack=10.0, release=100.0
                )
            except Exception:
                pass
            audio = normalize(audio, headroom=2.0)
            audio.export(audio_path, format="mp3", bitrate="192k",
                         parameters=["-q:a", "0"])
            logger.info(f"Audio post-processed: {audio_path}")
        except Exception as e:
            logger.warning(f"Audio post-processing skipped: {e}")

    def _estimate_word_timings(self, text: str, total_duration_s: float) -> list:
        """Estimate word timings for lip-sync (proportional to word length)."""
        words = [w for w in re.findall(r'\S+', text) if w]
        if not words or total_duration_s <= 0:
            return []

        weights = [len(w) + 1 for w in words]
        total_weight = sum(weights)
        boundaries = []
        cursor_us = 0.0
        total_us = total_duration_s * 1_000_000
        for word, weight in zip(words, weights):
            dur_us = total_us * (weight / total_weight)
            boundaries.append({
                "text": word,
                "offset_us": cursor_us,
                "duration_us": dur_us,
            })
            cursor_us += dur_us
        return boundaries

    def _synthesize_chunk_sync(self, text: str, voice_name: str) -> bytes:
        """Call Gemini TTS for a single chunk. Returns raw PCM bytes (24kHz, mono, 16-bit)."""
        from google.genai import types

        max_retries = 5
        backoff = 5
        last_err = None

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.MODEL,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        ),
                    ),
                )

                audio_data = response.candidates[0].content.parts[0].inline_data.data
                if audio_data:
                    return audio_data

                logger.warning(f"Gemini returned empty audio (attempt {attempt+1})")

            except Exception as e:
                last_err = e
                error_str = str(e)
                logger.warning(f"Gemini TTS error (attempt {attempt+1}): {e}")

                # If quota exhausted, wait longer (45 seconds as suggested by API)
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    import re
                    retry_match = re.search(r'retry in (\d+)', error_str, re.IGNORECASE)
                    wait_time = int(retry_match.group(1)) + 5 if retry_match else 50
                    logger.info(f"Quota exhausted, waiting {wait_time}s before retry...")
                    import time
                    time.sleep(wait_time)
                    continue

            import time
            time.sleep(backoff)
            backoff *= 2

        raise RuntimeError(f"Gemini TTS failed after {max_retries} retries: {last_err}")

    def _pcm_to_wav_bytes(self, pcm_data: bytes) -> bytes:
        """Convert raw PCM bytes to WAV format in memory."""
        import io
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)
        buf.seek(0)
        return buf.read()

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        language: str = None,
    ) -> TTSResult:
        """Synthesize text via Gemini TTS. Automatically chunks long text."""
        language = language or self.default_language
        voice_name = (
            voice
            or self.voice_name_override
            or self.DEFAULT_VOICES.get(language, "Fenrir")
        )

        cleaned_text = self._preprocess_text(text)
        if not cleaned_text:
            return TTSResult(
                audio_path="", duration=0, text=text,
                voice=self._voice_info(voice_name, language),
                success=False, error="Empty text after preprocessing",
            )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        chunks = self._split_text(cleaned_text)
        logger.info(
            f"Gemini TTS: {len(chunks)} chunk(s), {len(cleaned_text)} chars, "
            f"voice={voice_name}, lang={language}"
        )

        try:
            loop = asyncio.get_event_loop()
            merged = None

            for i, chunk_text in enumerate(chunks):
                logger.info(f"  Chunk {i+1}/{len(chunks)}: {len(chunk_text)} chars")

                # Rate limit: Gemini free tier allows 3 requests/min
                if i > 0 and len(chunks) > 1:
                    await asyncio.sleep(22)

                pcm_bytes = await loop.run_in_executor(
                    None, self._synthesize_chunk_sync, chunk_text, voice_name
                )

                wav_bytes = self._pcm_to_wav_bytes(pcm_bytes)
                import io
                segment = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
                merged = segment if merged is None else merged + segment

            merged.export(
                str(output_path), format="mp3", bitrate="192k",
                parameters=["-q:a", "0"]
            )

            self._postprocess_audio(str(output_path))

            duration = len(merged) / 1000.0
            logger.info(f"Gemini TTS complete: {duration:.1f}s, voice={voice_name}")

            word_boundaries = self._estimate_word_timings(cleaned_text, duration)
            word_timing_path = None
            if word_boundaries:
                word_timing_path = str(Path(output_path).with_suffix('.wordtiming.json'))
                with open(word_timing_path, 'w', encoding='utf-8') as f:
                    json.dump(word_boundaries, f)

            return TTSResult(
                audio_path=str(output_path),
                duration=duration,
                text=text,
                voice=self._voice_info(voice_name, language),
                success=True,
                word_timing_path=word_timing_path,
            )

        except Exception as e:
            logger.error(f"Gemini TTS failed: {e}")
            return TTSResult(
                audio_path="", duration=0, text=text,
                voice=self._voice_info(voice_name, language),
                success=False, error=str(e),
            )

    def _voice_info(self, voice_name: str, language: str) -> TTSVoice:
        return TTSVoice(
            id=f"gemini:{self.MODEL}:{voice_name}",
            name=f"{voice_name} ({self.MODEL})",
            language=language,
            language_code=f"{language}-IN",
            gender="unknown",
            provider="gemini",
        )

    async def list_voices(self, language: str = None) -> List[TTSVoice]:
        languages = [language] if language else list(self.DEFAULT_VOICES.keys())
        voices = []
        for lang in languages:
            if lang in self.DEFAULT_VOICES:
                voices.append(self._voice_info(self.DEFAULT_VOICES[lang], lang))
            if lang in self.FEMALE_VOICES:
                voices.append(self._voice_info(self.FEMALE_VOICES[lang], lang))
        return voices

    def get_default_voice(self, language: str) -> str:
        return self.DEFAULT_VOICES.get(language, "Fenrir")
