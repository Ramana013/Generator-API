import pytest

from certificates.models import Certificate, Job


pytestmark = pytest.mark.django_db(transaction=True)

def test_create_job_returns_201_and_creates_rows(api_client, valid_payload):
    response = api_client.post("/api/jobs/", valid_payload, format="json")
    assert response.status_code == 201

    body = response.json()
    assert body["total"] == 2
    assert len(body["certificates"]) == 2

    assert Job.objects.count() == 1
    assert Certificate.objects.count() == 2

    job = Job.objects.first()
    assert job.total == 2
    assert {c.recipient_name for c in job.certificates.all()} == {
        "Alice Smith",
        "Bob Jones",
    }


def test_create_job_enqueues_worker(api_client, valid_payload, wait_for_job):
    """Regression test: if enqueue is missing, jobs stay pending forever."""
    response = api_client.post("/api/jobs/", valid_payload, format="json")
    assert response.status_code == 201

    job = Job.objects.get(id=response.json()["id"])
    job = wait_for_job(job, timeout=10.0)

    assert job.status in (Job.Status.COMPLETED, Job.Status.PARTIAL)
    assert job.succeeded + job.failed == job.total


def test_empty_recipients_rejected(api_client):
    payload = {"course_name": "X", "issued_on": "2025-06-01", "recipients": []}
    response = api_client.post("/api/jobs/", payload, format="json")
    assert response.status_code == 400
    assert "recipients" in response.json()