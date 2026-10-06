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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.card_type} ****{self.last4}"