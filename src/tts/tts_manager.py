"""
TTS Manager - Orchestrates text-to-speech generation for educational content

Primary: Google Gemini TTS (free, realistic Hindi voice)
Fallback: Microsoft Edge TTS (free, always available)
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

import yaml

from .edge_tts_engine import EdgeTTSEngine
from .base_tts import TTSResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class TTSManager:
    """
    Manages TTS generation with Gemini (primary) and Edge TTS (fallback).

    Gemini TTS provides realistic Hindi voice that sounds natural and attractive.
    If Gemini fails, automatically falls back to Edge TTS.
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)

        tts_config = self.config.get("tts", {})
        self.provider = tts_config.get("provider", "gemini")

        # Always create Edge TTS as fallback
        edge_config = tts_config.get("edge", {})
        self.edge_engine = EdgeTTSEngine(
            rate=edge_config.get("rate", "-5%"),
            pitch=edge_config.get("pitch", "-3Hz"),
            volume=edge_config.get("volume", "+0%"),
        )

        # Try to initialize Gemini as primary
        self.gemini_engine = None
        if self.provider == "gemini":
            try:
                from .gemini_tts_engine import GeminiTTSEngine
                gemini_config = tts_config.get("gemini", {})
                self.gemini_engine = GeminiTTSEngine(
                    api_key=os.getenv("GEMINI_API_KEY"),
                    default_language=gemini_config.get("default_language", "hi"),
                    voice_name=gemini_config.get("voice_name"),
                    timeout=gemini_config.get("timeout", 120),
                )
                logger.info("TTSManager ready: Gemini TTS (realistic Hindi) + Edge TTS fallback")
            except Exception as e:
                logger.warning(f"Gemini TTS init failed ({e}), using Edge TTS only")
                self.provider = "edge"

        if self.provider == "edge":
            logger.info("TTSManager ready: Edge TTS")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}

    async def generate_audio(
        self, text: str, output_path: str,
        voice: str = None, rate: str = None, pitch: str = None,
        language: str = None
    ) -> TTSResult:
        """
        Generate audio from text.
        Tries Gemini first (realistic Hindi), falls back to Edge TTS.
        """
        # Try Gemini TTS first
        if self.gemini_engine is not None:
            try:
                logger.info(f"Generating audio via Gemini TTS (Hindi realistic voice)...")
                result = await self.gemini_engine.synthesize(
                    text=text,
                    output_path=output_path,
                    language=language or "hi",
                )
                if result.success:
                    return result
                logger.warning(f"Gemini TTS failed ({result.error}), falling back to Edge TTS")
            except Exception as e:
                logger.warning(f"Gemini TTS exception ({e}), falling back to Edge TTS")

        # Fallback to Edge TTS
        if len(text) > 5000:
            return await self.edge_engine.synthesize_long_text(
                text=text, output_path=output_path,
                voice=voice, rate=rate, pitch=pitch,
            )
        return await self.edge_engine.synthesize(
            text=text, output_path=output_path,
            voice=voice, rate=rate, pitch=pitch,
        )

    def generate_audio_sync(
        self, text: str, output_path: str,
        voice: str = None, rate: str = None, pitch: str = None
    ) -> TTSResult:
        """Synchronous wrapper for audio generation."""
        return asyncio.run(self.generate_audio(
            text=text, output_path=output_path,
            voice=voice, rate=rate, pitch=pitch
        ))

    async def generate_lesson_audio(
        self, narration_text: str, output_dir: str, part_number: int
    ) -> Dict[str, Any]:
        """Generate audio for a lesson."""
        output_path = Path(output_dir) / f"part_{part_number:03d}_audio.mp3"

        result = await self.generate_audio(
            text=narration_text,
            output_path=str(output_path)
        )

        if result.success:
            logger.info(f"Generated lesson audio: Part {part_number}, {result.duration:.1f}s, provider={result.voice.provider}")
            return {
                "success": True,
                "audio_path": result.audio_path,
                "duration": result.duration,
                "word_timing_path": result.word_timing_path,
            }
        else:
            logger.error(f"Failed to generate audio: {result.error}")
            return {"success": False, "error": result.error}
