from django.urls import path

from . import views_ui

app_name = "ui"

urlpatterns = [
    path("", views_ui.submit, name="submit"),
    path("jobs/", views_ui.job_list, name="job-list"),
    path("jobs/<uuid:job_id>/", views_ui.job_detail, name="job-detail"),
]