"""
Video Composer - Assembles final video from scenes, audio, and music
Prepends a channel intro video before the lesson content.
"""

from pathlib import Path
from typing import Optional

# Fix for Pillow 10+ (ANTIALIAS removed, use LANCZOS)
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    concatenate_videoclips, AudioFileClip, CompositeAudioClip,
    VideoFileClip
)

from .scene_builder import SceneBuilder
from src.syllabus.topic_models import LessonPlan
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VideoComposer:
    """Orchestrates the assembly of the final educational video."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.scene_builder = SceneBuilder()

        # Video settings
        video_config = self.config.get("video", {})
        self.fps = video_config.get("fps", 30)
        self.codec = video_config.get("codec", "libx264")
        self.bitrate = video_config.get("bitrate", "10000k")
        self.preset = video_config.get("preset", "medium")

        # Intro video
        comp_config = self.config.get("composition", {})
        self.intro_video_path = comp_config.get("intro_video", "")

        # Music settings
        music_config = comp_config.get("music", {})
        self.music_enabled = music_config.get("enabled", False)
        self.music_file = music_config.get("file", "")
        self.music_volume = music_config.get("volume", 0.08)

        logger.info("VideoComposer initialized")

    def compose(self, lesson: LessonPlan, audio_path: str,
                output_path: str) -> str:
        """
        Compose the final video from lesson plan and audio.
        Prepends the channel intro video if configured.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        all_clips = []
        intro_clip = None

        # 0. Prepend intro video if available
        if self.intro_video_path and Path(self.intro_video_path).exists():
            try:
                intro_clip = VideoFileClip(self.intro_video_path)
                # Resize to match our resolution if needed
                target_w = self.config.get("video", {}).get("resolution", {}).get("width", 1920)
                target_h = self.config.get("video", {}).get("resolution", {}).get("height", 1080)
                if intro_clip.size != (target_w, target_h):
                    intro_clip = intro_clip.resize((target_w, target_h))
                all_clips.append(intro_clip)
                logger.info(f"Intro video added: {self.intro_video_path} ({intro_clip.duration:.1f}s)")
            except Exception as e:
                logger.warning(f"Failed to load intro video: {e}")
                intro_clip = None

        # 1. Build scenes from lesson plan
        scenes = self.scene_builder.build_scenes(lesson)

        # 2. Load narration audio
        narration = AudioFileClip(audio_path)
        total_duration = narration.duration
        logger.info(f"Audio duration: {total_duration:.1f}s")

        # 3. Estimate scene durations
        durations = self.scene_builder.estimate_durations(scenes, total_duration)

        # 4. Render scenes to clips
        lesson_clips = self.scene_builder.scenes_to_clips(scenes, durations)
        all_clips.extend(lesson_clips)

        # 5. Concatenate all video clips (intro + lesson scenes)
        video = concatenate_videoclips(all_clips, method="compose")

        # 6. Build audio track
        # Intro video has its own audio, narration starts after intro
        intro_duration = intro_clip.duration if intro_clip else 0

        if intro_duration > 0:
            # Delay narration audio to start after intro video
            narration = narration.set_start(intro_duration)
            # Get intro audio
            intro_audio = intro_clip.audio
            if intro_audio:
                audio_tracks = [intro_audio.set_start(0), narration]
            else:
                audio_tracks = [narration]
        else:
            audio_tracks = [narration]

        # Add background music if available (plays during lesson part only)
        if self.music_enabled and self.music_file and Path(self.music_file).exists():
            try:
                music = AudioFileClip(self.music_file)
                if music.duration < video.duration:
                    loops = int(video.duration / music.duration) + 1
                    music = music.loop(n=loops)
                music = music.subclip(0, video.duration)
                music = music.volumex(self.music_volume)
                # Start music after intro
                if intro_duration > 0:
                    music = music.set_start(intro_duration)
                audio_tracks.append(music)
            except Exception as e:
                logger.warning(f"Failed to add background music: {e}")

        # Combine audio tracks
        final_audio = CompositeAudioClip(audio_tracks)
        video = video.set_audio(final_audio)

        # 7. Write final video
        logger.info(f"Rendering video: {output_path}")
        video.write_videofile(
            output_path,
            fps=self.fps,
            codec=self.codec,
            bitrate=self.bitrate,
            preset=self.preset,
            audio_codec="aac",
            threads=4,
            logger=None
        )

        # Cleanup
        narration.close()
        if intro_clip:
            intro_clip.close()
        video.close()

        total_video_duration = intro_duration + total_duration
        logger.info(f"Video composed: {output_path} ({total_video_duration:.1f}s, intro={intro_duration:.1f}s)")
        return output_path
