from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from cards.models import Card
from .models import Transaction


User = get_user_model()


class TransactionModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="transactionuser",
            email="transactionuser@example.com",
            password="TestPass123!"
        )

        self.card = Card.objects.create(
            user=self.user,
            card_holder_name="Transaction User",
            last4="4040",
            card_type="VISA",
            expiry_month=1,
            expiry_year=2030,
        )

    def test_create_transaction(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1001,
            amount=Decimal("5000.00"),
            status="SUCCESS",
            description="Test payment",
        )

        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.card, self.card)
        self.assertEqual(transaction.payment_id, 1001)
        self.assertEqual(transaction.amount, Decimal("5000.00"))
        self.assertEqual(transaction.status, "SUCCESS")
        self.assertEqual(transaction.description, "Test payment")

    def test_default_status_is_pending(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1002,
            amount=Decimal("2500.00"),
        )

        self.assertEqual(transaction.status, "PENDING")

    def test_transaction_string_representation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1003,
            amount=Decimal("1000.00"),
            status="SUCCESS",
        )

        self.assertEqual(
            str(transaction),
            f"Transaction #{transaction.id} - SUCCESS"
        )

    def test_transaction_belongs_to_user(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1004,
            amount=Decimal("3000.00"),
            status="FAILED",
        )

        self.assertEqual(self.user.transactions.count(), 1)
        self.assertEqual(
            self.user.transactions.first(),
            transaction
        )

    def test_transaction_ordering(self):
        first_transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1005,
            amount=Decimal("1000.00"),
            status="SUCCESS",
        )

        second_transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1006,
            amount=Decimal("2000.00"),
            status="FAILED",
        )

        transactions = list(Transaction.objects.all())

        self.assertEqual(transactions[0], second_transaction)
        self.assertEqual(transactions[1], first_transaction)

    def test_transaction_can_exist_without_card(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=None,
            payment_id=1007,
            amount=Decimal("1500.00"),
            status="PENDING",
        )

        self.assertIsNone(transaction.card)

    def test_payment_id_can_be_null(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=None,
            amount=Decimal("750.00"),
            status="PENDING",
        )

        self.assertIsNone(transaction.payment_id)

    def test_transaction_amount_decimal(self):
        transaction = Transaction.objects.create(
            user=self.user,
            card=self.card,
            payment_id=1008,
            amount=Decimal("12345.67"),
            status="SUCCESS",
        )

        self.assertEqual(
            transaction.amount,
            Decimal("12345.67")
        )