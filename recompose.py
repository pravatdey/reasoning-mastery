"""
Recompose video from existing audio/script — NO API calls.
Useful for adding intro video or changing visual layout without regenerating content.

Usage: python recompose.py --part 1
"""

import argparse
import json
from pathlib import Path

import yaml

from src.syllabus.topic_models import Topic, LessonPlan, FormulaBlock, Example, Question
from src.video.composer import VideoComposer
from src.video.thumbnail import ThumbnailGenerator
from src.utils.logger import setup_logger, get_logger


def load_lesson_from_script(script_path: str) -> LessonPlan:
    """Load a LessonPlan from a saved script JSON file."""
    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    topic = Topic(
        part=data["part"],
        title=data["title"],
        category=data["category"],
    )

    formulas = [
        FormulaBlock(
            formula=f.get("formula", ""),
            explanation=f.get("explanation", ""),
            visual_label=f.get("label", f.get("visual_label", "")),
        )
        for f in data.get("formulas", [])
    ]

    examples = [
        Example(
            question=e.get("question", ""),
            steps=e.get("steps", []),
            answer=e.get("answer", ""),
            explanation=e.get("explanation", ""),
        )
        for e in data.get("examples", [])
    ]

    questions = [
        Question(
            question=q.get("question", ""),
            options=q.get("options", []),
            correct_answer=q.get("correct", q.get("correct_answer", "")),
            explanation=q.get("explanation", ""),
        )
        for q in data.get("practice", [])
    ]

    return LessonPlan(
        topic=topic,
        introduction=data.get("introduction", ""),
        concept_explanation=data.get("concept", ""),
        formulas=formulas,
        solved_examples=examples,
        tips_and_tricks=data.get("tips", []),
        practice_questions=questions,
        summary_points=data.get("summary", []),
    )


def main():
    parser = argparse.ArgumentParser(description="Recompose video (no API calls)")
    parser.add_argument("--part", type=int, required=True, help="Part number")
    args = parser.parse_args()

    setup_logger(log_file="logs/recompose.log")
    logger = get_logger("Recompose")

    part = args.part
    script_path = f"output/scripts/part_{part:03d}_script.json"
    audio_path = f"output/audio/part_{part:03d}_audio.mp3"
    video_path = f"output/videos/part_{part:03d}.mp4"
    thumb_path = f"output/thumbnails/part_{part:03d}_thumb.png"

    if not Path(script_path).exists():
        print(f"Script not found: {script_path}")
        return
    if not Path(audio_path).exists():
        print(f"Audio not found: {audio_path}")
        return

    # Load config
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Load lesson from saved script
    logger.info(f"Loading script: {script_path}")
    lesson = load_lesson_from_script(script_path)

    # Recompose video with intro
    logger.info(f"Recomposing video with intro...")
    composer = VideoComposer(config)
    composer.compose(lesson, audio_path, video_path)

    # Regenerate thumbnail
    logger.info("Generating thumbnail...")
    ThumbnailGenerator().generate(lesson.topic, thumb_path)

    print(f"\nRecomposed successfully!")
    print(f"Video: {video_path}")
    print(f"Thumbnail: {thumb_path}")


if __name__ == "__main__":
    main()
