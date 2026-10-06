from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import Card


User = get_user_model()


class CardModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="carduser",
            email="carduser@example.com",
            password="TestPass123!"
        )

    def test_create_card(self):
        card = Card.objects.create(
            user=self.user,
            card_holder_name="Test User",
            last4="4040",
            card_type="VISA",
            expiry_month=1,
            expiry_year=2030,
        )

        self.assertEqual(card.user, self.user)
        self.assertEqual(card.card_holder_name, "Test User")
        self.assertEqual(card.last4, "4040")
        self.assertEqual(card.card_type, "VISA")
        self.assertEqual(card.expiry_month, 1)
        self.assertEqual(card.expiry_year, 2030)

    def test_card_string_representation(self):
        card = Card.objects.create(
            user=self.user,
            card_holder_name="Test User",
            last4="4040",
            card_type="VISA",
            expiry_month=1,
            expiry_year=2030,
        )

        self.assertEqual(
            str(card),
            "VISA ****4040"
        )

    def test_card_belongs_to_user(self):
        card = Card.objects.create(
            user=self.user,
            card_holder_name="Test User",
            last4="1234",
            card_type="MASTERCARD",
            expiry_month=12,
            expiry_year=2031,
        )

        self.assertEqual(
            self.user.cards.count(),
            1
        )

        self.assertEqual(
            self.user.cards.first(),
            card
        )

    def test_only_last_four_digits_are_stored(self):
        card = Card.objects.create(
            user=self.user,
            card_holder_name="Test User",
            last4="1111",
            card_type="VISA",
            expiry_month=6,
            expiry_year=2030,
        )

        self.assertEqual(len(card.last4), 4)
        self.assertNotIn(
            "4111111111111111",
            str(card.__dict__)
        )

    def test_card_ordering(self):
        first_card = Card.objects.create(
            user=self.user,
            card_holder_name="Test User",
            last4="1111",
            card_type="VISA",
            expiry_month=1,
            expiry_year=2030,
        )

        second_card = Card.objects.create(
            user=self.user,
            card_holder_name="Test User",
            last4="2222",
            card_type="RUPAY",
            expiry_month=2,
            expiry_year=2031,
        )

        cards = list(Card.objects.all())

        self.assertEqual(cards[0], second_card)
        self.assertEqual(cards[1], first_card)