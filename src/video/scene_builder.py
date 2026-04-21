"""
Scene Builder - Converts LessonPlan into Scene objects and MoviePy clips
"""

from typing import List

from moviepy.editor import ImageClip

from .scene_models import Scene, SceneType
from .slide_renderer import SlideRenderer
from .effects import apply_scene_transition, fade_out
from src.syllabus.topic_models import LessonPlan
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SceneBuilder:
    """Converts a LessonPlan into a sequence of Scenes, then into MoviePy clips."""

    def __init__(self):
        self.renderer = SlideRenderer()

    def build_scenes(self, lesson: LessonPlan) -> List[Scene]:
        """Convert a LessonPlan into an ordered list of Scenes."""
        scenes = []
        topic = lesson.topic
        common = {
            "part_number": topic.part,
            "total_parts": 200,
            "topic_category": topic.category,
        }

        # 1. Intro — warm welcome + hook to keep watching
        intro_prefix = (
            f"Namaste doston! Reasoning Mastery mein aapka swagat hai. "
            f"Yeh hai Part {topic.part} of 200. "
            f"Doston, yeh video aapke liye bahut important hai, toh please last tak zaroor dekhiye. "
            f"Maine is video ke end mein aur comment section mein kuch bahut important practice questions share kiye hain "
            f"jo aapke exam mein zaroor aayenge, toh video poora dekhiye aur comment section zaroor check kariye. "
            f"Chaliye shuru karte hain! ... "
        )
        scenes.append(Scene(
            scene_type=SceneType.INTRO_TITLE,
            title=topic.title,
            narration=intro_prefix + lesson.introduction,
            **common
        ))

        # 2. Concept explanation
        concept_lines = [s.strip() for s in lesson.concept_explanation.split(". ") if s.strip()]
        scenes.append(Scene(
            scene_type=SceneType.CONCEPT,
            title=topic.title,
            content_lines=concept_lines,
            section_label="CONCEPT",
            narration=lesson.concept_explanation,
            **common
        ))

        # 3. Formulas
        for fb in lesson.formulas:
            scenes.append(Scene(
                scene_type=SceneType.FORMULA,
                title=topic.title,
                highlight_text=fb.formula,
                formula_label=fb.visual_label,
                content_lines=[fb.explanation],
                narration=fb.explanation,
                **common
            ))

        # 4. Solved examples
        for i, ex in enumerate(lesson.solved_examples, 1):
            # Question slide
            scenes.append(Scene(
                scene_type=SceneType.EXAMPLE_QUESTION,
                title=topic.title,
                highlight_text=ex.question,
                step_number=i,
                narration=ex.question,
                **common
            ))

            # Step slides
            for j, step in enumerate(ex.steps, 1):
                scenes.append(Scene(
                    scene_type=SceneType.EXAMPLE_STEP,
                    title=topic.title,
                    content_lines=[step],
                    step_number=j,
                    total_steps=len(ex.steps),
                    narration=step,
                    **common
                ))

            # Answer slide
            scenes.append(Scene(
                scene_type=SceneType.EXAMPLE_ANSWER,
                title=topic.title,
                highlight_text=f"Answer: {ex.answer}",
                content_lines=[ex.explanation] if ex.explanation else [],
                narration=f"{ex.answer}. {ex.explanation}" if ex.explanation else ex.answer,
                **common
            ))

        # 5. Tips and tricks
        if lesson.tips_and_tricks:
            tips_narration = " ... ".join(lesson.tips_and_tricks)
            scenes.append(Scene(
                scene_type=SceneType.TIPS,
                title=topic.title,
                content_lines=lesson.tips_and_tricks,
                narration=tips_narration,
                **common
            ))

        # 6. Practice questions (show one at a time)
        for i, q in enumerate(lesson.practice_questions[:3], 1):  # Show max 3 in video
            scenes.append(Scene(
                scene_type=SceneType.PRACTICE,
                title=topic.title,
                highlight_text=f"Q{i}. {q.question}",
                options=q.options,
                correct_option=q.correct_answer,
                narration=f"Practice question number {i}. {q.question}. Iska answer pinned comment mein check kariye.",
                **common
            ))

        # 7. Summary
        if lesson.summary_points:
            summary_narration = " ... ".join(lesson.summary_points)
            scenes.append(Scene(
                scene_type=SceneType.SUMMARY,
                title=topic.title,
                content_lines=lesson.summary_points,
                narration=summary_narration,
                **common
            ))

        # 8. Outro — practice questions reminder + like/subscribe CTA
        next_part = f"Part {topic.part + 1}" if topic.part < 200 else "Series Complete!"
        outro_narration = (
            f"Toh doston, aaj ka topic yahan pe complete hota hai. "
            f"Umeed karta hoon aapko yeh video helpful lagi hogi. "
            f"Doston, maine comment section mein kuch bahut important practice questions share kiye hain "
            f"jo previous year exams mein baar baar puche gaye hain. "
            f"Please in questions ko zaroor solve kariye aur apna answer comment mein likhiye, "
            f"main aapko reply karunga ki sahi hai ya galat. "
            f"Agar yeh video aapko achhi lagi toh please like button dabayiye, "
            f"isse mujhe motivation milta hai aur aapke liye aur achhe videos banane mein madad hoti hai. "
            f"Aur agar aapne abhi tak channel subscribe nahi kiya hai toh abhi kariye "
            f"aur bell icon zaroor dabayiye taaki har nayi video ki notification aapko mil sake. "
            f"Yeh 200 parts ki complete series hai, ek bhi video mat miss kariye, "
            f"agar aapne poori series complete kar li toh exam mein reasoning section mein full marks pakke hain. "
            f"Apne doston ko bhi share kariye jinko isse fayda ho sakta hai. "
            f"Milte hain next video mein {next_part} ke saath. Tab tak practice karte rahiye! "
            f"Jai Hind!"
        )
        scenes.append(Scene(
            scene_type=SceneType.OUTRO,
            title=topic.title,
            content_lines=[next_part],
            narration=outro_narration,
            **common
        ))

        logger.info(f"Built {len(scenes)} scenes for Part {topic.part}")
        return scenes

    def scenes_to_clips(self, scenes: List[Scene], scene_durations: List[float]) -> List[ImageClip]:
        """Convert scenes to MoviePy ImageClips with transitions."""
        clips = []

        for i, (scene, duration) in enumerate(zip(scenes, scene_durations)):
            # Render the slide image
            img = self.renderer.render(scene)

            # Convert PIL Image to numpy array for MoviePy
            import numpy as np
            img_array = np.array(img)

            # Create ImageClip
            clip = ImageClip(img_array).set_duration(duration)

            # Apply transitions
            clip = apply_scene_transition(clip, scene.scene_type.value)

            # Fade out on last scene
            if i == len(scenes) - 1:
                clip = fade_out(clip, 1.0)

            clips.append(clip)

        return clips

    def estimate_durations(self, scenes: List[Scene], total_audio_duration: float) -> List[float]:
        """
        Estimate scene durations based on narration length proportionally to audio.
        Uses word count instead of char count for better accuracy with Hinglish text.
        Ensures minimum durations per scene type for readable slides.
        """
        # Minimum duration per scene type (seconds) — gives time to read the slide
        min_durations = {
            SceneType.INTRO_TITLE: 8.0,
            SceneType.CONCEPT: 10.0,
            SceneType.FORMULA: 8.0,
            SceneType.EXAMPLE_QUESTION: 6.0,
            SceneType.EXAMPLE_STEP: 5.0,
            SceneType.EXAMPLE_ANSWER: 6.0,
            SceneType.TIPS: 10.0,
            SceneType.PRACTICE: 6.0,
            SceneType.SUMMARY: 10.0,
            SceneType.OUTRO: 15.0,
        }

        # Use word count for better proportional estimation
        word_counts = []
        for scene in scenes:
            words = len(scene.narration.split()) if scene.narration else 0
            word_counts.append(max(words, 5))  # At least 5 words weight

        total_words = sum(word_counts)
        if total_words == 0:
            return [total_audio_duration / len(scenes)] * len(scenes)

        durations = []
        for scene, wc in zip(scenes, word_counts):
            # Proportional to word count
            ratio = wc / total_words
            dur = ratio * total_audio_duration
            # Apply minimum duration
            min_dur = min_durations.get(scene.scene_type, 4.0)
            dur = max(dur, min_dur)
            durations.append(dur)

        # Normalize to match total audio duration exactly
        total_est = sum(durations)
        if total_est > 0:
            scale = total_audio_duration / total_est
            durations = [d * scale for d in durations]

        return durations
