from django.test import TestCase
from django.contrib.auth import get_user_model


User = get_user_model()


class UserModelTests(TestCase):

    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="TestPass123!"
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("TestPass123!"))

    def test_password_is_hashed(self):
        user = User.objects.create_user(
            username="hashuser",
            email="hashuser@example.com",
            password="TestPass123!"
        )

        self.assertNotEqual(
            user.password,
            "TestPass123!"
        )

        self.assertTrue(
            user.check_password("TestPass123!")
        )

    def test_user_email_is_unique(self):
        User.objects.create_user(
            username="userone",
            email="same@example.com",
            password="TestPass123!"
        )

        with self.assertRaises(Exception):
            User.objects.create_user(
                username="usertwo",
                email="same@example.com",
                password="TestPass123!"
            )