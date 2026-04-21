"""
Scene models for video generation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SceneType(Enum):
    INTRO_TITLE = "intro_title"
    CONCEPT = "concept"
    FORMULA = "formula"
    EXAMPLE_QUESTION = "example_question"
    EXAMPLE_STEP = "example_step"
    EXAMPLE_ANSWER = "example_answer"
    TIPS = "tips"
    PRACTICE = "practice"
    SUMMARY = "summary"
    OUTRO = "outro"


@dataclass
class Scene:
    """A single scene/slide in the video"""
    scene_type: SceneType
    title: str = ""
    content_lines: List[str] = field(default_factory=list)
    highlight_text: str = ""
    step_number: int = 0
    total_steps: int = 0
    options: List[str] = field(default_factory=list)
    correct_option: str = ""
    narration: str = ""
    duration: float = 0.0
    part_number: int = 0
    total_parts: int = 200
    topic_category: str = ""
    section_label: str = ""
    formula_label: str = ""
