from rest_framework import serializers

from .models import Certificate, Job


# ---------------------------------------------------------------
# INPUT — one recipient
# ---------------------------------------------------------------
class RecipientInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, trim_whitespace=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Recipient name cannot be blank.")
        return value.strip()


# ---------------------------------------------------------------
# INPUT — bulk job creation
# ---------------------------------------------------------------
class JobCreateSerializer(serializers.Serializer):
    course_name = serializers.CharField(max_length=200, trim_whitespace=True)
    issued_on = serializers.DateField()
    recipients = RecipientInputSerializer(many=True, allow_empty=False)

    MAX_RECIPIENTS = 500

    def validate_course_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Course name cannot be blank.")
        return value.strip()

    def validate_recipients(self, value):
        if len(value) > self.MAX_RECIPIENTS:
            raise serializers.ValidationError(
                f"A single job can contain at most {self.MAX_RECIPIENTS} recipients."
            )
        return value

    def create(self, validated_data):
        recipients = validated_data.pop("recipients")
        course_name = validated_data["course_name"]
        issued_on = validated_data["issued_on"]

        job = Job.objects.create(total=len(recipients))

        Certificate.objects.bulk_create(
            [
                Certificate(
                    job=job,
                    recipient_name=r["name"],
                    recipient_email=r.get("email", "") or "",
                    course_name=course_name,
                    issued_on=issued_on,
                )
                for r in recipients
            ]
        )
        return job


# ---------------------------------------------------------------
# OUTPUT — one certificate
# ---------------------------------------------------------------
class CertificateSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    png_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = (
            "id",
            "recipient_name",
            "recipient_email",
            "course_name",
            "issued_on",
            "status",
            "pdf_url",
            "png_url",
            "error_message",
            "created_at",
            "updated_at",
        )

    def _url(self, obj, field_name) -> str | None:
        f = getattr(obj, field_name)
        if not f:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(f.url) if request else f.url

    def get_pdf_url(self, obj) -> str | None:
        return self._url(obj, "pdf_file")

    def get_png_url(self, obj) -> str | None:
        return self._url(obj, "png_file")


# ---------------------------------------------------------------
# OUTPUT — job with certificates nested
# ---------------------------------------------------------------
class JobStatusSerializer(serializers.ModelSerializer):
    certificates = CertificateSerializer(many=True, read_only=True)

    class Meta:
        model = Job
        fields = (
            "id",
            "status",
            "total",
            "succeeded",
            "failed",
            "created_at",
            "started_at",
            "finished_at",
            "certificates",
        )