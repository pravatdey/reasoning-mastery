"""
Lesson Writer - Generates structured lesson content using LLM
"""

import json
import re
from typing import Optional

from .llm_client import LLMClient
from .prompt_templates import SYSTEM_PROMPT, LESSON_PROMPT_TEMPLATE
from src.syllabus.topic_models import Topic, LessonPlan, FormulaBlock, Example, Question
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LessonWriter:
    """Generates complete lesson plans from topics using LLM."""

    def __init__(self, provider: str = "groq", **llm_kwargs):
        self.llm = LLMClient(provider=provider, **llm_kwargs)
        logger.info("LessonWriter initialized")

    def generate_lesson(self, topic: Topic, max_retries: int = 3) -> LessonPlan:
        """Generate a complete lesson plan for a topic."""
        prompt = LESSON_PROMPT_TEMPLATE.format(
            title=topic.title,
            part=topic.part,
            category=topic.category_display,
            difficulty=topic.difficulty,
            subtopics=", ".join(topic.subtopics),
            formulas=", ".join(topic.formulas) if topic.formulas else "No specific formulas",
            duration_target=topic.duration_target_minutes,
        )

        for attempt in range(max_retries):
            try:
                logger.info(f"Generating lesson for Part {topic.part}: {topic.title} (attempt {attempt + 1})")

                response = self.llm.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    max_tokens=8000,
                    temperature=0.7
                )

                lesson_data = self._parse_response(response)
                if lesson_data:
                    lesson = self._build_lesson_plan(topic, lesson_data)
                    logger.info(f"Lesson generated: {len(lesson.get_narration_text())} chars narration")
                    return lesson

                logger.warning(f"Failed to parse response (attempt {attempt + 1})")

            except Exception as e:
                logger.error(f"Lesson generation error (attempt {attempt + 1}): {e}")

        # Fallback: create a basic lesson plan
        logger.warning(f"Using fallback lesson for Part {topic.part}")
        return self._create_fallback_lesson(topic)

    def _parse_response(self, response: str) -> Optional[dict]:
        """Parse LLM response as JSON."""
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object boundaries
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(response[start:end + 1])
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not parse JSON from response: {response[:200]}...")
        return None

    def _build_lesson_plan(self, topic: Topic, data: dict) -> LessonPlan:
        """Build a LessonPlan from parsed JSON data."""
        formulas = []
        for f in data.get("formulas", []):
            formulas.append(FormulaBlock(
                formula=f.get("formula", ""),
                explanation=f.get("explanation", ""),
                visual_label=f.get("visual_label", ""),
            ))

        examples = []
        for e in data.get("solved_examples", []):
            examples.append(Example(
                question=e.get("question", ""),
                steps=e.get("steps", []),
                answer=e.get("answer", ""),
                explanation=e.get("explanation", ""),
            ))

        questions = []
        for q in data.get("practice_questions", []):
            questions.append(Question(
                question=q.get("question", ""),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation", ""),
            ))

        return LessonPlan(
            topic=topic,
            introduction=data.get("introduction", ""),
            concept_explanation=data.get("concept_explanation", ""),
            formulas=formulas,
            solved_examples=examples,
            tips_and_tricks=data.get("tips_and_tricks", []),
            practice_questions=questions,
            summary_points=data.get("summary_points", []),
        )

    def _create_fallback_lesson(self, topic: Topic) -> LessonPlan:
        """Create a basic lesson plan when LLM fails."""
        return LessonPlan(
            topic=topic,
            introduction=f"Welcome to Part {topic.part} of 200. Today we will learn about {topic.title}. This is an important topic for competitive exams.",
            concept_explanation=f"{topic.title} is a key topic in {topic.category_display}. It covers: {', '.join(topic.subtopics)}. Let's understand each concept step by step.",
            formulas=[
                FormulaBlock(
                    formula=f,
                    explanation=f"This formula is essential for solving {topic.title} problems.",
                    visual_label=f"Formula {i+1}"
                )
                for i, f in enumerate(topic.formulas[:3])
            ],
            solved_examples=[
                Example(
                    question=f"Example question on {sub}",
                    steps=["Step 1: Identify the pattern", "Step 2: Apply the concept", "Step 3: Verify the answer"],
                    answer="See the detailed solution",
                    explanation="This approach works because it follows the standard method."
                )
                for sub in topic.subtopics[:3]
            ],
            tips_and_tricks=[
                "Always read the question carefully before solving",
                "Look for patterns and shortcuts",
                "Practice with a timer to improve speed",
            ],
            practice_questions=[],
            summary_points=[
                f"{topic.title} is essential for competitive exams",
                "Practice regularly with timed exercises",
                "Review formulas before the exam",
            ],
        )
