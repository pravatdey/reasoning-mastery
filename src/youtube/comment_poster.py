"""
YouTube Comment Poster - Posts study notes and practice questions as pinned comments
"""

from typing import Optional, Dict

import yaml

from .auth import YouTubeAuth
from src.syllabus.topic_models import LessonPlan
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CommentPoster:
    """Posts and pins study notes + practice questions on YouTube videos."""

    def __init__(self, auth: YouTubeAuth, config_path: str = "config/youtube_config.yaml"):
        self.auth = auth
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def post_study_notes(self, video_id: str, lesson: LessonPlan) -> Optional[str]:
        """
        Post study notes as a comment on the video.

        Returns:
            Comment ID if successful, None otherwise
        """
        youtube = self.auth.get_service()
        if not youtube:
            logger.error("Not authenticated for comment posting")
            return None

        try:
            # Build study notes comment
            comment_config = self.config.get("comment", {})
            template = comment_config.get("study_notes_template", "")

            topic = lesson.topic
            study_notes = lesson.get_study_notes()
            practice_text = lesson.get_practice_text()

            # Format key concepts
            key_concepts = study_notes.split("KEY CONCEPTS:")[-1].split("IMPORTANT FORMULAS:")[0].strip() if "KEY CONCEPTS:" in study_notes else ""

            # Format formulas
            formulas = ""
            for fb in lesson.formulas:
                formulas += f"  {fb.visual_label}: {fb.formula}\n"

            # Format tips
            tips = ""
            for i, tip in enumerate(lesson.tips_and_tricks, 1):
                tips += f"  {i}. {tip}\n"

            if template:
                comment_text = template.format(
                    part=topic.part,
                    topic=topic.title,
                    key_concepts=key_concepts,
                    formulas=formulas,
                    tips=tips,
                    practice_questions=practice_text,
                )
            else:
                # Fallback format
                comment_text = self._build_default_comment(lesson)

            # Trim to YouTube comment limit (10,000 chars)
            comment_text = comment_text[:10000]

            # Post the comment
            request = youtube.commentThreads().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": comment_text
                            }
                        }
                    }
                }
            )
            response = request.execute()
            comment_id = response["id"]

            logger.info(f"Study notes posted on video {video_id}, comment: {comment_id}")

            # Post answer key as reply
            self._post_answer_reply(youtube, comment_id, lesson)

            return comment_id

        except Exception as e:
            logger.error(f"Failed to post comment: {e}")
            return None

    def _post_answer_reply(self, youtube, parent_comment_id: str, lesson: LessonPlan) -> None:
        """Post answer key as a reply to the study notes comment."""
        try:
            comment_config = self.config.get("comment", {})
            template = comment_config.get("answer_key_template", "")

            answer_key = lesson.get_answer_key()

            if template:
                reply_text = template.format(
                    part=lesson.topic.part,
                    answers=answer_key,
                )
            else:
                reply_text = f"ANSWER KEY - Part {lesson.topic.part}:\n{answer_key}"

            # The parent_comment_id from commentThreads is the thread ID
            # We need the actual comment ID for replying
            thread_id = parent_comment_id
            # Get the top-level comment ID from the thread
            thread = youtube.commentThreads().list(
                part="snippet",
                id=thread_id
            ).execute()

            if thread.get("items"):
                top_comment_id = thread["items"][0]["snippet"]["topLevelComment"]["id"]

                youtube.comments().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "parentId": top_comment_id,
                            "textOriginal": reply_text[:10000]
                        }
                    }
                ).execute()

                logger.info("Answer key posted as reply")

        except Exception as e:
            logger.warning(f"Failed to post answer reply: {e}")

    def _build_default_comment(self, lesson: LessonPlan) -> str:
        """Build a default study notes comment."""
        topic = lesson.topic
        lines = [
            f"STUDY NOTES - Part {topic.part}/200: {topic.title}",
            "",
            "KEY CONCEPTS:",
        ]

        # Add concept summary
        sentences = lesson.concept_explanation.split(". ")[:3]
        for s in sentences:
            lines.append(f"  - {s.strip()}")

        lines.append("")
        lines.append("IMPORTANT FORMULAS:")
        for fb in lesson.formulas:
            lines.append(f"  {fb.formula}")

        lines.append("")
        lines.append("TIPS & TRICKS:")
        for i, tip in enumerate(lesson.tips_and_tricks, 1):
            lines.append(f"  {i}. {tip}")

        lines.append("")
        lines.append("PRACTICE QUESTIONS:")
        lines.append(lesson.get_practice_text())

        lines.append("")
        lines.append("Like and subscribe for daily reasoning lessons!")

        return "\n".join(lines)
