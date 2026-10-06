from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import AdminLog


User = get_user_model()


class AdminLogModelTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="adminuser",
            email="adminuser@example.com",
            password="TestPass123!",
            is_staff=True,
            is_superuser=True,
        )

    def test_create_admin_log(self):
        log = AdminLog.objects.create(
            admin=self.admin,
            action="LOGIN",
            description="Admin logged in",
            ip_address="127.0.0.1",
        )

        self.assertEqual(log.admin, self.admin)
        self.assertEqual(log.action, "LOGIN")
        self.assertEqual(log.description, "Admin logged in")
        self.assertEqual(log.ip_address, "127.0.0.1")

    def test_admin_log_string_representation(self):
        log = AdminLog.objects.create(
            admin=self.admin,
            action="LOGIN",
            description="Admin logged in",
        )

        self.assertEqual(
            str(log),
            "adminuser - LOGIN"
        )

    def test_admin_log_without_admin(self):
        log = AdminLog.objects.create(
            admin=None,
            action="OTHER",
            description="System action",
        )

        self.assertIsNone(log.admin)

        self.assertEqual(
            str(log),
            "Unknown Admin - OTHER"
        )

    def test_admin_log_action_choices(self):
        log = AdminLog.objects.create(
            admin=self.admin,
            action="CSV_EXPORT",
            description="Transactions exported",
        )

        self.assertEqual(
            log.action,
            "CSV_EXPORT"
        )

    def test_admin_log_ordering(self):
        first_log = AdminLog.objects.create(
            admin=self.admin,
            action="LOGIN",
            description="First log",
        )

        second_log = AdminLog.objects.create(
            admin=self.admin,
            action="DASHBOARD_VIEW",
            description="Second log",
        )

        logs = list(AdminLog.objects.all())

        self.assertEqual(logs[0], second_log)
        self.assertEqual(logs[1], first_log)

    def test_admin_log_ip_address_can_be_null(self):
        log = AdminLog.objects.create(
            admin=self.admin,
            action="USER_UPDATE",
            description="User updated",
            ip_address=None,
        )

        self.assertIsNone(log.ip_address)

    def test_admin_log_description_can_be_blank(self):
        log = AdminLog.objects.create(
            admin=self.admin,
            action="CARD_VIEW",
            description="",
        )

        self.assertEqual(log.description, "")