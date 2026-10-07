import logging
from concurrent.futures import ThreadPoolExecutor

from django.db import connection
from django.utils import timezone

from .models import Certificate, Job
from .renderers import render_certificate

log = logging.getLogger(__name__)

_EXECUTOR: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="certgen")
    return _EXECUTOR


def enqueue_job(job_id) -> None:
    """Submit a job to the background pool. Returns immediately."""
    _get_executor().submit(_process_job, job_id)


def _process_job(job_id) -> None:
    try:
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            log.warning("enqueue_job: job %s not found", job_id)
            return

        job.status = Job.Status.PROCESSING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

        for cert in job.certificates.all():
            _process_certificate(cert)

        succeeded = job.certificates.filter(status=Certificate.Status.SUCCESS).count()
        failed = job.certificates.filter(status=Certificate.Status.FAILED).count()

        job.succeeded = succeeded
        job.failed = failed
        job.finished_at = timezone.now()

        if failed == 0 and succeeded == job.total:
            job.status = Job.Status.COMPLETED
        elif succeeded == 0 and failed == job.total:
            job.status = Job.Status.FAILED
        else:
            job.status = Job.Status.PARTIAL

        job.save(update_fields=["status", "succeeded", "failed", "finished_at"])
    except Exception:
        log.exception("worker crashed processing job %s", job_id)
    finally:
        connection.close()


def _process_certificate(cert: Certificate) -> None:
    """Wrap rendering so one certificate's failure never affects siblings."""
    try:
        pdf_rel, png_rel = render_certificate(cert)
        cert.pdf_file.name = pdf_rel
        cert.png_file.name = png_rel
        cert.status = Certificate.Status.SUCCESS
        cert.error_message = None
    except Exception as exc:
        log.exception("certificate %s failed", cert.id)
        cert.status = Certificate.Status.FAILED
        cert.error_message = f"{type(exc).__name__}: {exc}"
        cert.pdf_file = None
        cert.png_file = None
    finally:
        cert.save()