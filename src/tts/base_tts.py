"""
Base TTS class - Abstract interface for text-to-speech engines
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TTSVoice:
    """Represents a TTS voice"""
    id: str
    name: str
    language: str
    language_code: str
    gender: str
    provider: str


@dataclass
class TTSResult:
    """Result of TTS generation"""
    audio_path: str
    duration: float
    text: str
    voice: TTSVoice
    success: bool
    error: Optional[str] = None
    word_timing_path: Optional[str] = None


class BaseTTS(ABC):
    """Abstract base class for TTS engines"""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%"
    ) -> TTSResult:
        pass

    @abstractmethod
    async def list_voices(self, language: str = None) -> List[TTSVoice]:
        pass

    @abstractmethod
    def get_default_voice(self, language: str) -> str:
        pass
