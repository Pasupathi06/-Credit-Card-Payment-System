from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_date
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from cards.models import Card
from .models import Transaction
from .serializers import TransactionSerializer, PaymentSyncSerializer


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Transaction.objects.filter(
            user=self.request.user
        ).select_related("card")

        status_value = self.request.query_params.get("status")
        amount = self.request.query_params.get("amount")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if status_value:
            queryset = queryset.filter(
                status=status_value.upper()
            )

        if amount:
            try:
                amount_value = Decimal(amount)
                queryset = queryset.filter(
                    amount=amount_value
                )
            except (InvalidOperation, ValueError):
                pass

        if date_from:
            parsed_date = parse_date(date_from)

            if parsed_date:
                queryset = queryset.filter(
                    created_at__date__gte=parsed_date
                )

        if date_to:
            parsed_date = parse_date(date_to)

            if parsed_date:
                queryset = queryset.filter(
                    created_at__date__lte=parsed_date
                )

        return queryset


class PaymentSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PaymentSyncSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Make sure the payment belongs to the logged-in user
        if data["user_id"] != request.user.id:
            return Response(
                {"detail": "User mismatch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        card = None

        if data.get("card_id"):
            card = Card.objects.filter(
                id=data["card_id"],
                user=request.user,
            ).first()

            if not card:
                return Response(
                    {"detail": "Card not found for this user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        transaction, created = Transaction.objects.update_or_create(
            payment_id=data["payment_id"],
            defaults={
                "user": request.user,
                "card": card,
                "amount": data["amount"],
                "status": data["status"],
                "description": data.get("description"),
            },
        )

        return Response(
            {
                "message": (
                    "Transaction created."
                    if created
                    else "Transaction updated."
                ),
                "transaction": TransactionSerializer(transaction).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )