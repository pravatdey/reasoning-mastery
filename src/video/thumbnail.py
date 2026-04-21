"""
Thumbnail Generator - Creates highly attractive YouTube thumbnails
Professional Indian education channel style with bold colors and teacher image
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
    """Generates bold, attractive YouTube thumbnails."""

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
                f"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                f"assets/fonts/{font_file}",
                font_file,
            ]
            for p in paths:
                if os.path.exists(p):
                    self._font_cache[key] = ImageFont.truetype(p, size)
                    return self._font_cache[key]
            self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_outlined_text(self, draw, position, text, font, fill, outline_color=(0,0,0), outline_width=4):
        """Draw text with thick outline for bold visibility."""
        x, y = position
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx*dx + dy*dy <= outline_width*outline_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill)

    def generate(self, topic: Topic, output_path: str) -> str:
        """Generate a bold, attractive thumbnail."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        accent = Colors.get_accent(topic.category)
        accent_rgb = hex_to_rgb(accent)
        is_analytical = "analytical" in topic.category.lower()

        # === BOLD GRADIENT BACKGROUND ===
        for y in range(self.height):
            ratio = y / self.height
            if is_analytical:
                # Purple to dark gradient
                r = int(60 * (1 - ratio) + 8 * ratio)
                g = int(10 * (1 - ratio) + 5 * ratio)
                b = int(120 * (1 - ratio) + 30 * ratio)
            else:
                # Deep blue to dark gradient
                r = int(0 * (1 - ratio) + 5 * ratio)
                g = int(40 * (1 - ratio) + 10 * ratio)
                b = int(130 * (1 - ratio) + 35 * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # === BRIGHT DIAGONAL STRIPE (eye-catching) ===
        stripe_color = hex_to_rgb(Colors.YELLOW)
        # Top-left to bottom diagonal stripe
        for i in range(60):
            alpha = 1.0 - (i / 60)
            sc = tuple(int(c * alpha * 0.3) for c in stripe_color)
            draw.line([(0, i * 3), (i * 3, 0)], fill=sc, width=2)

        # === LARGE GLOW CIRCLES ===
        glow = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)

        # Big glow behind teacher
        glow_draw.ellipse(
            [self.width - 800, -100, self.width + 200, self.height + 100],
            fill=(accent_rgb[0] // 3, accent_rgb[1] // 3, accent_rgb[2] // 3)
        )
        # Small glow top-left
        glow_draw.ellipse(
            [-200, -200, 400, 400],
            fill=(accent_rgb[0] // 5, accent_rgb[1] // 5, accent_rgb[2] // 5)
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=100))
        from PIL import ImageChops
        img = ImageChops.add(img, glow)
        draw = ImageDraw.Draw(img)

        # === PART NUMBER — HUGE, TOP-LEFT with yellow accent ===
        part_font = self._get_font(Fonts.BOLD, 140)
        self._draw_outlined_text(
            draw, (60, 20),
            f"PART {topic.part}",
            part_font,
            fill=hex_to_rgb(Colors.YELLOW),
            outline_color=(0, 0, 0),
            outline_width=5
        )

        # "/200" next to part
        of_font = self._get_font(Fonts.BOLD, 60)
        bbox = draw.textbbox((60, 20), f"PART {topic.part}", font=part_font)
        self._draw_outlined_text(
            draw, (bbox[2] + 15, 80),
            "/200",
            of_font,
            fill=hex_to_rgb(Colors.WHITE),
            outline_width=3
        )

        # === TOPIC TITLE — HUGE WHITE BOLD TEXT ===
        title_font = self._get_font(Fonts.BOLD, 90)
        text_area_width = int(self.width * 0.55)

        words = topic.title.upper().split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=title_font)
            if bbox[2] - bbox[0] > text_area_width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        y = 280
        for line in lines:
            self._draw_outlined_text(
                draw, (70, y),
                line,
                title_font,
                fill=hex_to_rgb(Colors.WHITE),
                outline_color=(0, 0, 0),
                outline_width=5
            )
            y += 110

        # === CATEGORY BADGE — BRIGHT COLORED ===
        cat_text = topic.category.replace("_", " ").upper()
        badge_font = self._get_font(Fonts.BOLD, 36)
        bbox = draw.textbbox((0, 0), cat_text, font=badge_font)
        bw = bbox[2] - bbox[0] + 50
        by = y + 20

        # Badge with glow effect
        draw.rounded_rectangle(
            [65, by - 3, 65 + bw + 6, by + 58 + 3],
            radius=30,
            fill=(accent_rgb[0] // 2, accent_rgb[1] // 2, accent_rgb[2] // 2)
        )
        draw.rounded_rectangle(
            [68, by, 68 + bw, by + 55],
            radius=28,
            fill=accent_rgb
        )
        draw.text(
            (93, by + 8),
            cat_text,
            fill=hex_to_rgb(Colors.WHITE),
            font=badge_font
        )

        # === EXAM TAGS — COLORFUL ROW ===
        exam_data = [
            ("SSC", Colors.GREEN),
            ("BANKING", Colors.ORANGE),
            ("UPSC", Colors.VR_ACCENT),
            ("RRB", Colors.YELLOW),
        ]
        tag_font = self._get_font(Fonts.BOLD, 28)
        tag_x = 70
        tag_y = by + 75
        for tag_text, tag_color in exam_data:
            tc = hex_to_rgb(tag_color)
            tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
            tw = tag_bbox[2] - tag_bbox[0] + 30
            draw.rounded_rectangle(
                [tag_x, tag_y, tag_x + tw, tag_y + 42],
                radius=10,
                fill=(tc[0] // 4, tc[1] // 4, tc[2] // 4),
                outline=tc,
                width=2
            )
            draw.text(
                (tag_x + 15, tag_y + 6),
                tag_text,
                fill=tc,
                font=tag_font
            )
            tag_x += tw + 14

        # === BOTTOM BAR — BRIGHT YELLOW CTA ===
        bar_h = 80
        bar_y = self.height - bar_h
        draw.rectangle(
            [0, bar_y, self.width, self.height],
            fill=hex_to_rgb(Colors.YELLOW)
        )
        cta_font = self._get_font(Fonts.BOLD, 44)
        draw.text(
            (self.width // 2, bar_y + bar_h // 2),
            "TIPS & TRICKS  |  FORMULAS  |  SOLVED EXAMPLES",
            fill=(0, 0, 0),
            font=cta_font,
            anchor="mm"
        )

        # === RIGHT SIDE: TEACHER IMAGE ===
        try:
            teacher_img = Image.open(TEACHER_IMAGE_PATH)

            # Resize to fit right side
            target_h = self.height - bar_h - 30
            aspect = teacher_img.width / teacher_img.height
            target_w = int(target_h * aspect)

            max_w = int(self.width * 0.42)
            if target_w > max_w:
                target_w = max_w
                target_h = int(target_w / aspect)

            teacher_img = teacher_img.resize((target_w, target_h), Image.LANCZOS)

            paste_x = self.width - target_w - 30
            paste_y = bar_y - target_h

            if teacher_img.mode == 'RGBA':
                img.paste(teacher_img, (paste_x, paste_y), teacher_img)
            else:
                img.paste(teacher_img, (paste_x, paste_y))

            logger.info(f"Teacher image added: {target_w}x{target_h}")

        except Exception as e:
            logger.warning(f"Could not add teacher image: {e}")

        # === TOP-RIGHT CORNER BADGE: "FREE" ===
        free_font = self._get_font(Fonts.BOLD, 36)
        draw.rounded_rectangle(
            [self.width - 200, 20, self.width - 30, 75],
            radius=28,
            fill=hex_to_rgb(Colors.RED)
        )
        draw.text(
            (self.width - 115, 48),
            "FREE",
            fill=hex_to_rgb(Colors.WHITE),
            font=free_font,
            anchor="mm"
        )

        img.save(output_path, "PNG", quality=95)
        logger.info(f"Thumbnail generated: {output_path}")
        return output_path
