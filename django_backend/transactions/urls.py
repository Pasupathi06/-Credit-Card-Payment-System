from django.urls import path

from .views import (
    TransactionListView,
    AdminTransactionListView,
    PaymentSyncView,
    InternalPaymentSyncView,
    InternalCardValidationView,
    AdminTransactionCSVExportView,
    AdminDashboardSummaryView,
    MonthlyStatementView,
)


app_name = "transactions"


urlpatterns = [
    # ==========================================
    # User - Transaction History
    # GET /api/transactions/
    # ==========================================
    path(
        "",
        TransactionListView.as_view(),
        name="transaction-list",
    ),

    # ==========================================
    # User - Monthly Statement PDF
    # GET /api/transactions/monthly-statement/
    # ==========================================
    path(
        "monthly-statement/",
        MonthlyStatementView.as_view(),
        name="monthly-statement",
    ),

    # ==========================================
    # Admin - All Transactions
    # GET /api/transactions/admin/
    # ==========================================
    path(
        "admin/",
        AdminTransactionListView.as_view(),
        name="admin-transaction-list",
    ),

    # ==========================================
    # Internal - FastAPI Card Validation
    # POST /api/transactions/internal-validate-card/
    # ==========================================
    path(
        "internal-validate-card/",
        InternalCardValidationView.as_view(),
        name="internal-card-validation",
    ),

    # ==========================================
    # Internal - FastAPI Payment Synchronization
    # POST /api/transactions/internal-sync/
    # ==========================================
    path(
        "internal-sync/",
        InternalPaymentSyncView.as_view(),
        name="internal-payment-sync",
    ),

    # ==========================================
    # Payment Synchronization
    # POST /api/transactions/sync/
    # ==========================================
    path(
        "sync/",
        PaymentSyncView.as_view(),
        name="payment-sync",
    ),

    # ==========================================
    # Admin - Export Transactions to CSV
    # GET /api/transactions/admin/export-csv/
    # ==========================================
    path(
        "admin/export-csv/",
        AdminTransactionCSVExportView.as_view(),
        name="admin-transaction-export",
    ),

    # ==========================================
    # Admin - Dashboard Summary
    # GET /api/transactions/admin/dashboard/
    # ==========================================
    path(
        "admin/dashboard/",
        AdminDashboardSummaryView.as_view(),
        name="admin-dashboard",
    ),
]