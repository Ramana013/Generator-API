import pytest

from certificates.models import Job


pytestmark = pytest.mark.django_db(transaction=True)

def test_get_job_returns_nested_certificates(api_client, valid_payload, wait_for_job):
    create = api_client.post("/api/jobs/", valid_payload, format="json")
    job_id = create.json()["id"]

    job = Job.objects.get(id=job_id)
    wait_for_job(job, timeout=10.0)

    resp = api_client.get(f"/api/jobs/{job_id}/")
    assert resp.status_code == 200
    body = resp.json()

    assert body["id"] == job_id
    assert body["total"] == 2
    assert body["succeeded"] == 2
    assert body["failed"] == 0
    assert body["status"] == "completed"
    assert len(body["certificates"]) == 2

    for cert in body["certificates"]:
        assert cert["status"] == "success"
        assert cert["pdf_url"]
        assert cert["png_url"]


def test_get_unknown_job_returns_404(api_client):
    resp = api_client.get("/api/jobs/00000000-0000-0000-0000-000000000000/")
    assert resp.status_code == 404