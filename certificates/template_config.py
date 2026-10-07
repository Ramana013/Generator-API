"""
Single source of truth for the certificate design.

Both the PDF renderer (reportlab) and the PNG renderer (Pillow)
read from this module so the two outputs stay visually in sync.

NOTHING here imports reportlab or Pillow — it's pure data + tiny helpers.
"""

# ------------------------------------------------------------------
# Canvas
# ------------------------------------------------------------------
# Base unit is PDF points (reportlab's native unit).
# A4 landscape in points: 842 x 595.
CANVAS_WIDTH_PT = 842
CANVAS_HEIGHT_PT = 595

# PNG is the same canvas at a higher resolution:
# PNG pixel size = PT * PNG_SCALE
PNG_SCALE = 2.0   # 2x → 1684 x 1190, crisp on normal screens


# ------------------------------------------------------------------
# Colors  (stored as hex; helper converts to RGB for reportlab)
# ------------------------------------------------------------------
COLORS = {
    "background": "#fdfaf3",   # warm off-white
    "border_outer": "#1a2b5c", # deep navy
    "border_inner": "#c9a227", # gold
    "title": "#1a2b5c",
    "subtitle": "#444444",
    "recipient_name": "#0d1b3e",
    "course_label": "#444444",
    "course_name": "#1a2b5c",
    "date_text": "#666666",
    "footer_text": "#888888",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """'#1a2b5c' -> (26, 43, 92) for reportlab."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------
# Fonts
# ------------------------------------------------------------------
# PDF: reportlab built-in fonts (no external files needed).
PDF_FONTS = {
    "title":          "Helvetica-Bold",
    "subtitle":       "Helvetica",
    "recipient_name": "Helvetica-Bold",
    "course_label":   "Helvetica",
    "course_name":    "Helvetica-Bold",
    "date_text":      "Helvetica",
    "footer_text":    "Helvetica-Oblique",
}

# PNG: preferred TTF paths in order; first existing wins.
# If none exist, the PNG renderer falls back to Pillow's default (tiny but works).
FONT_CANDIDATES = {
    "regular": [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
    "bold": [
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ],
}


# ------------------------------------------------------------------
# Font sizes  (in PDF points — the PNG renderer scales them by PNG_SCALE)
# ------------------------------------------------------------------
FONT_SIZES = {
    "title":          36,
    "subtitle":       16,
    "recipient_name": 44,
    "course_label":   16,
    "course_name":    22,
    "date_text":      14,
    "footer_text":    12,
}


# ------------------------------------------------------------------
# Layout — vertical anchor as a fraction of canvas HEIGHT, from TOP.
# 0.0 = top of page, 1.0 = bottom. Both renderers use these fractions.
# ------------------------------------------------------------------
LAYOUT_Y = {
    "title":          0.16,
    "subtitle":       0.34,
    "recipient_name": 0.46,
    "course_label":   0.62,
    "course_name":    0.70,
    "date_text":      0.83,
    "footer_text":    0.93,
}


# ------------------------------------------------------------------
# Borders — as fractions of canvas size, so scaling works for both.
# ------------------------------------------------------------------
BORDER = {
    "outer_inset":   0.03,  # from each edge, as fraction of width
    "outer_width":   3,     # in PDF points (PNG multiplies by PNG_SCALE)
    "inner_inset":   0.045,
    "inner_width":   1,
}


# ------------------------------------------------------------------
# Static text — the parts that never change per recipient.
# Dynamic values (recipient name, course, date) come from the model.
# ------------------------------------------------------------------
TEXT = {
    "title":            "CERTIFICATE OF COMPLETION",
    "subtitle":         "This is to certify that",
    "course_label":     "has successfully completed the course",
    "date_prefix":      "Issued on",
    "footer":           "Bulk Certificate Generator",
}