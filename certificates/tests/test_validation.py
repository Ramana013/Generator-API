import pytest


pytestmark = pytest.mark.django_db


def _payload(recipients):
    return {
        "course_name": "Advanced Django",
        "issued_on": "2025-06-01",
        "recipients": recipients,
    }


def test_bad_email_reports_per_index_error(api_client):
    resp = api_client.post(
        "/api/jobs/",
        _payload([
            {"name": "Alice"},
            {"name": "Bob", "email": "not-an-email"},
            {"name": "Carol"},
        ]),
        format="json",
    )
    assert resp.status_code == 400
    errs = resp.json()["recipients"]

    # DRF returns errors only for failing indices (dict keyed by index).
    # Valid recipients are omitted entirely.
    assert "1" in errs
    assert "email" in errs["1"]
    assert "0" not in errs
    assert "2" not in errs

def test_blank_name_rejected(api_client):
    resp = api_client.post(
        "/api/jobs/", _payload([{"name": "   "}]), format="json"
    )
    assert resp.status_code == 400


def test_missing_required_fields(api_client):
    resp = api_client.post("/api/jobs/", {}, format="json")
    assert resp.status_code == 400
    body = resp.json()
    assert "course_name" in body
    assert "issued_on" in body
    assert "recipients" in body


def test_invalid_date(api_client):
    resp = api_client.post(
        "/api/jobs/",
        {"course_name": "X", "issued_on": "not-a-date", "recipients": [{"name": "A"}]},
        format="json",
    )
    assert resp.status_code == 400
    assert "issued_on" in resp.json()


def test_too_many_recipients_rejected(api_client):
    resp = api_client.post(
        "/api/jobs/",
        _payload([{"name": f"R{i}"} for i in range(501)]),
        format="json",
    )
    assert resp.status_code == 400
    assert "recipients" in resp.json()