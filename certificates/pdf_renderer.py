"""
PDF certificate renderer (reportlab).

Reads the design from template_config so the PDF and PNG
(Step 9) stay visually in sync.

Public API:
    render_pdf(cert, output_path) -> None   # raises on failure
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdf_canvas

from . import template_config as cfg


def _y_from_top(fraction: float) -> float:
    """Convert 'fraction from top' (0.0 = top) to reportlab Y (0.0 = bottom)."""
    return cfg.CANVAS_HEIGHT_PT * (1.0 - fraction)


def _draw_centered_text(
    c: pdf_canvas.Canvas,
    key: str,
    text: str,
) -> None:
    """Draw a centered line of text using the config for font/size/color/position."""
    font = cfg.PDF_FONTS[key]
    size = cfg.FONT_SIZES[key]
    color = cfg.hex_to_rgb(cfg.COLORS[key])
    y_top = cfg.LAYOUT_Y[key]

    c.setFont(font, size)
    c.setFillColorRGB(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    c.drawCentredString(
        cfg.CANVAS_WIDTH_PT / 2.0,
        _y_from_top(y_top),
        text,
    )


def _draw_borders(c: pdf_canvas.Canvas) -> None:
    """Draw outer and inner rectangles, inset as fractions of canvas width."""
    w = cfg.CANVAS_WIDTH_PT
    h = cfg.CANVAS_HEIGHT_PT

    # Outer
    inset = cfg.BORDER["outer_inset"] * w
    color = cfg.hex_to_rgb(cfg.COLORS["border_outer"])
    c.setStrokeColorRGB(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    c.setLineWidth(cfg.BORDER["outer_width"])
    c.rect(inset, inset, w - 2 * inset, h - 2 * inset, stroke=1, fill=0)

    # Inner
    inset = cfg.BORDER["inner_inset"] * w
    color = cfg.hex_to_rgb(cfg.COLORS["border_inner"])
    c.setStrokeColorRGB(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    c.setLineWidth(cfg.BORDER["inner_width"])
    c.rect(inset, inset, w - 2 * inset, h - 2 * inset, stroke=1, fill=0)


def _draw_background(c: pdf_canvas.Canvas) -> None:
    """Fill the entire page with the background color."""
    color = cfg.hex_to_rgb(cfg.COLORS["background"])
    c.setFillColorRGB(color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
    c.rect(0, 0, cfg.CANVAS_WIDTH_PT, cfg.CANVAS_HEIGHT_PT, stroke=0, fill=1)


def render_pdf(cert, output_path: str) -> None:
    """
    Draw a certificate PDF for `cert` to `output_path` (absolute).

    Raises on any failure — the caller (worker) handles isolation.
    """
    # A4 landscape matches our CANVAS_* dimensions (842 x 595 pt).
    # We assert here to catch a config drift early instead of shipping
    # a silently-mismatched PDF.
    page = landscape(A4)
    assert abs(page[0] - cfg.CANVAS_WIDTH_PT) < 1, \
        f"Config width {cfg.CANVAS_WIDTH_PT} != A4 landscape width {page[0]}"
    assert abs(page[1] - cfg.CANVAS_HEIGHT_PT) < 1, \
        f"Config height {cfg.CANVAS_HEIGHT_PT} != A4 landscape height {page[1]}"

    c = pdf_canvas.Canvas(output_path, pagesize=page)

    _draw_background(c)
    _draw_borders(c)

    # Static lines from config
    _draw_centered_text(c, "title",    cfg.TEXT["title"])
    _draw_centered_text(c, "subtitle", cfg.TEXT["subtitle"])

    # Recipient name (dynamic)
    _draw_centered_text(c, "recipient_name", cert.recipient_name)

    # Course label + name
    _draw_centered_text(c, "course_label", cfg.TEXT["course_label"])
    _draw_centered_text(c, "course_name",  cert.course_name)

    # Date line
    date_line = f'{cfg.TEXT["date_prefix"]} {cert.issued_on:%B %d, %Y}'
    _draw_centered_text(c, "date_text", date_line)

    # Footer
    _draw_centered_text(c, "footer_text", cfg.TEXT["footer"])

    c.showPage()
    c.save()