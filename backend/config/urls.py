from django.contrib import admin
from django.urls import include, path
from voting.views_health import health_check, system_status, readiness_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("voting.urls")),
    path("health/", health_check, name="health_check"),
    path("status/", system_status, name="system_status"),
    path("ready/", readiness_check, name="readiness_check"),
]