"""
Shared fixtures for the certificates test suite.
"""

import time

import pytest
from rest_framework.test import APIClient

from certificates.models import Job


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def valid_payload():
    return {
        "course_name": "Advanced Django",
        "issued_on": "2025-06-01",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
        ],
    }


@pytest.fixture(autouse=True)
def media_root_tmp(tmp_path, settings):
    """Redirect MEDIA_ROOT to a temp dir for every test."""
    settings.MEDIA_ROOT = tmp_path
    yield tmp_path


def wait_until_done(job, timeout=5.0, interval=0.05):
    """Poll a job's status until it leaves pending/processing."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job.refresh_from_db()
        if job.status not in (Job.Status.PENDING, Job.Status.PROCESSING):
            return job
        time.sleep(interval)
    raise AssertionError(
        f"Job {job.id} did not finish within {timeout}s "
        f"(final status: {job.status})"
    )


@pytest.fixture
def wait_for_job():
    return wait_until_done