"""
Thumbnail Generator - Creates attractive YouTube thumbnails with teacher image
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .visual_themes import Colors, Fonts
from .slide_renderer import hex_to_rgb
from src.syllabus.topic_models import Topic
from src.utils.logger import get_logger

logger = get_logger(__name__)

TEACHER_IMAGE_PATH = "assets/Gemini_Generated_Image_y5mm01y5mm01y5mm.png"


class ThumbnailGenerator:
    """Generates eye-catching YouTube thumbnails with teacher image."""

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
                f"/usr/share/fonts/truetype/dejavu/{font_file}",
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
        """Generate a thumbnail with teacher image on right, text on left."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGB", (self.width, self.height), hex_to_rgb(Colors.BG_PRIMARY))
        draw = ImageDraw.Draw(img)

        accent = Colors.get_accent(topic.category)
        accent_rgb = hex_to_rgb(accent)
        secondary = Colors.get_secondary(topic.category)

        # Gradient background
        for y in range(self.height):
            ratio = y / self.height
            r = int(10 + 12 * ratio)
            g = int(14 + 16 * ratio)
            b = int(26 + 20 * ratio)
            r = min(255, r + int(accent_rgb[0] * 0.03 * (1 - ratio)))
            g = min(255, g + int(accent_rgb[1] * 0.03 * (1 - ratio)))
            b = min(255, b + int(accent_rgb[2] * 0.03 * (1 - ratio)))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Glow circle behind teacher area (right side)
        glow_img = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.ellipse(
            [self.width - 700, 50, self.width + 100, self.height - 50],
            fill=(accent_rgb[0] // 5, accent_rgb[1] // 5, accent_rgb[2] // 5)
        )
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=80))
        from PIL import ImageChops
        img = ImageChops.add(img, glow_img)
        draw = ImageDraw.Draw(img)

        # === LEFT SIDE: Text content (60% of width) ===
        text_area_width = int(self.width * 0.58)

        # Part number - top left, big and bold
        part_font = self._get_font(Fonts.BOLD, 100)
        draw.text(
            (80, 50),
            f"Part {topic.part}",
            fill=accent_rgb,
            font=part_font
        )
        of_font = self._get_font(Fonts.REGULAR, 50)
        bbox = draw.textbbox((80, 50), f"Part {topic.part}", font=part_font)
        draw.text(
            (bbox[2] + 10, 85),
            "/200",
            fill=hex_to_rgb(Colors.TEXT_SECONDARY),
            font=of_font
        )

        # Topic title - large, left-aligned, wrapped
        title_font = self._get_font(Fonts.BOLD, 78)
        words = topic.title.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=title_font)
            if bbox[2] - bbox[0] > text_area_width - 100:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        y = self.height // 2 - len(lines) * 50
        for line in lines:
            # Text shadow
            draw.text((83, y + 3), line,
                      fill=(0, 0, 0), font=title_font)
            draw.text((80, y), line,
                      fill=hex_to_rgb(Colors.WHITE), font=title_font)
            y += 90

        # Category badge
        cat_text = topic.category.replace("_", " ").upper()
        badge_font = self._get_font(Fonts.BOLD, 30)
        bbox = draw.textbbox((0, 0), cat_text, font=badge_font)
        bw = bbox[2] - bbox[0] + 40
        by = y + 25
        draw.rounded_rectangle(
            [80, by, 80 + bw, by + 48],
            radius=24,
            fill=accent_rgb
        )
        draw.text(
            (100, by + 8),
            cat_text,
            fill=hex_to_rgb(Colors.WHITE),
            font=badge_font
        )

        # Exam tags below category
        exam_tags = ["SSC", "BANKING", "UPSC", "RRB"]
        tag_font = self._get_font(Fonts.BOLD, 24)
        tag_x = 80
        tag_y = by + 65
        for tag in exam_tags:
            tag_bbox = draw.textbbox((0, 0), tag, font=tag_font)
            tw = tag_bbox[2] - tag_bbox[0] + 24
            draw.rounded_rectangle(
                [tag_x, tag_y, tag_x + tw, tag_y + 38],
                radius=10,
                fill=hex_to_rgb(Colors.BG_CARD),
                outline=hex_to_rgb(Colors.TEXT_DIM),
                width=1
            )
            draw.text(
                (tag_x + 12, tag_y + 6),
                tag,
                fill=hex_to_rgb(Colors.TEXT_SECONDARY),
                font=tag_font
            )
            tag_x += tw + 12

        # "Tips & Tricks Inside!" - bottom left
        cta_font = self._get_font(Fonts.BOLD, 36)
        draw.text(
            (80, self.height - 80),
            "Tips & Tricks Inside!",
            fill=hex_to_rgb(Colors.YELLOW),
            font=cta_font
        )

        # Bottom accent bar
        draw.rectangle(
            [0, self.height - 10, self.width, self.height],
            fill=accent_rgb
        )

        # === RIGHT SIDE: Teacher image (40% of width) ===
        try:
            teacher_img = Image.open(TEACHER_IMAGE_PATH)

            # Resize teacher image to fit right side
            target_h = self.height - 20
            aspect = teacher_img.width / teacher_img.height
            target_w = int(target_h * aspect)

            # Cap width to right side area
            max_w = int(self.width * 0.45)
            if target_w > max_w:
                target_w = max_w
                target_h = int(target_w / aspect)

            teacher_img = teacher_img.resize((target_w, target_h), Image.LANCZOS)

            # Position on right side
            paste_x = self.width - target_w - 20
            paste_y = self.height - target_h

            # If image has alpha channel, use it as mask
            if teacher_img.mode == 'RGBA':
                img.paste(teacher_img, (paste_x, paste_y), teacher_img)
            else:
                img.paste(teacher_img, (paste_x, paste_y))

            logger.info(f"Teacher image added to thumbnail: {target_w}x{target_h}")

        except Exception as e:
            logger.warning(f"Could not add teacher image: {e}")

        img.save(output_path, "PNG", quality=95)
        logger.info(f"Thumbnail generated: {output_path}")
        return output_path
