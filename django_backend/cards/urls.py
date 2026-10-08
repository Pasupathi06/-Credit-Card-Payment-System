from django.urls import path

from .views import (
    CardListCreateView,
    CardDeleteView,
    AdminCardListView,
    AdminCardStatusUpdateView,
    AdminCardCreditLimitUpdateView,
    CardCreditSummaryView,
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

    path(
        "admin/<int:pk>/status/",
        AdminCardStatusUpdateView.as_view(),
        name="admin-card-status-update",
    ),

    path(
        "admin/<int:pk>/credit-limit/",
        AdminCardCreditLimitUpdateView.as_view(),
        name="admin-card-credit-limit-update",
    ),

    path(
        "<int:pk>/credit-summary/",
        CardCreditSummaryView.as_view(),
        name="card-credit-summary",
    ),
]