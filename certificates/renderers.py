"""
Certificate rendering dispatcher.

PDF is real (pdf_renderer.render_pdf).
PNG is real (png_renderer.render_png).
Both share template_config as the single source of design truth.

The worker calls `render_certificate(cert)`, which returns
(relative_pdf_path, relative_png_path) under MEDIA_ROOT.
"""

import os

from django.conf import settings

from .pdf_renderer import render_pdf
from .png_renderer import render_png


def _abs(rel_path: str) -> str:
    return os.path.join(settings.MEDIA_ROOT, rel_path)


def _ensure_job_dir(job_id) -> None:
    os.makedirs(
        os.path.join(settings.MEDIA_ROOT, "certificates", str(job_id)),
        exist_ok=True,
    )


def render_certificate(cert):
    """
    Draw both formats for `cert` and return their MEDIA_ROOT-relative paths.
    Raises on failure — the worker isolates per-certificate errors.
    """
    _ensure_job_dir(cert.job_id)

    pdf_rel = os.path.join("certificates", str(cert.job_id), f"{cert.id}.pdf")
    png_rel = os.path.join("certificates", str(cert.job_id), f"{cert.id}.png")

    render_pdf(cert, _abs(pdf_rel))
    render_png(cert, _abs(png_rel))

    return pdf_rel, png_rel