from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


urlpatterns = [
    # ==========================================
    # Django Admin Panel
    # http://127.0.0.1:8000/admin/
    # ==========================================
    path(
        "admin/",
        admin.site.urls,
    ),

    # ==========================================
    # Authentication & User APIs
    # /api/auth/
    # ==========================================
    path(
        "api/auth/",
        include("users.urls"),
    ),

    # ==========================================
    # Credit Card APIs
    # /api/cards/
    # ==========================================
    path(
        "api/cards/",
        include("cards.urls"),
    ),

    # ==========================================
    # Transaction & Payment APIs
    # /api/transactions/
    # ==========================================
    path(
        "api/transactions/",
        include("transactions.urls"),
    ),

    # ==========================================
    # OpenAPI Schema
    # http://127.0.0.1:8000/api/schema/
    # ==========================================
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    # ==========================================
    # Swagger API Documentation
    # http://127.0.0.1:8000/swagger/
    # ==========================================
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
        ),
        name="swagger-ui",
    ),
]