from decimal import Decimal

from django.conf import settings
from django.db import models


class Card(models.Model):
    CARD_TYPES = [
        ("VISA", "Visa"),
        ("MASTERCARD", "MasterCard"),
        ("RUPAY", "RuPay"),
        ("AMEX", "American Express"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cards",
    )

    card_holder_name = models.CharField(max_length=100)

    # Only last 4 digits are stored.
    last4 = models.CharField(max_length=4)

    card_type = models.CharField(
        max_length=20,
        choices=CARD_TYPES,
    )

    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()

    # Credit limit assigned to the card.
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Card blocking status.
    is_blocked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.card_type} ****{self.last4}"

    @property
    def total_spent(self):
        """
        Calculate total successful transaction amount
        for this card.
        """
        from transactions.models import Transaction

        total = (
            Transaction.objects.filter(
                card=self,
                status="SUCCESS",
            ).aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        return total

    @property
    def available_credit(self):
        """
        Calculate remaining available credit.
        """
        if self.credit_limit is None:
            return None

        available = self.credit_limit - self.total_spent

        return max(available, Decimal("0.00"))

    @property
    def available_credit_percentage(self):
        """
        Calculate available credit percentage.

        Example:
        Credit limit = ₹10,000
        Available credit = ₹800
        Result = 8%
        """
        if not self.credit_limit or self.credit_limit <= 0:
            return None

        percentage = (
            self.available_credit / self.credit_limit
        ) * Decimal("100")

        return percentage