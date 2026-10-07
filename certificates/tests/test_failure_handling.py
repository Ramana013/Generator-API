import datetime

import pytest

from certificates.models import Certificate, Job
from certificates.tasks import _process_job


pytestmark = pytest.mark.django_db


def test_one_failure_does_not_block_siblings(monkeypatch):
    """Core spec requirement: one failure must not prevent siblings."""
    job = Job.objects.create(total=3)
    for name in ("Alice", "BOOM", "Carol"):
        Certificate.objects.create(
            job=job,
            recipient_name=name,
            course_name="Advanced Django",
            issued_on=datetime.date(2025, 6, 1),
        )

    from certificates import tasks as tasks_mod
    real = tasks_mod.render_certificate

    def fake_render(cert):
        if cert.recipient_name == "BOOM":
            raise RuntimeError("simulated render failure")
        return real(cert)

    monkeypatch.setattr(tasks_mod, "render_certificate", fake_render)

    _process_job(job.id)

    job.refresh_from_db()
    assert job.status == Job.Status.PARTIAL
    assert job.succeeded == 2
    assert job.failed == 1

    by_name = {c.recipient_name: c for c in job.certificates.all()}
    assert by_name["Alice"].status == Certificate.Status.SUCCESS
    assert by_name["Carol"].status == Certificate.Status.SUCCESS
    assert by_name["BOOM"].status == Certificate.Status.FAILED
    assert "simulated render failure" in (by_name["BOOM"].error_message or "")
    assert not by_name["BOOM"].pdf_file


def test_all_failures_gives_failed_status(monkeypatch):
    job = Job.objects.create(total=2)
    for name in ("A", "B"):
        Certificate.objects.create(
            job=job,
            recipient_name=name,
            course_name="X",
            issued_on=datetime.date(2025, 6, 1),
        )

    from certificates import tasks as tasks_mod
    monkeypatch.setattr(
        tasks_mod,
        "render_certificate",
        lambda cert: (_ for _ in ()).throw(RuntimeError("nope")),
    )

    _process_job(job.id)

    job.refresh_from_db()
    assert job.status == Job.Status.FAILED
    assert job.succeeded == 0
    assert job.failed == 2