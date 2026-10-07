import datetime
import os

import pytest

from certificates.models import Certificate, Job
from certificates.tasks import _process_job


pytestmark = pytest.mark.django_db


def _make_job(n=2):
    job = Job.objects.create(total=n)
    for i in range(n):
        Certificate.objects.create(
            job=job,
            recipient_name=f"Recipient {i}",
            course_name="Advanced Django",
            issued_on=datetime.date(2025, 6, 1),
        )
    return job


def test_process_job_marks_completed_and_writes_files():
    job = _make_job(2)
    _process_job(job.id)

    job.refresh_from_db()
    assert job.status == Job.Status.COMPLETED
    assert job.succeeded == 2
    assert job.failed == 0
    assert job.started_at is not None
    assert job.finished_at is not None

    for cert in job.certificates.all():
        cert.refresh_from_db()
        assert cert.status == Certificate.Status.SUCCESS
        assert cert.pdf_file
        assert cert.png_file
        assert os.path.getsize(cert.pdf_file.path) > 500
        assert os.path.getsize(cert.png_file.path) > 5000