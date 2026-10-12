import csv

from datetime import date
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
from .statement_service import generate_monthly_statement


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
            description="Filter transactions from this date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="date_to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Filter transactions up to this date (YYYY-MM-DD)",
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

        # Filter by status
        status_value = self.request.query_params.get("status")

        if status_value:
            queryset = queryset.filter(
                status=status_value.upper()
            )

        # Filter by exact amount
        amount = self.request.query_params.get("amount")

        if amount:
            try:
                amount_value = Decimal(amount)

                if amount_value.is_finite():
                    queryset = queryset.filter(
                        amount=amount_value
                    )

            except (InvalidOperation, ValueError):
                pass

        # Filter from date
        date_from = self.request.query_params.get("date_from")

        if date_from:
            parsed_date = parse_date(date_from)

            if parsed_date:
                queryset = queryset.filter(
                    created_at__date__gte=parsed_date
                )

        # Filter to date
        date_to = self.request.query_params.get("date_to")

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
            .select_related("user", "card")
            .order_by("-created_at")
        )


# ==========================================
# INTERNAL FastAPI -> Django Card Validation
# ==========================================

class InternalCardValidationView(APIView):
    """
    Internal endpoint used by FastAPI to validate a card
    before attempting a payment.

    Required header:
        X-Internal-API-Key

    Request body:
        {
            "user_id": 1,
            "card_id": 1,
            "amount": "100.00"
        }
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT},
        description=(
            "Internally validate card ownership, block status, "
            "expiry and available credit."
        ),
    )
    def post(self, request):

        # --------------------------------
        # Validate internal API key
        # --------------------------------

        provided_key = request.headers.get(
            "X-Internal-API-Key"
        )

        configured_key = getattr(
            settings,
            "INTERNAL_API_KEY",
            "",
        )

        if not configured_key:
            return Response(
                {
                    "detail": "Internal API key is not configured."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not provided_key or provided_key != configured_key:
            return Response(
                {
                    "detail": "Invalid internal API key."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # --------------------------------
        # Validate request data
        # --------------------------------

        try:
            user_id = int(request.data.get("user_id"))
            card_id = int(request.data.get("card_id"))

            amount = Decimal(
                str(request.data.get("amount"))
            )

        except (TypeError, ValueError, InvalidOperation):
            return Response(
                {
                    "detail": (
                        "Valid user_id, card_id and amount "
                        "are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            user_id <= 0
            or card_id <= 0
            or not amount.is_finite()
            or amount <= 0
        ):
            return Response(
                {
                    "detail": (
                        "IDs and amount must be positive, "
                        "and amount must be a valid number."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------
        # Validate card ownership
        # --------------------------------

        card = Card.objects.filter(
            id=card_id,
            user_id=user_id,
        ).first()

        if not card:
            return Response(
                {
                    "valid": False,
                    "detail": "Card not found for this user.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------
        # Check blocked card
        # --------------------------------

        if card.is_blocked:
            return Response(
                {
                    "valid": False,
                    "detail": "This card is blocked.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------
        # Check card expiry
        # --------------------------------

        today = date.today()

        if (
            card.expiry_year < today.year
            or (
                card.expiry_year == today.year
                and card.expiry_month < today.month
            )
        ):
            return Response(
                {
                    "valid": False,
                    "detail": "This card has expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------
        # Validate credit limit
        # --------------------------------

        if (
            card.credit_limit is None
            or card.credit_limit <= Decimal("0.00")
        ):
            return Response(
                {
                    "valid": False,
                    "detail": (
                        "A valid credit limit is not configured "
                        "for this card."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------
        # Calculate successful spending
        # --------------------------------

        spending_data = Transaction.objects.filter(
            card=card,
            status="SUCCESS",
        ).aggregate(
            total=Sum("amount")
        )

        total_spent = (
            spending_data["total"]
            or Decimal("0.00")
        )

        available_credit = (
            card.credit_limit - total_spent
        )

        # --------------------------------
        # Check available credit
        # --------------------------------

        if amount > available_credit:
            return Response(
                {
                    "valid": False,
                    "detail": "Insufficient available credit.",
                    "credit_limit": str(card.credit_limit),
                    "total_spent": str(total_spent),
                    "available_credit": str(
                        max(
                            available_credit,
                            Decimal("0.00"),
                        )
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------
        # Card validation successful
        # --------------------------------

        return Response(
            {
                "valid": True,
                "message": "Card validation successful.",
                "user_id": user_id,
                "card_id": card.id,
                "masked_card": (
                    f"**** **** **** {card.last4}"
                ),
                "amount": str(amount),
                "credit_limit": str(card.credit_limit),
                "total_spent": str(total_spent),
                "available_credit": str(available_credit),
            },
            status=status.HTTP_200_OK,
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

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Verify logged-in user
        if data["user_id"] != request.user.id:
            return Response(
                {"detail": "User mismatch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        card = None

        # Validate card ownership
        if data.get("card_id"):
            card = Card.objects.filter(
                id=data["card_id"],
                user=request.user,
            ).first()

            if not card:
                return Response(
                    {
                        "detail": "Card not found for this user."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Create or update transaction
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
    Internal endpoint used by FastAPI to sync payments
    into Django transactions.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):

        # Validate internal API key
        internal_key = request.headers.get(
            "X-Internal-API-Key"
        )

        configured_key = getattr(
            settings,
            "INTERNAL_API_KEY",
            "",
        )

        if not configured_key:
            return Response(
                {
                    "detail": "Internal API key is not configured."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not internal_key or internal_key != configured_key:
            return Response(
                {"detail": "Invalid internal API key."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate payment data
        serializer = PaymentSyncSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Find user
        User = get_user_model()

        user = User.objects.filter(
            id=data["user_id"]
        ).first()

        if not user:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate card ownership
        card = None

        if data.get("card_id"):
            card = Card.objects.filter(
                id=data["card_id"],
                user=user,
            ).first()

            if not card:
                return Response(
                    {
                        "detail": "Card not found for this user."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Create or update transaction
        transaction, created = Transaction.objects.update_or_create(
            payment_id=data["payment_id"],
            defaults={
                "user": user,
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

        # Admin log
        AdminLog.objects.create(
            admin=request.user,
            action="CSV_EXPORT",
            description="Admin exported transactions as CSV.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        transactions = (
            Transaction.objects
            .select_related("user", "card")
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

        # Admin log
        AdminLog.objects.create(
            admin=request.user,
            action="DASHBOARD_VIEW",
            description="Admin viewed dashboard summary.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        User = get_user_model()

        # Overall summary
        total_users = User.objects.count()
        total_cards = Card.objects.count()
        total_transactions = Transaction.objects.count()

        successful_payments = Transaction.objects.filter(
            status="SUCCESS"
        ).count()

        failed_payments = Transaction.objects.filter(
            status="FAILED"
        ).count()

        pending_payments = Transaction.objects.filter(
            status="PENDING"
        ).count()

        total_payment_amount = (
            Transaction.objects.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # Summary date
        requested_date = request.query_params.get("date")

        if requested_date:
            summary_date = parse_date(requested_date)

            if not summary_date:
                return Response(
                    {
                        "detail": (
                            "Invalid date format. Use YYYY-MM-DD."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            summary_date = timezone.localdate()

        # Daily transactions
        daily_transactions = Transaction.objects.filter(
            created_at__date=summary_date
        )

        daily_total_transactions = daily_transactions.count()

        daily_successful_payments = daily_transactions.filter(
            status="SUCCESS"
        ).count()

        daily_failed_payments = daily_transactions.filter(
            status="FAILED"
        ).count()

        daily_pending_payments = daily_transactions.filter(
            status="PENDING"
        ).count()

        daily_total_amount = (
            daily_transactions.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        return Response(
            {
                "overall_summary": {
                    "total_users": total_users,
                    "total_cards": total_cards,
                    "total_transactions": total_transactions,
                    "successful_payments": successful_payments,
                    "failed_payments": failed_payments,
                    "pending_payments": pending_payments,
                    "total_payment_amount": str(
                        total_payment_amount
                    ),
                },
                "daily_summary": {
                    "date": str(summary_date),
                    "total_transactions": daily_total_transactions,
                    "successful_payments": daily_successful_payments,
                    "failed_payments": daily_failed_payments,
                    "pending_payments": daily_pending_payments,
                    "total_payment_amount": str(
                        daily_total_amount
                    ),
                },
            }
        )


# ==========================================
# Monthly Statement PDF
# ==========================================

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="year",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Statement year. Example: 2026",
        ),
        OpenApiParameter(
            name="month",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Statement month. Value must be between 1 and 12.",
        ),
    ]
)
class MonthlyStatementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        # Get year and month
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response(
                {
                    "detail": "year and month are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate year and month
        try:
            year = int(year)
            month = int(month)

        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "Invalid year or month."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if year < 1:
            return Response(
                {
                    "detail": "Year must be greater than zero."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month < 1 or month > 12:
            return Response(
                {
                    "detail": "Month must be between 1 and 12."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate PDF statement
        return generate_monthly_statement(
            user=request.user,
            year=year,
            month=month,
        )