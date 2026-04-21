"""
Thumbnail Generator - Creates attractive YouTube thumbnails for reasoning topics
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .visual_themes import Colors, Fonts, Layout
from .slide_renderer import hex_to_rgb
from src.syllabus.topic_models import Topic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThumbnailGenerator:
    """Generates eye-catching YouTube thumbnails."""

    def __init__(self):
        self.width = 1920
        self.height = 1080
        self._font_cache = {}

    def _get_font(self, font_file: str, size: int) -> ImageFont.FreeTypeFont:
        key = (font_file, size)
        if key not in self._font_cache:
            import os
            paths = [
                f"C:/Windows/Fonts/{font_file}",
                f"assets/fonts/{font_file}",
                font_file,
            ]
            for p in paths:
                if os.path.exists(p):
                    self._font_cache[key] = ImageFont.truetype(p, size)
                    return self._font_cache[key]
            self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def generate(self, topic: Topic, output_path: str) -> str:
        """Generate a thumbnail for the given topic."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGB", (self.width, self.height), hex_to_rgb(Colors.BG_PRIMARY))
        draw = ImageDraw.Draw(img)

        accent = Colors.get_accent(topic.category)
        secondary = Colors.get_secondary(topic.category)

        # Gradient background effect
        for y in range(self.height):
            ratio = y / self.height
            r = int(11 * (1 - ratio) + 17 * ratio)
            g = int(14 * (1 - ratio) + 24 * ratio)
            b = int(23 * (1 - ratio) + 39 * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Large accent circle (decorative, top-right)
        draw.ellipse(
            [self.width - 300, -100, self.width + 100, 300],
            fill=hex_to_rgb(secondary)
        )

        # Part number - large, top-left
        part_font = self._get_font(Fonts.BOLD, 96)
        draw.text(
            (60, 40),
            f"Part {topic.part}",
            fill=hex_to_rgb(accent),
            font=part_font
        )

        # "/200" smaller
        of_font = self._get_font(Fonts.REGULAR, 48)
        bbox = draw.textbbox((60, 40), f"Part {topic.part}", font=part_font)
        draw.text(
            (bbox[2] + 10, 70),
            f"/200",
            fill=hex_to_rgb(Colors.TEXT_SECONDARY),
            font=of_font
        )

        # Topic title - large, centered
        title_font = self._get_font(Fonts.BOLD, 72)
        # Wrap title
        words = topic.title.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=title_font)
            if bbox[2] - bbox[0] > self.width - 140:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        y = self.height // 2 - len(lines) * 35
        for line in lines:
            # Text shadow
            draw.text((self.width // 2 + 3, y + 3), line,
                      fill=(0, 0, 0), font=title_font, anchor="mm")
            draw.text((self.width // 2, y), line,
                      fill=hex_to_rgb(Colors.WHITE), font=title_font, anchor="mm")
            y += 70

        # Category badge
        cat_text = topic.category.replace("_", " ").upper()
        badge_font = self._get_font(Fonts.BOLD, 24)
        bbox = draw.textbbox((0, 0), cat_text, font=badge_font)
        bw = bbox[2] - bbox[0] + 40
        bx = (self.width - bw) // 2
        by = y + 20
        draw.rounded_rectangle(
            [bx, by, bx + bw, by + 40],
            radius=20,
            fill=hex_to_rgb(accent)
        )
        draw.text(
            (self.width // 2, by + 20),
            cat_text,
            fill=hex_to_rgb(Colors.WHITE),
            font=badge_font,
            anchor="mm"
        )

        # "Tips & Tricks Inside!" text at bottom
        cta_font = self._get_font(Fonts.BOLD, 28)
        draw.text(
            (self.width // 2, self.height - 60),
            "Tips & Tricks Inside!",
            fill=hex_to_rgb(Colors.YELLOW),
            font=cta_font,
            anchor="mm"
        )

        # Bottom accent bar
        draw.rectangle(
            [0, self.height - 8, self.width, self.height],
            fill=hex_to_rgb(accent)
        )

        img.save(output_path, "PNG", quality=95)
        logger.info(f"Thumbnail generated: {output_path}")
        return output_path
