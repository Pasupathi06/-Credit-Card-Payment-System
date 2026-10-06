from django.urls import path

from .views import (
    TransactionListView,
    AdminTransactionListView,
    PaymentSyncView,
    InternalPaymentSyncView,
    AdminTransactionCSVExportView,
    AdminDashboardSummaryView,
)


urlpatterns = [

    # ==========================================
    # User Transaction History
    # ==========================================

    path(
        "",
        TransactionListView.as_view(),
        name="transaction-list",
    ),

    # ==========================================
    # Admin - All Transactions
    # ==========================================

    path(
        "admin/",
        AdminTransactionListView.as_view(),
        name="admin-transaction-list",
    ),

    # ==========================================
    # Internal FastAPI -> Django Sync
    # ==========================================

    path(
        "internal-sync/",
        InternalPaymentSyncView.as_view(),
        name="internal-payment-sync",
    ),

    # ==========================================
    # User Payment Sync
    # ==========================================

    path(
        "sync/",
        PaymentSyncView.as_view(),
        name="payment-sync",
    ),

    # ==========================================
    # Admin - CSV Export
    # ==========================================

    path(
        "admin/export-csv/",
        AdminTransactionCSVExportView.as_view(),
        name="admin-transaction-export",
    ),

    # ==========================================
    # Admin - Dashboard
    # ==========================================

    path(
        "admin/dashboard/",
        AdminDashboardSummaryView.as_view(),
        name="admin-dashboard",
    ),
]