"""
PNG certificate renderer (Pillow).

Reads the design from template_config so the PDF (Step 8) and PNG
stay visually in sync.

Public API:
    render_png(cert, output_path) -> None   # raises on failure
"""

from PIL import Image, ImageDraw, ImageFont

from . import template_config as cfg


# ------------------------------------------------------------------
# Text element -> font weight for PNG (PDF has its own mapping).
# ------------------------------------------------------------------
_FONT_KIND = {
    "title":          "bold",
    "subtitle":       "regular",
    "recipient_name": "bold",
    "course_label":   "regular",
    "course_name":    "bold",
    "date_text":      "regular",
    "footer_text":    "regular",
}


# ------------------------------------------------------------------
# Canvas size in pixels
# ------------------------------------------------------------------
def _canvas_size() -> tuple[int, int]:
    return (
        int(cfg.CANVAS_WIDTH_PT * cfg.PNG_SCALE),
        int(cfg.CANVAS_HEIGHT_PT * cfg.PNG_SCALE),
    )


# ------------------------------------------------------------------
# Font loading with cache
# ------------------------------------------------------------------
_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _load_font(kind: str, size_pt: int) -> ImageFont.FreeTypeFont:
    """Return a cached Pillow font for the given kind/size."""
    size_px = max(1, round(size_pt * cfg.PNG_SCALE))
    key = (kind, size_px)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    font = None
    for path in cfg.FONT_CANDIDATES.get(kind, []):
        try:
            font = ImageFont.truetype(path, size_px)
            break
        except OSError:
            continue

    if font is None:
        # Fallback: Pillow's default bitmap font. Tiny, but never crashes.
        font = ImageFont.load_default()

    _FONT_CACHE[key] = font
    return font


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _draw_background(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    draw.rectangle([0, 0, w, h], fill=cfg.COLORS["background"])


def _draw_borders(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    # Outer
    inset = int(cfg.BORDER["outer_inset"] * w)
    draw.rectangle(
        [inset, inset, w - inset, h - inset],
        outline=cfg.COLORS["border_outer"],
        width=max(1, round(cfg.BORDER["outer_width"] * cfg.PNG_SCALE)),
    )

    # Inner
    inset = int(cfg.BORDER["inner_inset"] * w)
    draw.rectangle(
        [inset, inset, w - inset, h - inset],
        outline=cfg.COLORS["border_inner"],
        width=max(1, round(cfg.BORDER["inner_width"] * cfg.PNG_SCALE)),
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw, w: int, h: int, key: str, text: str
) -> None:
    font = _load_font(_FONT_KIND[key], cfg.FONT_SIZES[key])

    # Measure text width so we can center it.
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]

    x = (w - text_w) / 2
    y = h * cfg.LAYOUT_Y[key]   # top anchor (fraction from top)

    draw.text((x, y), text, fill=cfg.COLORS[key], font=font)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
def render_png(cert, output_path: str) -> None:
    """
    Draw the certificate as a PNG and write it to `output_path` (absolute).
    Raises on failure — the caller (worker) handles isolation.
    """
    w, h = _canvas_size()
    img = Image.new("RGB", (w, h), cfg.COLORS["background"])
    draw = ImageDraw.Draw(img)

    _draw_borders(draw, w, h)

    _draw_centered_text(draw, w, h, "title",    cfg.TEXT["title"])
    _draw_centered_text(draw, w, h, "subtitle", cfg.TEXT["subtitle"])
    _draw_centered_text(draw, w, h, "recipient_name", cert.recipient_name)
    _draw_centered_text(draw, w, h, "course_label", cfg.TEXT["course_label"])
    _draw_centered_text(draw, w, h, "course_name",  cert.course_name)

    date_line = f'{cfg.TEXT["date_prefix"]} {cert.issued_on:%B %d, %Y}'
    _draw_centered_text(draw, w, h, "date_text", date_line)
    _draw_centered_text(draw, w, h, "footer_text", cfg.TEXT["footer"])

    img.save(output_path, format="PNG")