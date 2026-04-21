"""
YouTube Metadata Generator - Creates SEO-optimized metadata for reasoning videos
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import yaml

from src.syllabus.topic_models import Topic, LessonPlan
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetadataGenerator:
    """Generates YouTube video metadata optimized for educational content."""

    def __init__(self, config_path: str = "config/youtube_config.yaml"):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load YouTube config: {e}")
            return {}

    def generate(self, topic: Topic, lesson: LessonPlan) -> Dict[str, Any]:
        """Generate complete metadata for a video."""
        meta_config = self.config.get("metadata", {})

        # Title
        title_template = meta_config.get(
            "title_template",
            "{category} Part {part}/200 | {topic} | Tips & Tricks | Competitive Exams"
        )
        title = title_template.format(
            category=topic.category_display,
            part=topic.part,
            topic=topic.title,
        )
        # YouTube title limit is 100 chars
        if len(title) > 100:
            title = f"{topic.category_display} Part {topic.part}/200 | {topic.title}"[:100]

        # Description
        topic_summary = "\n".join(f"- {sub}" for sub in topic.subtopics)
        desc_template = meta_config.get("description_template", "")
        description = desc_template.format(
            series_name="Reasoning Mastery",
            part=topic.part,
            topic=topic.title,
            category=topic.category_display,
            topic_summary=topic_summary,
        )

        # Tags
        base_tags = meta_config.get("tags", [])
        topic_tags = [
            topic.title.lower(),
            topic.category.replace("_", " "),
            f"part {topic.part}",
        ]
        for sub in topic.subtopics[:5]:
            topic_tags.append(sub.lower())

        tags = list(set(base_tags + topic_tags))[:500]

        return {
            "title": title,
            "description": description[:5000],
            "tags": tags,
            "category_id": meta_config.get("category_id", "27"),
            "made_for_kids": meta_config.get("made_for_kids", False),
        }
