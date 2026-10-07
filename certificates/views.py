import os

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import Certificate, Job
from .serializers import (
    JobCreateSerializer,
    JobStatusSerializer,
    # CertificateSerializer,
)


# ---------------------------------------------------------------
# GET  /api/jobs/     → list jobs (paginated)
# POST /api/jobs/     → create a bulk job
# ---------------------------------------------------------------
class JobListCreateView(ListCreateAPIView):
    queryset = Job.objects.all().prefetch_related("certificates")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return JobCreateSerializer
        return JobStatusSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()

        # Hand off to the background worker; returns immediately.
        from .tasks import enqueue_job
        enqueue_job(job.id)

        # Worker may have already updated rows in parallel; read a fresh
        # snapshot from the DB before serializing the response.
        job.refresh_from_db()
        job._prefetched_objects_cache = {}

        read = JobStatusSerializer(job, context={"request": request})

        headers = self.get_success_headers(read.data)
        return Response(read.data, status=status.HTTP_201_CREATED, headers=headers)


# ---------------------------------------------------------------
# GET /api/jobs/{uuid}/
# ---------------------------------------------------------------
class JobDetailView(RetrieveAPIView):
    queryset = Job.objects.all().prefetch_related("certificates")
    serializer_class = JobStatusSerializer
    lookup_field = "id"


# ---------------------------------------------------------------
# GET /api/jobs/{job_id}/certificates/{cert_id}/download/?format=pdf|png
# ---------------------------------------------------------------
class CertificateDownloadView(APIView):
    ALLOWED_FORMATS = {"pdf": "pdf_file", "png": "png_file"}

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="format",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=["pdf", "png"],
                default="pdf",
                description="Which file format to download.",
            ),
        ],
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            (200, "image/png"): OpenApiTypes.BINARY,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        description="Download a generated certificate as PDF or PNG.",
    )

    def get(self, request, job_id, cert_id):
        fmt = request.query_params.get("format", "pdf").lower()
        if fmt not in self.ALLOWED_FORMATS:
            return Response(
                {"detail": f"Invalid format. Use one of: {sorted(self.ALLOWED_FORMATS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cert = Certificate.objects.get(id=cert_id, job_id=job_id)
        except Certificate.DoesNotExist:
            raise Http404("Certificate not found for this job.")

        if cert.status == Certificate.Status.FAILED:
            return Response(
                {"detail": "Certificate generation failed.", "error": cert.error_message},
                status=status.HTTP_409_CONFLICT,
            )

        file_field = getattr(cert, self.ALLOWED_FORMATS[fmt])
        if not file_field:
            return Response(
                {"detail": f"{fmt.upper()} file is not available yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Safe download filename: "<recipient> - <course>.<ext>"
        safe_name = "".join(
            c for c in f"{cert.recipient_name} - {cert.course_name}"
            if c.isalnum() or c in " -_"
        ).strip() or "certificate"

        response = FileResponse(
            file_field.open("rb"),
            as_attachment=True,
            filename=f"{safe_name}.{fmt}",
        )
        return response