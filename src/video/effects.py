"""
Video animation effects using MoviePy
"""

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import numpy as np
from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip


def fade_in(clip, duration=0.5):
    """Apply fade-in effect to a clip."""
    return clip.crossfadein(duration)


def fade_out(clip, duration=0.5):
    """Apply fade-out effect to a clip."""
    return clip.crossfadeout(duration)


def slide_in_left(clip, duration=0.4):
    """Slide clip in from the left."""
    w = clip.size[0]

    def position(t):
        if t < duration:
            progress = t / duration
            # Ease-out cubic
            progress = 1 - (1 - progress) ** 3
            x = -w + w * progress
        else:
            x = 0
        return (x, 'center')

    return clip.set_position(position)


def slide_in_bottom(clip, duration=0.4):
    """Slide clip in from the bottom."""
    h = clip.size[1]

    def position(t):
        if t < duration:
            progress = t / duration
            progress = 1 - (1 - progress) ** 3
            y = h - h * progress
        else:
            y = 0
        return ('center', y)

    return clip.set_position(position)


def zoom_in(clip, start_scale=0.92, duration=0.5):
    """Subtle zoom-in effect using cropping to maintain output resolution."""
    w, h = clip.size

    def make_frame(t):
        if t < duration:
            progress = t / duration
            progress = 1 - (1 - progress) ** 2  # Ease-out quad
            scale = start_scale + (1 - start_scale) * progress
        else:
            scale = 1.0

        frame = clip.get_frame(t)

        if scale >= 1.0:
            return frame

        # Crop from center (zoom effect without changing output resolution)
        crop_w = int(w * scale)
        crop_h = int(h * scale)
        x1 = (w - crop_w) // 2
        y1 = (h - crop_h) // 2
        cropped = frame[y1:y1+crop_h, x1:x1+crop_w]

        # Resize back to original dimensions
        from PIL import Image
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    new_clip = VideoClip(make_frame, duration=clip.duration)
    new_clip = new_clip.set_duration(clip.duration)
    new_clip.size = [w, h]
    new_clip.fps = getattr(clip, 'fps', 30)
    return new_clip


def apply_scene_transition(clip, scene_type: str, duration: float = 0.4):
    """Apply appropriate transition based on scene type."""
    clip = fade_in(clip, min(duration, 0.5))

    if scene_type in ("intro_title", "outro"):
        clip = zoom_in(clip, start_scale=0.95, duration=0.6)
    elif scene_type in ("formula", "example_answer"):
        clip = zoom_in(clip, start_scale=0.97, duration=0.3)

    return clip
