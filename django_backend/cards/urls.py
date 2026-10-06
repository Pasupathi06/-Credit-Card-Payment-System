from django.urls import path

from .views import (
    CardListCreateView,
    CardDeleteView,
    AdminCardListView,
)


urlpatterns = [
    path(
        "",
        CardListCreateView.as_view(),
        name="card-list-create",
    ),

    path(
        "<int:pk>/",
        CardDeleteView.as_view(),
        name="card-delete",
    ),

    path(
        "admin/",
        AdminCardListView.as_view(),
        name="admin-card-list",
    ),
]