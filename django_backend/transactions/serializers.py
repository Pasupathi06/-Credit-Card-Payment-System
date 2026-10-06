from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    card_last4 = serializers.CharField(
        source="card.last4",
        read_only=True,
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "payment_id",
            "card",
            "card_last4",
            "amount",
            "status",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "payment_id",
            "card_last4",
            "created_at",
            "updated_at",
        ]


class PaymentSyncSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    card_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    status = serializers.ChoiceField(
        choices=["PENDING", "SUCCESS", "FAILED"],
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
