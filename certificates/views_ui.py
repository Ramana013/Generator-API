"""
Server-rendered UI views for non-technical users.

These views do NOT replace the API — they render HTML pages that use
the same underlying models and read from the same database.
"""

import json

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Certificate, Job
from .serializers import JobCreateSerializer
from .tasks import enqueue_job


@require_http_methods(["GET", "POST"])
def submit(request):
    """Landing page: form to submit a bulk certificate job."""
    if request.method == "POST":
        # The form posts JSON (pasted) or individual fields.
        recipients_raw = request.POST.get("recipients", "").strip()

        # Parse the recipients textarea. One recipient per line:
        #   Name <email>
        # or just:
        #   Name
        recipients = []
        parse_errors = []

        for i, line in enumerate(recipients_raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue

            name = line
            email = ""

            # Support "Name <email>" syntax
            if "<" in line and line.endswith(">"):
                name, _, rest = line.partition("<")
                email = rest.rstrip(">").strip()

            name = name.strip()
            if not name:
                parse_errors.append(f"Line {i}: name is empty.")
                continue

            recipients.append({"name": name, "email": email})

        payload = {
            "course_name": request.POST.get("course_name", "").strip(),
            "issued_on": request.POST.get("issued_on", "").strip(),
            "recipients": recipients,
        }

        # Reuse the API serializer for the same validation rules.
        serializer = JobCreateSerializer(data=payload)

        if parse_errors:
            for msg in parse_errors:
                messages.error(request, msg)

        if serializer.is_valid():
            job = serializer.save()
            enqueue_job(job.id)
            return redirect("ui:job-detail", job_id=job.id)

        # Show validation errors on the form
        for field, errs in serializer.errors.items():
            if isinstance(errs, dict):
                for idx, sub in errs.items():
                    for msg in (sub if isinstance(sub, list) else [sub]):
                        messages.error(
                            request, f"Recipient #{int(idx) + 1}: {msg}"
                        )
            else:
                for msg in (errs if isinstance(errs, list) else [errs]):
                    messages.error(request, f"{field}: {msg}")

    return render(request, "certificates/submit.html")


def job_detail(request, job_id):
    """Show a job's progress and per-recipient download buttons."""
    job = get_object_or_404(
        Job.objects.prefetch_related("certificates"), id=job_id
    )

    is_processing = job.status in (Job.Status.PENDING, Job.Status.PROCESSING)

    return render(
        request,
        "certificates/job_detail.html",
        {
            "job": job,
            "is_processing": is_processing,
        },
    )


def job_list(request):
    """List all jobs with links to detail pages."""
    jobs = Job.objects.all().prefetch_related("certificates")
    return render(request, "certificates/job_list.html", {"jobs": jobs})