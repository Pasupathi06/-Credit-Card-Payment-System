from django.conf import settings
from django.db import models


class AdminLog(models.Model):
    ACTION_CHOICES = [
        ("LOGIN", "Login"),
        ("USER_UPDATE", "User Update"),
        ("USER_DELETE", "User Delete"),
        ("CARD_VIEW", "Card View"),
        ("CARD_STATUS_UPDATE", "Card Status Update"),
        ("CREDIT_LIMIT_UPDATE", "Credit Limit Update"),
        ("TRANSACTION_VIEW", "Transaction View"),
        ("CSV_EXPORT", "CSV Export"),
        ("DASHBOARD_VIEW", "Dashboard View"),
        ("OTHER", "Other"),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_logs",
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
    )

    description = models.TextField(
        blank=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        admin_name = (
            self.admin.username
            if self.admin
            else "Unknown Admin"
        )

        return f"{admin_name} - {self.action}"