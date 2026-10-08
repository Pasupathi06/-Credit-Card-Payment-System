from decimal import Decimal, InvalidOperation

from django.db.models import Sum

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Card
from .serializers import CardSerializer
from admin_logs.models import AdminLog
from transactions.models import Transaction


class CardListCreateView(generics.ListCreateAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Card.objects.filter(
            user=self.request.user
        )


class CardDeleteView(generics.DestroyAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Card.objects.filter(
            user=self.request.user
        )


class AdminCardListView(generics.ListAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Card.objects.all().select_related("user")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        AdminLog.objects.create(
            admin=request.user,
            action="CARD_VIEW",
            description="Admin viewed all card details.",
            ip_address=self.get_client_ip(request),
        )

        return response

    @staticmethod
    def get_client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")


class AdminCardStatusUpdateView(generics.UpdateAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAdminUser]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Card.objects.all().select_related("user")

    def partial_update(self, request, *args, **kwargs):
        card = self.get_object()

        is_blocked = request.data.get("is_blocked")

        if isinstance(is_blocked, str):
            is_blocked = is_blocked.lower() == "true"

        if not isinstance(is_blocked, bool):
            return Response(
                {
                    "detail": "is_blocked must be true or false."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = card.is_blocked

        card.is_blocked = is_blocked
        card.save(update_fields=["is_blocked"])

        action = (
            "blocked"
            if is_blocked
            else "unblocked"
        )

        AdminLog.objects.create(
            admin=request.user,
            action="CARD_STATUS_UPDATE",
            description=(
                f"Admin {action} card "
                f"{card.card_type} ****{card.last4}."
            ),
            ip_address=self.get_client_ip(request),
        )

        return Response(
            {
                "message": f"Card {action} successfully.",
                "card_id": card.id,
                "masked_card_number": (
                    f"**** **** **** {card.last4}"
                ),
                "is_blocked": card.is_blocked,
                "previous_is_blocked": old_status,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def get_client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")


class AdminCardCreditLimitUpdateView(generics.UpdateAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAdminUser]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Card.objects.all().select_related("user")

    def partial_update(self, request, *args, **kwargs):
        card = self.get_object()

        credit_limit = request.data.get("credit_limit")

        if credit_limit is None:
            return Response(
                {
                    "detail": "credit_limit is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            credit_limit = Decimal(str(credit_limit))
        except (InvalidOperation, ValueError, TypeError):
            return Response(
                {
                    "detail": "credit_limit must be a valid number."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if credit_limit <= 0:
            return Response(
                {
                    "detail": "credit_limit must be greater than 0."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_credit_limit = card.credit_limit

        card.credit_limit = credit_limit
        card.save(update_fields=["credit_limit"])

        AdminLog.objects.create(
            admin=request.user,
            action="CREDIT_LIMIT_UPDATE",
            description=(
                f"Admin updated credit limit for "
                f"{card.card_type} ****{card.last4} "
                f"from {old_credit_limit} to {credit_limit}."
            ),
            ip_address=self.get_client_ip(request),
        )

        return Response(
            {
                "message": "Credit limit updated successfully.",
                "card_id": card.id,
                "masked_card_number": (
                    f"**** **** **** {card.last4}"
                ),
                "credit_limit": str(card.credit_limit),
                "previous_credit_limit": (
                    str(old_credit_limit)
                    if old_credit_limit is not None
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def get_client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")


class CardCreditSummaryView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Card.objects.filter(
            user=self.request.user
        )

    def retrieve(self, request, *args, **kwargs):
        card = self.get_object()

        credit_limit = card.credit_limit

        # Credit limit has not been assigned yet.
        if credit_limit is None:
            return Response(
                {
                    "card_id": card.id,
                    "masked_card_number": (
                        f"**** **** **** {card.last4}"
                    ),
                    "credit_limit": None,
                    "used_credit": "0.00",
                    "available_credit": None,
                    "available_credit_percentage": None,
                    "is_below_10_percent": False,
                    "message": (
                        "Credit limit has not been assigned "
                        "to this card."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # Calculate total successful spending for this card.
        successful_spending = (
            Transaction.objects.filter(
                card=card,
                status="SUCCESS",
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # Available credit = credit limit - successful spending.
        available_credit = (
            credit_limit - successful_spending
        )

        # Prevent negative available credit.
        if available_credit < Decimal("0.00"):
            available_credit = Decimal("0.00")

        # Calculate available credit percentage.
        available_percentage = (
            (available_credit / credit_limit)
            * Decimal("100")
        )

        available_percentage = (
            available_percentage.quantize(
                Decimal("0.01")
            )
        )

        return Response(
            {
                "card_id": card.id,
                "masked_card_number": (
                    f"**** **** **** {card.last4}"
                ),
                "credit_limit": str(credit_limit),
                "used_credit": str(successful_spending),
                "available_credit": str(
                    available_credit
                ),
                "available_credit_percentage": str(
                    available_percentage
                ),
                "is_below_10_percent": (
                    available_percentage
                    < Decimal("10.00")
                ),
            },
            status=status.HTTP_200_OK,
        )