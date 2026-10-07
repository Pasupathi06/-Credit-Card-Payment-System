import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Transaction


@admin.action(description="Export selected transactions to CSV")
def export_transactions_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Transaction ID",
        "Payment ID",
        "Username",
        "Email",
        "Card Last 4",
        "Amount",
        "Status",
        "Description",
        "Created At",
        "Updated At",
    ])

    for transaction in queryset.select_related("user", "card"):
        writer.writerow([
            transaction.id,
            transaction.payment_id,
            transaction.user.username if transaction.user else "",
            transaction.user.email if transaction.user else "",
            transaction.card.last4 if transaction.card else "",
            transaction.amount,
            transaction.status,
            transaction.description or "",
            transaction.created_at,
            transaction.updated_at,
        ])

    return response


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment_id",
        "user",
        "card",
        "amount",
        "status",
        "description",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "payment_id",
        "user__username",
        "user__email",
        "description",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "payment_id",
        "created_at",
        "updated_at",
    )

    actions = (
        export_transactions_csv,
    )