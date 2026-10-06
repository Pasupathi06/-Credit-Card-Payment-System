from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # Authentication & User APIs
    path("api/auth/", include("users.urls")),

    # Card APIs
    path("api/cards/", include("cards.urls")),

    # Transaction APIs
    path("api/transactions/", include("transactions.urls")),

    # API Schema
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    # Swagger UI
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]