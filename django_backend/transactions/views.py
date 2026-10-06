import csv

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from cards.models import Card
from admin_logs.models import AdminLog

from .models import Transaction
from .serializers import (
    TransactionSerializer,
    PaymentSyncSerializer,
)


# ==========================================
# Transaction History + Filters
# ==========================================

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                "Filter transactions by status: "
                "PENDING, SUCCESS, or FAILED"
            ),
        ),
        OpenApiParameter(
            name="amount",
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            description="Filter transactions by exact amount",
        ),
        OpenApiParameter(
            name="date_from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description=(
                "Filter transactions from this date "
                "(YYYY-MM-DD)"
            ),
        ),
        OpenApiParameter(
            name="date_to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description=(
                "Filter transactions up to this date "
                "(YYYY-MM-DD)"
            ),
        ),
    ]
)
class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Transaction.objects
            .filter(user=self.request.user)
            .select_related("card")
        )

        # --------------------------------
        # Filter by status
        # --------------------------------

        status_value = self.request.query_params.get(
            "status"
        )

        if status_value:
            queryset = queryset.filter(
                status=status_value.upper()
            )

        # --------------------------------
        # Filter by exact amount
        # --------------------------------

        amount = self.request.query_params.get(
            "amount"
        )

        if amount:
            try:
                amount_value = Decimal(amount)

                queryset = queryset.filter(
                    amount=amount_value
                )

            except (InvalidOperation, ValueError):
                pass

        # --------------------------------
        # Filter from date
        # --------------------------------

        date_from = self.request.query_params.get(
            "date_from"
        )

        if date_from:
            parsed_date = parse_date(date_from)

            if parsed_date:
                queryset = queryset.filter(
                    created_at__date__gte=parsed_date
                )

        # --------------------------------
        # Filter to date
        # --------------------------------

        date_to = self.request.query_params.get(
            "date_to"
        )

        if date_to:
            parsed_date = parse_date(date_to)

            if parsed_date:
                queryset = queryset.filter(
                    created_at__date__lte=parsed_date
                )

        return queryset


# ==========================================
# ADMIN - All Transactions
# ==========================================

class AdminTransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):

        AdminLog.objects.create(
            admin=self.request.user,
            action="TRANSACTION_VIEW",
            description="Admin viewed all transactions.",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )

        return (
            Transaction.objects
            .select_related(
                "user",
                "card",
            )
            .order_by("-created_at")
        )


# ==========================================
# Payment Sync API
# ==========================================

@extend_schema(
    request=PaymentSyncSerializer,
    responses=TransactionSerializer,
)
class PaymentSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        serializer = PaymentSyncSerializer(
            data=request.data
        )

        # --------------------------------
        # Validate request data
        # --------------------------------

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # --------------------------------
        # Make sure payment belongs
        # to logged-in user
        # --------------------------------

        if data["user_id"] != request.user.id:
            return Response(
                {
                    "detail": "User mismatch."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        card = None

        # --------------------------------
        # Validate card ownership
        # --------------------------------

        if data.get("card_id"):

            card = Card.objects.filter(
                id=data["card_id"],
                user=request.user,
            ).first()

            if not card:
                return Response(
                    {
                        "detail": (
                            "Card not found for this user."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        # --------------------------------
        # Create or update transaction
        # --------------------------------

        transaction, created = (
            Transaction.objects.update_or_create(
                payment_id=data["payment_id"],
                defaults={
                    "user": request.user,
                    "card": card,
                    "amount": data["amount"],
                    "status": data["status"],
                    "description": data.get(
                        "description"
                    ),
                },
            )
        )

        # --------------------------------
        # Response
        # --------------------------------

        return Response(
            {
                "message": (
                    "Transaction created."
                    if created
                    else "Transaction updated."
                ),
                "transaction": TransactionSerializer(
                    transaction
                ).data,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


# ==========================================
# INTERNAL FastAPI -> Django Payment Sync
# ==========================================

class InternalPaymentSyncView(APIView):
    """
    Internal endpoint used by FastAPI to sync
    completed payments into Django transactions.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):

        # --------------------------------
        # Validate internal API key
        # --------------------------------

        internal_key = request.headers.get(
            "X-Internal-API-Key"
        )

        configured_key = getattr(
            settings,
            "INTERNAL_API_KEY",
            ""
        )

        if not internal_key:
            return Response(
                {
                    "detail": (
                        "Internal API key is required."
                    )
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not configured_key:
            return Response(
                {
                    "detail": (
                        "Internal API key is not configured."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if internal_key != configured_key:
            return Response(
                {
                    "detail": "Invalid internal API key."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # --------------------------------
        # Validate payment data
        # --------------------------------

        serializer = PaymentSyncSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # --------------------------------
        # Find user
        # --------------------------------

        User = get_user_model()

        user = User.objects.filter(
            id=data["user_id"]
        ).first()

        if not user:
            return Response(
                {
                    "detail": "User not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------
        # Validate card
        # --------------------------------

        card = None

        if data.get("card_id"):

            card = Card.objects.filter(
                id=data["card_id"],
                user=user,
            ).first()

            if not card:
                return Response(
                    {
                        "detail": (
                            "Card not found for this user."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        # --------------------------------
        # Create or update transaction
        # --------------------------------

        transaction, created = (
            Transaction.objects.update_or_create(
                payment_id=data["payment_id"],
                defaults={
                    "user": user,
                    "card": card,
                    "amount": data["amount"],
                    "status": data["status"],
                    "description": data.get(
                        "description"
                    ),
                },
            )
        )

        # --------------------------------
        # Response
        # --------------------------------

        return Response(
            {
                "message": (
                    "Transaction created."
                    if created
                    else "Transaction updated."
                ),
                "transaction": TransactionSerializer(
                    transaction
                ).data,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


# ==========================================
# Admin Transaction CSV Export
# ==========================================

class AdminTransactionCSVExportView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):

        # --------------------------------
        # Admin Log
        # --------------------------------

        AdminLog.objects.create(
            admin=request.user,
            action="CSV_EXPORT",
            description="Admin exported transactions as CSV.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        transactions = (
            Transaction.objects
            .select_related(
                "user",
                "card",
            )
            .order_by("-created_at")
        )

        response = HttpResponse(
            content_type="text/csv"
        )

        response["Content-Disposition"] = (
            'attachment; filename="transactions.csv"'
        )

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

        for transaction in transactions:

            writer.writerow([
                transaction.id,
                transaction.payment_id,
                transaction.user.username,
                transaction.user.email,
                (
                    transaction.card.last4
                    if transaction.card
                    else ""
                ),
                transaction.amount,
                transaction.status,
                transaction.description or "",
                transaction.created_at,
                transaction.updated_at,
            ])

        return response


# ==========================================
# Admin Dashboard Summary
# ==========================================

class AdminDashboardSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):

        # --------------------------------
        # Admin Log
        # --------------------------------

        AdminLog.objects.create(
            admin=request.user,
            action="DASHBOARD_VIEW",
            description="Admin viewed dashboard summary.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        User = get_user_model()

        # --------------------------------
        # Overall Summary
        # --------------------------------

        total_users = User.objects.count()

        total_cards = Card.objects.count()

        total_transactions = (
            Transaction.objects.count()
        )

        successful_payments = (
            Transaction.objects.filter(
                status="SUCCESS"
            ).count()
        )

        failed_payments = (
            Transaction.objects.filter(
                status="FAILED"
            ).count()
        )

        pending_payments = (
            Transaction.objects.filter(
                status="PENDING"
            ).count()
        )

        total_payment_amount = (
            Transaction.objects.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # --------------------------------
        # Daily Summary Date
        # --------------------------------

        requested_date = request.query_params.get(
            "date"
        )

        if requested_date:

            summary_date = parse_date(
                requested_date
            )

            if not summary_date:
                return Response(
                    {
                        "detail": (
                            "Invalid date format. "
                            "Use YYYY-MM-DD."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:

            summary_date = timezone.localdate()

        # --------------------------------
        # Daily Transactions
        # --------------------------------

        daily_transactions = (
            Transaction.objects.filter(
                created_at__date=summary_date
            )
        )

        daily_total_transactions = (
            daily_transactions.count()
        )

        daily_successful_payments = (
            daily_transactions.filter(
                status="SUCCESS"
            ).count()
        )

        daily_failed_payments = (
            daily_transactions.filter(
                status="FAILED"
            ).count()
        )

        daily_pending_payments = (
            daily_transactions.filter(
                status="PENDING"
            ).count()
        )

        daily_total_amount = (
            daily_transactions.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # --------------------------------
        # Dashboard Response
        # --------------------------------

        return Response(
            {
                "overall_summary": {
                    "total_users": total_users,
                    "total_cards": total_cards,
                    "total_transactions": (
                        total_transactions
                    ),
                    "successful_payments": (
                        successful_payments
                    ),
                    "failed_payments": (
                        failed_payments
                    ),
                    "pending_payments": (
                        pending_payments
                    ),
                    "total_payment_amount": (
                        str(total_payment_amount)
                    ),
                },
                "daily_summary": {
                    "date": str(summary_date),
                    "total_transactions": (
                        daily_total_transactions
                    ),
                    "successful_payments": (
                        daily_successful_payments
                    ),
                    "failed_payments": (
                        daily_failed_payments
                    ),
                    "pending_payments": (
                        daily_pending_payments
                    ),
                    "total_payment_amount": (
                        str(daily_total_amount)
                    ),
                },
            }
        )