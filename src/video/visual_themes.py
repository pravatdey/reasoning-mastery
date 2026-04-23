"""
Visual Themes - Colors, typography, and layout constants for video rendering
"""


class Colors:
    """Color palette for the video UI — vibrant, modern edtech look"""

    # Background — rich dark with subtle blue/purple tint
    BG_PRIMARY = "#0A0E1A"
    BG_SECONDARY = "#0F1629"
    BG_CARD = "#151C30"
    BG_CARD_LIGHT = "#1C2540"
    BG_GRADIENT_TOP = "#0D1224"
    BG_GRADIENT_BOTTOM = "#0A1628"

    # Verbal Reasoning theme — vibrant cyan/blue
    VR_ACCENT = "#00D4FF"
    VR_SECONDARY = "#0099DD"
    VR_GRADIENT_START = "#001a33"
    VR_GLOW = "#00D4FF"
    VR_HIGHLIGHT = "#00FFE0"

    # Analytical Reasoning theme — vibrant purple/magenta
    AR_ACCENT = "#A855FF"
    AR_SECONDARY = "#8B2FE8"
    AR_GRADIENT_START = "#1a0033"
    AR_GLOW = "#A855FF"
    AR_HIGHLIGHT = "#E040FB"

    # Common
    WHITE = "#FFFFFF"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#C0CDE0"
    TEXT_DIM = "#8899AA"
    GREEN = "#10B981"
    GREEN_BRIGHT = "#34D399"
    GREEN_DARK = "#064E3B"
    RED = "#EF4444"
    RED_BRIGHT = "#FF6B6B"
    YELLOW = "#FBBF24"
    ORANGE = "#FB923C"
    PROGRESS_BG = "#1E2538"
    GOLD = "#FFD700"

    @staticmethod
    def get_accent(category: str) -> str:
        if "analytical" in category.lower():
            return Colors.AR_ACCENT
        return Colors.VR_ACCENT

    @staticmethod
    def get_secondary(category: str) -> str:
        if "analytical" in category.lower():
            return Colors.AR_SECONDARY
        return Colors.VR_SECONDARY

    @staticmethod
    def get_glow(category: str) -> str:
        if "analytical" in category.lower():
            return Colors.AR_GLOW
        return Colors.VR_GLOW


class Fonts:
    """Font configuration — large readable text for YouTube"""

    # Font sizes — optimized for 1920x1080 Full HD YouTube viewing
    # YouTube compresses heavily — use larger, bolder text for readability
    TITLE = 96
    SECTION_LABEL = 60
    BODY = 64
    BODY_SMALL = 56
    FORMULA = 72
    SMALL = 44
    TINY = 36
    OPTION = 56
    STEP_NUMBER = 52
    BADGE = 38

    # Font families (will use system fonts or custom)
    BOLD = "arialbd.ttf"
    REGULAR = "arial.ttf"
    MONO = "consola.ttf"


class Layout:
    """Layout constants for 1920x1080 Full HD video"""

    # Video dimensions
    WIDTH = 1920
    HEIGHT = 1080

    # Margins
    MARGIN_X = 90
    MARGIN_Y = 30
    CONTENT_PADDING = 50

    # Top bar
    TOP_BAR_HEIGHT = 70
    PROGRESS_BAR_HEIGHT = 6
    PROGRESS_BAR_Y = 0

    # Content area
    CONTENT_TOP = 100
    CONTENT_BOTTOM = 1000
    CONTENT_WIDTH = WIDTH - 2 * MARGIN_X

    # Bottom bar
    BOTTOM_BAR_Y = 1005
    BOTTOM_BAR_HEIGHT = 75

    # Card dimensions
    CARD_PADDING = 28
    CARD_RADIUS = 16

    # Section header
    SECTION_HEADER_Y = 110

    # Formula box
    FORMULA_BOX_PADDING = 32
    FORMULA_BOX_MARGIN_Y = 24

    # Step circle
    STEP_CIRCLE_RADIUS = 24

    # Option card
    OPTION_HEIGHT = 95
    OPTION_GAP = 24
