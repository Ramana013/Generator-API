import datetime
import os

import pytest

from certificates.models import Certificate, Job
from certificates.tasks import _process_job


pytestmark = pytest.mark.django_db


def _completed_job():
    job = Job.objects.create(total=1)
    cert = Certificate.objects.create(
        job=job,
        recipient_name="Alice Smith",
        course_name="Advanced Django",
        issued_on=datetime.date(2025, 6, 1),
    )
    _process_job(job.id)
    cert.refresh_from_db()
    return job, cert


def test_files_exist_on_disk_and_are_non_empty():
    """Spec requirement: generated certificates retrievable."""
    job, cert = _completed_job()

    assert cert.pdf_file
    assert cert.png_file

    pdf_abs = cert.pdf_file.path
    png_abs = cert.png_file.path

    assert os.path.exists(pdf_abs)
    assert os.path.exists(png_abs)

    with open(pdf_abs, "rb") as f:
        assert f.read(4) == b"%PDF"

    with open(png_abs, "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_serializer_returns_urls(api_client):
    """The API response exposes pdf_url / png_url."""
    job, cert = _completed_job()

    resp = api_client.get(f"/api/jobs/{job.id}/")
    assert resp.status_code == 200
    body = resp.json()

    c = body["certificates"][0]
    assert c["status"] == "success"
    assert c["pdf_url"].startswith("http")
    assert c["pdf_url"].endswith(".pdf")
    assert c["png_url"].startswith("http")
    assert c["png_url"].endswith(".png")