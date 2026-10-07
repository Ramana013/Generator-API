from django.contrib import admin

from .models import Certificate, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "total", "succeeded", "failed", "created_at")
    list_filter = ("status",)
    search_fields = ("id",)
    readonly_fields = ("id", "created_at", "started_at", "finished_at")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job",
        "recipient_name",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("recipient_name", "recipient_email")
    readonly_fields = ("id", "created_at", "updated_at")
