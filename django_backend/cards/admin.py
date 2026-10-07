from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "card_holder_name",
        "masked_card",
        "card_type",
        "expiry_month",
        "expiry_year",
        "created_at",
    )

    list_filter = (
        "card_type",
        "created_at",
    )

    search_fields = (
        "card_holder_name",
        "last4",
        "user__username",
        "user__email",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "last4",
        "created_at",
    )

    def masked_card(self, obj):
        return f"**** **** **** {obj.last4}"

    masked_card.short_description = "Card Number"