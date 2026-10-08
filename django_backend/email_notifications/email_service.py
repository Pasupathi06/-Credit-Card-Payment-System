import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


def send_notification_email(
    recipient,
    subject,
    message,
):
    """
    Common function used to send notification emails.
    """

    if not recipient:
        logger.warning(
            "Notification email skipped: recipient email is empty."
        )
        return False

    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

        return sent_count > 0

    except Exception:
        # Email failure should not break the payment/card operation.
        logger.exception(
            "Failed to send notification email."
        )
        return False


def send_high_value_transaction_email(transaction):
    """
    Sends an email when a successful transaction
    exceeds ₹5000.
    """

    if transaction.amount <= Decimal("5000.00"):
        return False

    user = transaction.user

    card_details = "N/A"

    if transaction.card:
        card_details = (
            f"{transaction.card.card_type} "
            f"****{transaction.card.last4}"
        )

    subject = (
        "Credit Card Alert - High Value Transaction"
    )

    message = f"""
Dear {user.username},

A high-value transaction has been detected on your credit card.

Transaction ID: {transaction.id}
Amount: ₹{transaction.amount}
Card: {card_details}
Status: {transaction.status}
Date: {transaction.created_at}

This transaction exceeds the ₹5000 notification threshold.

If you do not recognize this transaction, please contact
the appropriate support team immediately.

Regards,
Credit Card Payment System
""".strip()

    return send_notification_email(
        recipient=user.email,
        subject=subject,
        message=message,
    )


def send_card_blocked_email(card):
    """
    Sends an email when a card is blocked.
    """

    user = card.user

    subject = (
        "Credit Card Alert - Card Blocked"
    )

    message = f"""
Dear {user.username},

Your credit card has been blocked.

Card: {card.card_type} ****{card.last4}
Card Holder: {card.card_holder_name}

For your security, the full card number and CVV are never
included in notification emails.

If you did not request this action, please contact
the appropriate support team immediately.

Regards,
Credit Card Payment System
""".strip()

    return send_notification_email(
        recipient=user.email,
        subject=subject,
        message=message,
    )


def send_low_credit_limit_email(card):
    """
    Sends an email when available credit falls below 10%.
    """

    percentage = card.available_credit_percentage

    if percentage is None:
        return False

    if percentage >= Decimal("10"):
        return False

    user = card.user

    available_credit = card.available_credit

    subject = (
        "Credit Card Alert - Low Available Credit"
    )

    message = f"""
Dear {user.username},

Your available credit limit has fallen below 10%.

Card: {card.card_type} ****{card.last4}
Credit Limit: ₹{card.credit_limit}
Available Credit: ₹{available_credit}
Available Credit Percentage: {percentage:.2f}%

Please review your recent transactions and available credit.

Regards,
Credit Card Payment System
""".strip()

    return send_notification_email(
        recipient=user.email,
        subject=subject,
        message=message,
    )