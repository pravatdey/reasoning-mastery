"""
Syllabus Manager - Loads and manages the 200-topic syllabus
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

from .topic_models import Topic
from src.utils.logger import get_logger
from src.utils.database import Database

logger = get_logger(__name__)


class SyllabusManager:
    """Loads the syllabus YAML and tracks progress through the database."""

    def __init__(self, config_path: str = "config/syllabus.yaml", db: Database = None):
        self.config_path = config_path
        self.db = db
        self.topics: Dict[int, Topic] = {}
        self._load_syllabus()

    def _load_syllabus(self) -> None:
        """Load all topics from syllabus YAML"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            syllabus = data.get("syllabus", {})
            sections = syllabus.get("sections", [])

            for section in sections:
                category = section.get("category", "verbal_reasoning")
                for topic_data in section.get("topics", []):
                    part = topic_data["part"]
                    self.topics[part] = Topic(
                        part=part,
                        title=topic_data["title"],
                        category=category,
                        subtopics=topic_data.get("subtopics", []),
                        difficulty=topic_data.get("difficulty", "intermediate"),
                        formulas=topic_data.get("formulas", []),
                        duration_target_minutes=topic_data.get("duration_target_minutes", 8),
                    )

            logger.info(f"Loaded {len(self.topics)} topics from syllabus")

        except Exception as e:
            logger.error(f"Failed to load syllabus: {e}")
            raise

    def get_next_topic(self) -> Optional[Topic]:
        """Get the next topic to generate based on DB progress"""
        if self.db:
            next_part = self.db.get_next_part_number()
        else:
            next_part = 1

        return self.get_topic_by_part(next_part)

    def get_topic_by_part(self, part_number: int) -> Optional[Topic]:
        """Get a specific topic by part number"""
        topic = self.topics.get(part_number)
        if not topic:
            logger.warning(f"Topic not found for part {part_number}")
        return topic

    def get_all_topics(self) -> List[Topic]:
        """Get all topics sorted by part number"""
        return [self.topics[k] for k in sorted(self.topics.keys())]

    def get_topics_by_category(self, category: str) -> List[Topic]:
        """Get topics filtered by category"""
        return [t for t in self.get_all_topics() if t.category == category]

    def get_progress(self) -> Dict[str, Any]:
        """Get progress summary"""
        total = len(self.topics)
        db_progress = self.db.get_progress() if self.db else {}
        return {
            "total_topics": total,
            "completed": db_progress.get("uploaded", 0),
            "next_part": db_progress.get("next_part", 1),
            "percentage": round(db_progress.get("uploaded", 0) / total * 100, 1) if total else 0,
        }

    def mark_completed(self, part_number: int, video_id: str = "") -> None:
        """Mark a topic as completed"""
        if self.db:
            self.db.update_lesson_status(
                part_number, "uploaded",
                youtube_id=video_id
            )
            logger.info(f"Part {part_number} marked as completed")
