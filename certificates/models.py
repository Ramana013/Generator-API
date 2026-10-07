from django.db import models
import uuid

# Create your models here.
# ---------- upload_to callables ----------
def certificate_pdf_path(instance, filename):
    """media/certificates/<job_id>/<cert_id>.pdf"""
    return f"certificates/{instance.job_id}/{instance.id}.pdf"


def certificate_png_path(instance, filename):
    """media/certificates/<job_id>/<cert_id>.png"""
    return f"certificates/{instance.job_id}/{instance.id}.png"


# ---------- Job ----------
class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partially completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    total = models.PositiveIntegerField(default=0)
    succeeded = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.id} [{self.status}] {self.succeeded}/{self.total}"


# ---------- Certificate ----------
class Certificate(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="certificates"
    )

    # recipient / certificate content
    recipient_name = models.CharField(max_length=200)
    recipient_email = models.EmailField(blank=True)
    course_name = models.CharField(max_length=200)
    issued_on = models.DateField()

    # generation outcome
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    pdf_file = models.FileField(
        upload_to=certificate_pdf_path, null=True, blank=True
    )
    png_file = models.FileField(
        upload_to=certificate_png_path, null=True, blank=True
    )
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
        ]

    def __str__(self):
        return f"{self.recipient_name} [{self.status}]"