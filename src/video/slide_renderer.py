"""
Slide Renderer - Renders individual scene images using Pillow
This is the core visual engine for the full-screen educational video UI.
"""

import os
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .scene_models import Scene, SceneType
from .visual_themes import Colors, Fonts, Layout
from src.utils.logger import get_logger

logger = get_logger(__name__)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 8:  # RGBA
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    rgb = hex_to_rgb(hex_color)
    return (*rgb, alpha)


class SlideRenderer:
    """Renders beautiful educational slides for each scene type."""

    def __init__(self):
        self.width = Layout.WIDTH
        self.height = Layout.HEIGHT
        self._font_cache = {}
        self._load_fonts()

    def _load_fonts(self):
        """Load fonts, trying system paths."""
        font_dirs = []

        # Windows font directories
        if os.name == 'nt':
            font_dirs.append("C:/Windows/Fonts")
            font_dirs.append(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))

        # Project fonts
        font_dirs.append("assets/fonts")

        self._font_dirs = font_dirs

    def _get_font(self, font_file: str, size: int) -> ImageFont.FreeTypeFont:
        """Get or create a font, with caching."""
        key = (font_file, size)
        if key in self._font_cache:
            return self._font_cache[key]

        for font_dir in self._font_dirs:
            path = os.path.join(font_dir, font_file)
            if os.path.exists(path):
                font = ImageFont.truetype(path, size)
                self._font_cache[key] = font
                return font

        # Fallback to default
        try:
            font = ImageFont.truetype(font_file, size)
            self._font_cache[key] = font
            return font
        except Exception:
            font = ImageFont.load_default()
            self._font_cache[key] = font
            return font

    @property
    def font_title(self):
        return self._get_font(Fonts.BOLD, Fonts.TITLE)

    @property
    def font_section(self):
        return self._get_font(Fonts.BOLD, Fonts.SECTION_LABEL)

    @property
    def font_body(self):
        return self._get_font(Fonts.REGULAR, Fonts.BODY)

    @property
    def font_body_small(self):
        return self._get_font(Fonts.REGULAR, Fonts.BODY_SMALL)

    @property
    def font_formula(self):
        return self._get_font(Fonts.BOLD, Fonts.FORMULA)

    @property
    def font_small(self):
        return self._get_font(Fonts.REGULAR, Fonts.SMALL)

    @property
    def font_tiny(self):
        return self._get_font(Fonts.REGULAR, Fonts.TINY)

    @property
    def font_badge(self):
        return self._get_font(Fonts.BOLD, Fonts.BADGE)

    @property
    def font_option(self):
        return self._get_font(Fonts.REGULAR, Fonts.OPTION)

    @property
    def font_step(self):
        return self._get_font(Fonts.BOLD, Fonts.STEP_NUMBER)

    def render(self, scene: Scene) -> Image.Image:
        """Render a scene to a PIL Image."""
        renderers = {
            SceneType.INTRO_TITLE: self._render_intro,
            SceneType.CONCEPT: self._render_concept,
            SceneType.FORMULA: self._render_formula,
            SceneType.EXAMPLE_QUESTION: self._render_example_question,
            SceneType.EXAMPLE_STEP: self._render_example_step,
            SceneType.EXAMPLE_ANSWER: self._render_example_answer,
            SceneType.TIPS: self._render_tips,
            SceneType.PRACTICE: self._render_practice,
            SceneType.SUMMARY: self._render_summary,
            SceneType.OUTRO: self._render_outro,
        }

        renderer = renderers.get(scene.scene_type, self._render_concept)
        img = renderer(scene)
        return img

    def _create_base(self, scene: Scene) -> Tuple[Image.Image, ImageDraw.Draw]:
        """Create base image with gradient background, glowing accents, top bar, and bottom bar."""
        img = Image.new("RGB", (self.width, self.height), hex_to_rgb(Colors.BG_PRIMARY))
        draw = ImageDraw.Draw(img)

        accent = Colors.get_accent(scene.topic_category)
        secondary = Colors.get_secondary(scene.topic_category)
        accent_rgb = hex_to_rgb(accent)

        # Gradient background — dark to slightly lighter
        for y in range(self.height):
            ratio = y / self.height
            r = int(10 + 8 * ratio)
            g = int(14 + 10 * ratio)
            b = int(26 + 14 * ratio)
            # Add subtle accent color tint
            r = min(255, r + int(accent_rgb[0] * 0.02 * (1 - ratio)))
            g = min(255, g + int(accent_rgb[1] * 0.02 * (1 - ratio)))
            b = min(255, b + int(accent_rgb[2] * 0.02 * (1 - ratio)))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Decorative glow circle — top right (subtle)
        glow_img = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.ellipse(
            [self.width - 250, -80, self.width + 80, 250],
            fill=(accent_rgb[0] // 8, accent_rgb[1] // 8, accent_rgb[2] // 8)
        )
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=60))
        # Blend glow with background
        from PIL import ImageChops
        img = ImageChops.add(img, glow_img)
        draw = ImageDraw.Draw(img)

        # Second glow — bottom left (smaller)
        glow_img2 = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        glow_draw2 = ImageDraw.Draw(glow_img2)
        glow_draw2.ellipse(
            [-100, self.height - 200, 200, self.height + 50],
            fill=(accent_rgb[0] // 10, accent_rgb[1] // 10, accent_rgb[2] // 10)
        )
        glow_img2 = glow_img2.filter(ImageFilter.GaussianBlur(radius=50))
        img = ImageChops.add(img, glow_img2)
        draw = ImageDraw.Draw(img)

        # Progress bar at very top — glowing accent
        progress_width = int(self.width * (scene.part_number / scene.total_parts))
        draw.rectangle(
            [0, 0, self.width, Layout.PROGRESS_BAR_HEIGHT],
            fill=hex_to_rgb(Colors.PROGRESS_BG)
        )
        if progress_width > 0:
            draw.rectangle(
                [0, 0, progress_width, Layout.PROGRESS_BAR_HEIGHT],
                fill=accent_rgb
            )
            # Glow effect on progress bar
            draw.rectangle(
                [0, Layout.PROGRESS_BAR_HEIGHT, progress_width, Layout.PROGRESS_BAR_HEIGHT + 2],
                fill=(accent_rgb[0] // 3, accent_rgb[1] // 3, accent_rgb[2] // 3)
            )

        # Top bar background — semi-transparent dark
        draw.rectangle(
            [0, Layout.PROGRESS_BAR_HEIGHT, self.width, Layout.TOP_BAR_HEIGHT],
            fill=hex_to_rgb(Colors.BG_SECONDARY)
        )

        # Series name (left) — with accent glow
        draw.text(
            (Layout.MARGIN_X, 12),
            "REASONING MASTERY",
            fill=accent_rgb,
            font=self.font_tiny
        )

        # Part badge (right) — vibrant with glow
        part_text = f"Part {scene.part_number}/{scene.total_parts}"
        badge_font = self.font_badge
        bbox = draw.textbbox((0, 0), part_text, font=badge_font)
        badge_w = bbox[2] - bbox[0] + 24
        badge_x = self.width - Layout.MARGIN_X - badge_w
        badge_y = 10

        # Badge glow background
        draw.rounded_rectangle(
            [badge_x - 2, badge_y - 2, badge_x + badge_w + 2, badge_y + 32],
            radius=16,
            fill=(accent_rgb[0] // 4, accent_rgb[1] // 4, accent_rgb[2] // 4)
        )
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + 28],
            radius=14,
            fill=accent_rgb
        )
        draw.text(
            (badge_x + 12, badge_y + 4),
            part_text,
            fill=hex_to_rgb(Colors.WHITE),
            font=badge_font
        )

        # Bottom bar — with gradient top edge
        draw.rectangle(
            [0, Layout.BOTTOM_BAR_Y, self.width, self.height],
            fill=hex_to_rgb(Colors.BG_SECONDARY)
        )
        # Gradient accent line at top of bottom bar
        for i in range(3):
            alpha = 1.0 - (i * 0.3)
            line_color = (
                int(accent_rgb[0] * alpha),
                int(accent_rgb[1] * alpha),
                int(accent_rgb[2] * alpha)
            )
            draw.rectangle(
                [0, Layout.BOTTOM_BAR_Y - i, self.width, Layout.BOTTOM_BAR_Y - i + 1],
                fill=line_color
            )

        # Category label (bottom left)
        category_text = scene.topic_category.replace("_", " ").upper()
        draw.text(
            (Layout.MARGIN_X, Layout.BOTTOM_BAR_Y + 18),
            category_text,
            fill=accent_rgb,
            font=self.font_tiny
        )

        # Exam tags (bottom right) — vibrant colored pills
        exam_tags = ["SSC", "BANKING", "UPSC", "RRB"]
        tag_colors = [Colors.VR_ACCENT, Colors.ORANGE, Colors.GREEN, Colors.YELLOW]
        tag_x = self.width - Layout.MARGIN_X
        for tag, tcolor in zip(reversed(exam_tags), reversed(tag_colors)):
            tag_bbox = draw.textbbox((0, 0), tag, font=self.font_tiny)
            tw = tag_bbox[2] - tag_bbox[0] + 16
            tag_x -= tw + 8
            tc_rgb = hex_to_rgb(tcolor)
            # Dark bg with colored border
            draw.rounded_rectangle(
                [tag_x, Layout.BOTTOM_BAR_Y + 14, tag_x + tw, Layout.BOTTOM_BAR_Y + 34],
                radius=8,
                fill=(tc_rgb[0] // 6, tc_rgb[1] // 6, tc_rgb[2] // 6),
                outline=tc_rgb,
                width=1
            )
            draw.text(
                (tag_x + 8, Layout.BOTTOM_BAR_Y + 16),
                tag,
                fill=tc_rgb,
                font=self.font_tiny
            )

        return img, draw

    def _draw_section_header(self, draw: ImageDraw.Draw, text: str,
                              y: int, accent: str) -> int:
        """Draw a section header with accent underline. Returns y after header."""
        draw.text(
            (Layout.MARGIN_X, y),
            text,
            fill=hex_to_rgb(accent),
            font=self.font_section
        )
        bbox = draw.textbbox((Layout.MARGIN_X, y), text, font=self.font_section)
        line_y = bbox[3] + 6
        draw.rectangle(
            [Layout.MARGIN_X, line_y, Layout.MARGIN_X + 80, line_y + 3],
            fill=hex_to_rgb(accent)
        )
        return line_y + 20

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont,
                    max_width: int) -> list:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = ""

        dummy_img = Image.new("RGB", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = dummy_draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def _draw_card(self, draw: ImageDraw.Draw, x: int, y: int,
                    w: int, h: int, fill: str = None,
                    border_color: str = None) -> None:
        """Draw a rounded rectangle card."""
        fill_color = hex_to_rgb(fill or Colors.BG_CARD)
        draw.rounded_rectangle(
            [x, y, x + w, y + h],
            radius=Layout.CARD_RADIUS,
            fill=fill_color
        )
        if border_color:
            draw.rounded_rectangle(
                [x, y, x + w, y + h],
                radius=Layout.CARD_RADIUS,
                outline=hex_to_rgb(border_color),
                width=2
            )

    # ===== SCENE RENDERERS =====

    def _render_intro(self, scene: Scene) -> Image.Image:
        """Render intro title slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        # Center area for title
        center_y = self.height // 2 - 60

        # Series subtitle
        draw.text(
            (self.width // 2, center_y - 60),
            "REASONING MASTERY",
            fill=hex_to_rgb(Colors.TEXT_SECONDARY),
            font=self.font_section,
            anchor="mm"
        )

        # Main topic title (wrapped)
        title_lines = self._wrap_text(scene.title, self.font_title, self.width - 200)
        y = center_y
        for line in title_lines:
            draw.text(
                (self.width // 2, y),
                line,
                fill=hex_to_rgb(Colors.WHITE),
                font=self.font_title,
                anchor="mm"
            )
            y += 55

        # Category badge
        cat_text = scene.topic_category.replace("_", " ").upper()
        bbox = draw.textbbox((0, 0), cat_text, font=self.font_small)
        bw = bbox[2] - bbox[0] + 30
        bx = (self.width - bw) // 2
        by = y + 20
        draw.rounded_rectangle(
            [bx, by, bx + bw, by + 32],
            radius=16,
            fill=hex_to_rgb(accent)
        )
        draw.text(
            (self.width // 2, by + 16),
            cat_text,
            fill=hex_to_rgb(Colors.WHITE),
            font=self.font_small,
            anchor="mm"
        )

        # Decorative lines
        line_y = center_y - 90
        draw.rectangle(
            [(self.width // 2 - 100), line_y, (self.width // 2 + 100), line_y + 2],
            fill=hex_to_rgb(accent)
        )

        return img

    def _render_concept(self, scene: Scene) -> Image.Image:
        """Render concept explanation slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        # Section header
        label = scene.section_label or "CONCEPT"
        y = self._draw_section_header(draw, label, Layout.SECTION_HEADER_Y, accent)

        # Topic title
        draw.text(
            (Layout.MARGIN_X, y),
            scene.title,
            fill=hex_to_rgb(Colors.WHITE),
            font=self.font_section
        )
        y += 40

        # Content text with wrapping
        max_width = Layout.CONTENT_WIDTH
        for line in scene.content_lines:
            wrapped = self._wrap_text(line, self.font_body_small, max_width)
            for wl in wrapped:
                if y > Layout.CONTENT_BOTTOM - 40:
                    break
                draw.text(
                    (Layout.MARGIN_X + 10, y),
                    wl,
                    fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                    font=self.font_body_small
                )
                y += 32
            y += 10  # gap between paragraphs

        # Left accent bar
        draw.rectangle(
            [Layout.MARGIN_X - 15, Layout.SECTION_HEADER_Y,
             Layout.MARGIN_X - 11, min(y, Layout.CONTENT_BOTTOM)],
            fill=hex_to_rgb(accent)
        )

        return img

    def _render_formula(self, scene: Scene) -> Image.Image:
        """Render formula display slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        # Section header
        y = self._draw_section_header(draw, "FORMULA", Layout.SECTION_HEADER_Y, accent)

        # Formula label
        if scene.formula_label:
            draw.text(
                (Layout.MARGIN_X + 10, y),
                scene.formula_label,
                fill=hex_to_rgb(Colors.TEXT_SECONDARY),
                font=self.font_small
            )
            y += 30

        # Formula box
        formula_text = scene.highlight_text
        formula_lines = self._wrap_text(formula_text, self.font_formula,
                                         Layout.CONTENT_WIDTH - 2 * Layout.FORMULA_BOX_PADDING - 40)

        box_h = len(formula_lines) * 48 + 2 * Layout.FORMULA_BOX_PADDING
        box_x = Layout.MARGIN_X + 20
        box_w = Layout.CONTENT_WIDTH - 40
        box_y = y + 10

        # Box with border
        self._draw_card(draw, box_x, box_y, box_w, box_h, Colors.BG_CARD, accent)

        # Left accent stripe on card
        draw.rectangle(
            [box_x, box_y + Layout.CARD_RADIUS,
             box_x + 5, box_y + box_h - Layout.CARD_RADIUS],
            fill=hex_to_rgb(accent)
        )

        # Formula text centered in box
        formula_y = box_y + Layout.FORMULA_BOX_PADDING
        for fl in formula_lines:
            draw.text(
                (self.width // 2, formula_y + 16),
                fl,
                fill=hex_to_rgb(Colors.WHITE),
                font=self.font_formula,
                anchor="mm"
            )
            formula_y += 48

        y = box_y + box_h + 30

        # Explanation below
        max_width = Layout.CONTENT_WIDTH - 20
        for line in scene.content_lines:
            wrapped = self._wrap_text(line, self.font_body_small, max_width)
            for wl in wrapped:
                if y > Layout.CONTENT_BOTTOM - 30:
                    break
                draw.text(
                    (Layout.MARGIN_X + 10, y),
                    wl,
                    fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                    font=self.font_body_small
                )
                y += 32

        return img

    def _render_example_question(self, scene: Scene) -> Image.Image:
        """Render solved example question slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        # Section header
        label = f"SOLVED EXAMPLE #{scene.step_number}" if scene.step_number else "SOLVED EXAMPLE"
        y = self._draw_section_header(draw, label, Layout.SECTION_HEADER_Y, accent)

        # Question in a card
        question_text = scene.highlight_text or (scene.content_lines[0] if scene.content_lines else "")
        q_lines = self._wrap_text(question_text, self.font_body, Layout.CONTENT_WIDTH - 80)
        card_h = len(q_lines) * 38 + 40

        self._draw_card(draw, Layout.MARGIN_X, y, Layout.CONTENT_WIDTH, card_h,
                         Colors.BG_CARD, accent)

        # "Q" badge
        draw.rounded_rectangle(
            [Layout.MARGIN_X + 15, y + 12, Layout.MARGIN_X + 45, y + 42],
            radius=6,
            fill=hex_to_rgb(accent)
        )
        draw.text(
            (Layout.MARGIN_X + 30, y + 27),
            "Q",
            fill=hex_to_rgb(Colors.WHITE),
            font=self.font_step,
            anchor="mm"
        )

        # Question text
        qy = y + 18
        for ql in q_lines:
            draw.text(
                (Layout.MARGIN_X + 60, qy),
                ql,
                fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                font=self.font_body
            )
            qy += 38

        y = y + card_h + 30

        # "Let's solve step by step" label
        draw.text(
            (self.width // 2, y + 10),
            "Let's solve this step by step...",
            fill=hex_to_rgb(Colors.TEXT_SECONDARY),
            font=self.font_body_small,
            anchor="mm"
        )

        return img

    def _render_example_step(self, scene: Scene) -> Image.Image:
        """Render a single step of solving an example."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        # Section header with step indicator
        label = f"STEP {scene.step_number} OF {scene.total_steps}"
        y = self._draw_section_header(draw, label, Layout.SECTION_HEADER_Y, accent)

        # Step circle
        circle_x = Layout.MARGIN_X + 30
        circle_y = y + 30
        r = Layout.STEP_CIRCLE_RADIUS

        draw.ellipse(
            [circle_x - r, circle_y - r, circle_x + r, circle_y + r],
            fill=hex_to_rgb(accent)
        )
        draw.text(
            (circle_x, circle_y),
            str(scene.step_number),
            fill=hex_to_rgb(Colors.WHITE),
            font=self.font_step,
            anchor="mm"
        )

        # Step content
        step_x = circle_x + r + 20
        step_y = circle_y - 12
        max_w = self.width - step_x - Layout.MARGIN_X

        for line in scene.content_lines:
            wrapped = self._wrap_text(line, self.font_body, max_w)
            for wl in wrapped:
                if step_y > Layout.CONTENT_BOTTOM - 40:
                    break
                draw.text(
                    (step_x, step_y),
                    wl,
                    fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                    font=self.font_body
                )
                step_y += 36
            step_y += 10

        # Step progress dots at bottom
        dots_y = Layout.CONTENT_BOTTOM - 20
        dots_start = self.width // 2 - (scene.total_steps * 20) // 2
        for i in range(1, scene.total_steps + 1):
            dot_x = dots_start + (i - 1) * 20
            color = accent if i <= scene.step_number else Colors.TEXT_DIM
            dot_r = 5 if i == scene.step_number else 4
            draw.ellipse(
                [dot_x - dot_r, dots_y - dot_r, dot_x + dot_r, dots_y + dot_r],
                fill=hex_to_rgb(color)
            )

        return img

    def _render_example_answer(self, scene: Scene) -> Image.Image:
        """Render the answer reveal slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        y = self._draw_section_header(draw, "ANSWER", Layout.SECTION_HEADER_Y, accent)

        # Answer in green highlight box
        answer_text = scene.highlight_text
        a_lines = self._wrap_text(answer_text, self.font_body, Layout.CONTENT_WIDTH - 100)
        card_h = len(a_lines) * 38 + 40

        self._draw_card(draw, Layout.MARGIN_X, y, Layout.CONTENT_WIDTH, card_h,
                         Colors.GREEN_DARK, Colors.GREEN)

        # Checkmark
        draw.text(
            (Layout.MARGIN_X + 30, y + card_h // 2),
            "\u2713",
            fill=hex_to_rgb(Colors.GREEN),
            font=self.font_title,
            anchor="mm"
        )

        # Answer text
        ay = y + 20
        for al in a_lines:
            draw.text(
                (Layout.MARGIN_X + 70, ay),
                al,
                fill=hex_to_rgb(Colors.WHITE),
                font=self.font_body
            )
            ay += 38

        y = y + card_h + 30

        # Explanation
        for line in scene.content_lines:
            wrapped = self._wrap_text(line, self.font_body_small, Layout.CONTENT_WIDTH - 20)
            for wl in wrapped:
                if y > Layout.CONTENT_BOTTOM - 30:
                    break
                draw.text(
                    (Layout.MARGIN_X + 10, y),
                    wl,
                    fill=hex_to_rgb(Colors.TEXT_SECONDARY),
                    font=self.font_body_small
                )
                y += 30

        return img

    def _render_tips(self, scene: Scene) -> Image.Image:
        """Render tips and tricks slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        y = self._draw_section_header(draw, "TIPS & TRICKS", Layout.SECTION_HEADER_Y, accent)
        y += 10

        for i, tip in enumerate(scene.content_lines):
            if y > Layout.CONTENT_BOTTOM - 60:
                break

            # Tip card
            tip_lines = self._wrap_text(tip, self.font_body_small,
                                         Layout.CONTENT_WIDTH - 80)
            card_h = len(tip_lines) * 28 + 24

            self._draw_card(draw, Layout.MARGIN_X + 10, y,
                            Layout.CONTENT_WIDTH - 20, card_h, Colors.BG_CARD)

            # Left accent stripe
            draw.rectangle(
                [Layout.MARGIN_X + 10, y + Layout.CARD_RADIUS,
                 Layout.MARGIN_X + 15, y + card_h - Layout.CARD_RADIUS],
                fill=hex_to_rgb(accent)
            )

            # Tip number
            draw.text(
                (Layout.MARGIN_X + 35, y + 12),
                f"{i + 1}.",
                fill=hex_to_rgb(accent),
                font=self.font_step
            )

            # Tip text
            ty = y + 12
            for tl in tip_lines:
                draw.text(
                    (Layout.MARGIN_X + 65, ty),
                    tl,
                    fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                    font=self.font_body_small
                )
                ty += 28

            y += card_h + 12

        return img

    def _render_practice(self, scene: Scene) -> Image.Image:
        """Render practice question with options."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        y = self._draw_section_header(draw, "PRACTICE QUESTION", Layout.SECTION_HEADER_Y, accent)

        # Question
        q_lines = self._wrap_text(scene.highlight_text, self.font_body,
                                   Layout.CONTENT_WIDTH - 40)
        for ql in q_lines:
            draw.text(
                (Layout.MARGIN_X + 10, y),
                ql,
                fill=hex_to_rgb(Colors.WHITE),
                font=self.font_body
            )
            y += 36
        y += 20

        # Options
        for opt in scene.options:
            if y > Layout.CONTENT_BOTTOM - 60:
                break

            opt_h = Layout.OPTION_HEIGHT
            self._draw_card(draw, Layout.MARGIN_X + 20, y,
                            Layout.CONTENT_WIDTH - 40, opt_h, Colors.BG_CARD)

            # Option letter circle
            letter = opt[0] if opt else ""
            draw.ellipse(
                [Layout.MARGIN_X + 35, y + 10,
                 Layout.MARGIN_X + 55, y + opt_h - 10],
                fill=hex_to_rgb(Colors.BG_CARD_LIGHT)
            )
            draw.text(
                (Layout.MARGIN_X + 45, y + opt_h // 2),
                letter,
                fill=hex_to_rgb(accent),
                font=self.font_step,
                anchor="mm"
            )

            # Option text
            opt_text = opt[3:].strip() if len(opt) > 3 else opt
            draw.text(
                (Layout.MARGIN_X + 75, y + 13),
                opt_text,
                fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                font=self.font_option
            )

            y += opt_h + Layout.OPTION_GAP

        return img

    def _render_summary(self, scene: Scene) -> Image.Image:
        """Render summary/key takeaways slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        y = self._draw_section_header(draw, "KEY TAKEAWAYS", Layout.SECTION_HEADER_Y, accent)
        y += 10

        for i, point in enumerate(scene.content_lines):
            if y > Layout.CONTENT_BOTTOM - 50:
                break

            p_lines = self._wrap_text(point, self.font_body_small,
                                       Layout.CONTENT_WIDTH - 80)

            # Checkmark circle
            cx = Layout.MARGIN_X + 25
            cy = y + 14
            draw.ellipse(
                [cx - 12, cy - 12, cx + 12, cy + 12],
                fill=hex_to_rgb(Colors.GREEN)
            )
            draw.text(
                (cx, cy),
                "\u2713",
                fill=hex_to_rgb(Colors.WHITE),
                font=self.font_tiny,
                anchor="mm"
            )

            # Point text
            py = y + 2
            for pl in p_lines:
                draw.text(
                    (Layout.MARGIN_X + 50, py),
                    pl,
                    fill=hex_to_rgb(Colors.TEXT_PRIMARY),
                    font=self.font_body_small
                )
                py += 28

            y = py + 14

        return img

    def _render_outro(self, scene: Scene) -> Image.Image:
        """Render outro/subscribe slide."""
        img, draw = self._create_base(scene)
        accent = Colors.get_accent(scene.topic_category)

        center_y = self.height // 2

        # "Thanks for watching" text
        draw.text(
            (self.width // 2, center_y - 60),
            "Thanks for watching!",
            fill=hex_to_rgb(Colors.WHITE),
            font=self.font_title,
            anchor="mm"
        )

        # Subscribe button
        btn_text = "SUBSCRIBE for Daily Lessons"
        bbox = draw.textbbox((0, 0), btn_text, font=self.font_section)
        btn_w = bbox[2] - bbox[0] + 40
        btn_h = 50
        btn_x = (self.width - btn_w) // 2
        btn_y = center_y + 10

        draw.rounded_rectangle(
            [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
            radius=25,
            fill=hex_to_rgb(Colors.RED)
        )
        draw.text(
            (self.width // 2, btn_y + btn_h // 2),
            btn_text,
            fill=hex_to_rgb(Colors.WHITE),
            font=self.font_section,
            anchor="mm"
        )

        # Next topic teaser
        if scene.content_lines:
            next_text = f"Next: {scene.content_lines[0]}"
            draw.text(
                (self.width // 2, btn_y + btn_h + 40),
                next_text,
                fill=hex_to_rgb(Colors.TEXT_SECONDARY),
                font=self.font_small,
                anchor="mm"
            )

        # Part progress
        draw.text(
            (self.width // 2, center_y - 110),
            f"Part {scene.part_number} of {scene.total_parts} Complete!",
            fill=hex_to_rgb(accent),
            font=self.font_small,
            anchor="mm"
        )

        return img
