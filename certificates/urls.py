from django.urls import path

from .views import (
    CertificateDownloadView,
    JobDetailView,
    JobListCreateView,
)

app_name = "certificates"

urlpatterns = [
    path("jobs/", JobListCreateView.as_view(), name="job-list-create"),
    path("jobs/<uuid:id>/", JobDetailView.as_view(), name="job-detail"),
    path(
        "download/<uuid:job_id>/<uuid:cert_id>/",
        CertificateDownloadView.as_view(),
        name="certificate-download",
    ),
]