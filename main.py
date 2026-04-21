"""
Main Pipeline - Orchestrates the complete video generation and upload workflow

Usage:
    python main.py                    # Generate next part and upload
    python main.py --part 5           # Generate specific part
    python main.py --no-upload        # Generate without uploading
    python main.py --test             # Generate Part 1 as private (test mode)
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

import yaml

from src.syllabus.syllabus_manager import SyllabusManager
from src.script_generator.lesson_writer import LessonWriter
from src.tts.tts_manager import TTSManager
from src.video.composer import VideoComposer
from src.video.thumbnail import ThumbnailGenerator
from src.youtube.auth import YouTubeAuth
from src.youtube.uploader import YouTubeUploader
from src.youtube.metadata import MetadataGenerator
from src.youtube.comment_poster import CommentPoster
from src.youtube.playlist_manager import PlaylistManager
from src.utils.database import Database
from src.utils.logger import setup_logger, get_logger


class ReasoningVideoPipeline:
    """Complete pipeline: Topic → Script → Audio → Video → Upload → Comment → Playlist"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        # Load config
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Setup logger
        setup_logger(log_file="logs/pipeline.log")
        self.logger = get_logger("Pipeline")

        # Initialize components
        db_path = self.config.get("database", {}).get("path", "data/reasoning_tracker.db")
        self.db = Database(db_path)

        syllabus_path = self.config.get("syllabus", {}).get("file", "config/syllabus.yaml")
        self.syllabus = SyllabusManager(syllabus_path, self.db)

        llm_config = self.config.get("llm", {})
        self.lesson_writer = LessonWriter(
            provider=llm_config.get("provider", "groq"),
            model=llm_config.get("groq", {}).get("model", "llama-3.3-70b-versatile")
        )

        self.tts = TTSManager(config_path)
        self.composer = VideoComposer(self.config)
        self.thumbnail_gen = ThumbnailGenerator()
        self.metadata_gen = MetadataGenerator()

        # YouTube components (initialized lazily)
        self._yt_auth = None
        self._uploader = None
        self._comment_poster = None
        self._playlist_mgr = None

        self.logger.info("Pipeline initialized")

    @property
    def yt_auth(self):
        if not self._yt_auth:
            self._yt_auth = YouTubeAuth()
        return self._yt_auth

    @property
    def uploader(self):
        if not self._uploader:
            self._uploader = YouTubeUploader(self.yt_auth)
        return self._uploader

    @property
    def comment_poster(self):
        if not self._comment_poster:
            self._comment_poster = CommentPoster(self.yt_auth)
        return self._comment_poster

    @property
    def playlist_mgr(self):
        if not self._playlist_mgr:
            self._playlist_mgr = PlaylistManager(self.yt_auth)
        return self._playlist_mgr

    def _read_progress(self) -> int:
        """Read next part number from progress.json"""
        try:
            with open("progress.json", "r") as f:
                data = json.load(f)
            return data.get("next_part", 1)
        except Exception:
            return 1

    def _save_progress(self, completed_part: int) -> None:
        """Save progress to progress.json (persists across GitHub Actions runs)"""
        try:
            with open("progress.json", "r") as f:
                data = json.load(f)
        except Exception:
            data = {"next_part": 1, "completed": []}

        if completed_part not in data.get("completed", []):
            data["completed"].append(completed_part)
        data["next_part"] = completed_part + 1
        data["completed"] = sorted(data["completed"])

        with open("progress.json", "w") as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Progress saved: next_part={completed_part + 1}")

    async def run(self, part_number: int = None, upload: bool = True,
                  test_mode: bool = False) -> dict:
        """
        Run the complete pipeline for one video.

        Args:
            part_number: Specific part to generate (None = next in sequence)
            upload: Whether to upload to YouTube
            test_mode: Upload as private if True

        Returns:
            Result dictionary with status and paths
        """
        result = {"success": False, "part": 0}

        try:
            # Step 1: Get topic
            if part_number:
                topic = self.syllabus.get_topic_by_part(part_number)
            else:
                # Read progress from progress.json (for GitHub Actions persistence)
                next_part = self._read_progress()
                topic = self.syllabus.get_topic_by_part(next_part)

            if not topic:
                self.logger.error("No topic available")
                return result

            result["part"] = topic.part
            self.logger.info(f"=== Starting Part {topic.part}: {topic.title} ===")

            # Create DB record
            self.db.create_lesson_record(topic.part, topic.title, topic.category)

            # Step 2: Generate lesson script
            self.logger.info("Step 2: Generating lesson script...")
            lesson = self.lesson_writer.generate_lesson(topic)

            # Save script
            output_config = self.config.get("output", {})
            script_dir = output_config.get("script_dir", "output/scripts")
            script_path = Path(script_dir) / f"part_{topic.part:03d}_script.json"
            script_path.parent.mkdir(parents=True, exist_ok=True)

            script_data = {
                "part": topic.part,
                "title": topic.title,
                "category": topic.category,
                "introduction": lesson.introduction,
                "concept": lesson.concept_explanation,
                "formulas": [{"formula": f.formula, "explanation": f.explanation,
                              "label": f.visual_label} for f in lesson.formulas],
                "examples": [{"question": e.question, "steps": e.steps,
                              "answer": e.answer, "explanation": e.explanation}
                             for e in lesson.solved_examples],
                "tips": lesson.tips_and_tricks,
                "practice": [{"question": q.question, "options": q.options,
                              "correct": q.correct_answer, "explanation": q.explanation}
                             for q in lesson.practice_questions],
                "summary": lesson.summary_points,
            }
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script_data, f, indent=2, ensure_ascii=False)

            self.db.update_lesson_status(topic.part, "generated", script_path=str(script_path))

            # Step 3: Generate audio
            self.logger.info("Step 3: Generating audio...")
            audio_dir = output_config.get("audio_dir", "output/audio")
            narration_text = lesson.get_narration_text()
            audio_result = await self.tts.generate_lesson_audio(
                narration_text, audio_dir, topic.part
            )

            if not audio_result.get("success"):
                raise RuntimeError(f"Audio generation failed: {audio_result.get('error')}")

            audio_path = audio_result["audio_path"]
            self.db.update_lesson_status(topic.part, "generated", audio_path=audio_path)

            # Step 4: Compose video
            self.logger.info("Step 4: Composing video...")
            video_dir = output_config.get("video_dir", "output/videos")
            video_path = str(Path(video_dir) / f"part_{topic.part:03d}.mp4")
            self.composer.compose(lesson, audio_path, video_path)

            self.db.update_lesson_status(topic.part, "generated",
                                         video_path=video_path,
                                         duration=audio_result.get("duration", 0))
            result["video_path"] = video_path

            # Step 5: Generate thumbnail
            self.logger.info("Step 5: Generating thumbnail...")
            thumb_dir = output_config.get("thumbnail_dir", "output/thumbnails")
            thumb_path = str(Path(thumb_dir) / f"part_{topic.part:03d}_thumb.png")
            self.thumbnail_gen.generate(topic, thumb_path)
            self.db.update_lesson_status(topic.part, "generated", thumbnail_path=thumb_path)
            result["thumbnail_path"] = thumb_path

            if not upload:
                self.logger.info(f"Video generated (no upload): {video_path}")
                result["success"] = True
                return result

            # Step 6: Upload to YouTube
            self.logger.info("Step 6: Uploading to YouTube...")
            privacy = "private" if test_mode else self.config.get("youtube", {}).get("privacy_status", "public")

            metadata = self.metadata_gen.generate(topic, lesson)
            upload_result = self.uploader.upload(
                video_path=video_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                category_id=metadata["category_id"],
                privacy_status=privacy,
                thumbnail_path=thumb_path,
                made_for_kids=metadata["made_for_kids"]
            )

            if not upload_result.success:
                raise RuntimeError(f"Upload failed: {upload_result.error}")

            video_id = upload_result.video_id
            self.db.update_lesson_status(
                topic.part, "uploaded",
                youtube_id=video_id,
                youtube_url=upload_result.video_url
            )
            result["youtube_url"] = upload_result.video_url

            # Step 7: Add to playlist
            self.logger.info("Step 7: Adding to playlist...")
            self.playlist_mgr.add_video(video_id, position=topic.part - 1)

            # Step 8: Post study notes comment
            self.logger.info("Step 8: Posting study notes comment...")
            comment_id = self.comment_poster.post_study_notes(video_id, lesson)
            if comment_id:
                self.db.update_lesson_status(topic.part, "uploaded", comment_id=comment_id)

            # Update playlist description
            progress = self.db.get_progress()
            self.playlist_mgr.update_description(progress["uploaded"])

            # Save progress for next run
            self._save_progress(topic.part)

            self.logger.info(f"=== Part {topic.part} COMPLETE: {upload_result.video_url} ===")
            result["success"] = True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            result["error"] = str(e)
            if result.get("part"):
                self.db.update_lesson_status(result["part"], "failed", error=str(e))

        return result


def main():
    parser = argparse.ArgumentParser(description="Reasoning Mastery Video Pipeline")
    parser.add_argument("--part", type=int, help="Specific part number to generate")
    parser.add_argument("--no-upload", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--test", action="store_true", help="Test mode (upload as private)")
    parser.add_argument("--progress", action="store_true", help="Show progress")

    args = parser.parse_args()

    pipeline = ReasoningVideoPipeline()

    if args.progress:
        progress = pipeline.syllabus.get_progress()
        print(f"\n=== Reasoning Mastery Progress ===")
        print(f"Total Topics: {progress['total_topics']}")
        print(f"Completed: {progress['completed']}")
        print(f"Next Part: {progress['next_part']}")
        print(f"Progress: {progress['percentage']}%")
        return

    result = asyncio.run(pipeline.run(
        part_number=args.part,
        upload=not args.no_upload,
        test_mode=args.test
    ))

    if result["success"]:
        print(f"\nPart {result['part']} generated successfully!")
        if result.get("youtube_url"):
            print(f"YouTube: {result['youtube_url']}")
        if result.get("video_path"):
            print(f"Video: {result['video_path']}")
    else:
        print(f"\nFailed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
