"""
Edge TTS Engine - Microsoft Edge Text-to-Speech (Free)
Adapted for educational reasoning content with natural delivery.
"""

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import List
import tempfile
import uuid
import shutil

try:
    import imageio_ffmpeg
    import pydub
    pydub.AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    pydub.AudioSegment.ffprobe = imageio_ffmpeg.get_ffmpeg_exe().replace('ffmpeg', 'ffprobe')
except ImportError:
    pass

import edge_tts
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

from .base_tts import BaseTTS, TTSVoice, TTSResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EdgeTTSEngine(BaseTTS):
    """Microsoft Edge TTS engine - free, high-quality voices."""

    DEFAULT_VOICES = {
        "en": "en-IN-PrabhatNeural",
        "en-us": "en-US-AndrewNeural",
        "en-in": "en-IN-PrabhatNeural",
        "hi": "hi-IN-MadhurNeural",
    }

    def __init__(
        self,
        default_voice: str = None,
        rate: str = "-5%",
        pitch: str = "-3Hz",
        volume: str = "+0%"
    ):
        self.default_voice = default_voice or self.DEFAULT_VOICES["en"]
        self.default_rate = rate
        self.default_pitch = pitch
        self.default_volume = volume
        logger.info(f"Initialized EdgeTTS with voice: {self.default_voice}")

    def _preprocess_text(self, text: str) -> str:
        """Clean text for natural TTS delivery of educational content."""
        # Remove markdown formatting
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
        text = re.sub(r'^[\s]*[▸♦→•\-\*]+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'[✔✗✓✕→←↑↓■□●○◆◇★☆]', '', text)

        # Add breathing pauses
        text = re.sub(r'\.\s+([A-Z])', r'.\n\1', text)
        text = re.sub(r'\n\n+', '.\n\n', text)
        text = re.sub(r'\n', ' ... ', text)
        text = re.sub(r':\s+', ': ... ', text)
        text = re.sub(r';\s+', '; ... ', text)

        # Break long sentences
        def break_long_sentence(m):
            s = m.group(0)
            if len(s) > 200:
                s = re.sub(
                    r'(?<!\w)(and|but|which|that|however|therefore)\s+',
                    r'\1, ', s, count=1
                )
            return s
        text = re.sub(r'[^.!?]+[.!?]', break_long_sentence, text)

        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    def _postprocess_audio(self, audio_path: str) -> None:
        """Apply audio enhancement for clear, warm voice."""
        try:
            audio = AudioSegment.from_file(audio_path)
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

    async def synthesize(
        self, text: str, output_path: str,
        voice: str = None, rate: str = None,
        pitch: str = None, volume: str = None
    ) -> TTSResult:
        voice = voice or self.default_voice
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch
        volume = volume or self.default_volume

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            communicate = edge_tts.Communicate(
                text=text, voice=voice, rate=rate, pitch=pitch, volume=volume
            )

            word_boundaries = []
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
                elif chunk["type"] == "WordBoundary":
                    word_boundaries.append({
                        "text": chunk["text"],
                        "offset_us": chunk["offset"] / 10,
                        "duration_us": chunk["duration"] / 10,
                    })

            with open(str(output_path), "wb") as f:
                f.write(audio_data)

            word_timing_path = str(Path(output_path).with_suffix('.wordtiming.json'))
            if word_boundaries:
                with open(word_timing_path, 'w', encoding='utf-8') as f:
                    json.dump(word_boundaries, f)
            else:
                word_timing_path = None

            self._postprocess_audio(str(output_path))
            duration = self._get_audio_duration(str(output_path))

            voice_info = TTSVoice(
                id=voice, name=voice,
                language=voice.split("-")[0],
                language_code="-".join(voice.split("-")[:2]),
                gender="unknown", provider="edge-tts"
            )

            return TTSResult(
                audio_path=str(output_path), duration=duration,
                text=text, voice=voice_info, success=True,
                word_timing_path=word_timing_path,
            )

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return TTSResult(
                audio_path="", duration=0, text=text,
                voice=TTSVoice(id=voice, name=voice, language="",
                               language_code="", gender="", provider="edge-tts"),
                success=False, error=str(e)
            )

    async def synthesize_long_text(
        self, text: str, output_path: str,
        voice: str = None, rate: str = None,
        pitch: str = None, max_chunk_size: int = 5000
    ) -> TTSResult:
        voice = voice or self.default_voice
        rate = rate or self.default_rate
        pitch = pitch or self.default_pitch

        chunks = self._split_text(text, max_chunk_size)
        logger.info(f"Split text into {len(chunks)} chunks")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.gettempdir()) / f"edge_tts_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_files = []

        try:
            all_word_boundaries = []
            cumulative_offset_us = 0.0

            for i, chunk in enumerate(chunks):
                temp_path = temp_dir / f"chunk_{i}.mp3"
                temp_files.append(temp_path)

                chunk_audio = b""
                for attempt in range(3):
                    try:
                        chunk_audio = b""
                        communicate = edge_tts.Communicate(
                            text=chunk, voice=voice, rate=rate, pitch=pitch
                        )
                        async for evt in communicate.stream():
                            if evt["type"] == "audio":
                                chunk_audio += evt["data"]
                            elif evt["type"] == "WordBoundary":
                                all_word_boundaries.append({
                                    "text": evt["text"],
                                    "offset_us": evt["offset"] / 10 + cumulative_offset_us,
                                    "duration_us": evt["duration"] / 10,
                                })
                        if chunk_audio:
                            break
                    except Exception as e:
                        if attempt == 2:
                            raise

                with open(str(temp_path), "wb") as f:
                    f.write(chunk_audio)

                chunk_dur = self._get_audio_duration(str(temp_path))
                cumulative_offset_us += chunk_dur * 1_000_000

            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                ffmpeg_exe = "ffmpeg"

            list_file = temp_dir / "files.txt"
            with open(list_file, "w") as f:
                for temp_file in temp_files:
                    f.write(f"file '{temp_file}'\n")

            cmd = [ffmpeg_exe, "-f", "concat", "-safe", "0",
                   "-i", str(list_file), "-c", "copy", "-y", str(output_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg error: {result.stderr}")

            self._postprocess_audio(str(output_path))

            try:
                duration_result = subprocess.run(
                    [ffmpeg_exe, "-i", str(output_path), "-f", "null", "-"],
                    capture_output=True, text=True
                )
                time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", duration_result.stderr)
                if time_match:
                    h, m, s = time_match.groups()
                    duration = int(h) * 3600 + int(m) * 60 + float(s)
                else:
                    duration = 0
            except Exception:
                duration = 0

            shutil.rmtree(str(temp_dir), ignore_errors=True)

            word_timing_path = str(Path(output_path).with_suffix('.wordtiming.json'))
            if all_word_boundaries:
                with open(word_timing_path, 'w', encoding='utf-8') as f:
                    json.dump(all_word_boundaries, f)
            else:
                word_timing_path = None

            voice_info = TTSVoice(
                id=voice, name=voice,
                language=voice.split("-")[0],
                language_code="-".join(voice.split("-")[:2]),
                gender="unknown", provider="edge-tts"
            )

            return TTSResult(
                audio_path=str(output_path), duration=duration,
                text=text, voice=voice_info, success=True,
                word_timing_path=word_timing_path,
            )

        except Exception as e:
            shutil.rmtree(str(temp_dir), ignore_errors=True)
            logger.error(f"Long text TTS failed: {e}")
            return TTSResult(
                audio_path="", duration=0, text=text,
                voice=TTSVoice(id=voice, name=voice, language="",
                               language_code="", gender="", provider="edge-tts"),
                success=False, error=str(e)
            )

    def _split_text(self, text: str, max_size: int) -> List[str]:
        if len(text) <= max_size:
            return [text]
        chunks = []
        current_chunk = ""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
        except Exception:
            return 0.0

    async def list_voices(self, language: str = None) -> List[TTSVoice]:
        voices = await edge_tts.list_voices()
        result = []
        for voice in voices:
            if language:
                voice_lang = voice["Locale"].split("-")[0].lower()
                if voice_lang != language.lower():
                    continue
            result.append(TTSVoice(
                id=voice["ShortName"], name=voice["FriendlyName"],
                language=voice["Locale"].split("-")[0],
                language_code=voice["Locale"],
                gender=voice.get("Gender", "Unknown"), provider="edge-tts"
            ))
        return result

    def get_default_voice(self, language: str) -> str:
        return self.DEFAULT_VOICES.get(language.lower(), self.DEFAULT_VOICES["en"])
