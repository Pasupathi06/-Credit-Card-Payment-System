from datetime import datetime

from rest_framework import serializers

from .models import Card


class CardSerializer(serializers.ModelSerializer):
    card_number = serializers.CharField(
        write_only=True,
        min_length=13,
        max_length=19,
    )

    masked_card_number = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = Card
        fields = [
            "id",
            "card_holder_name",
            "card_number",
            "masked_card_number",
            "card_type",
            "expiry_month",
            "expiry_year",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "masked_card_number",
            "created_at",
        ]

    def validate_card_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "Card number must contain only digits."
            )

        if not 13 <= len(value) <= 19:
            raise serializers.ValidationError(
                "Card number must be between 13 and 19 digits."
            )

        return value

    def validate_expiry_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError(
                "Expiry month must be between 1 and 12."
            )

        return value

    def validate_expiry_year(self, value):
        current_year = datetime.now().year

        if value < current_year:
            raise serializers.ValidationError(
                "Card expiry year cannot be in the past."
            )

        return value

    def create(self, validated_data):
        card_number = validated_data.pop("card_number")

        # Store only the last 4 digits
        last4 = card_number[-4:]

        card = Card.objects.create(
            user=self.context["request"].user,
            last4=last4,
            **validated_data,
        )

        return card

    def get_masked_card_number(self, obj):
        return f"**** **** **** {obj.last4}"