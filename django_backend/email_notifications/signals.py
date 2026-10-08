from django.db import transaction as db_transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from cards.models import Card
from transactions.models import Transaction

from .email_service import (
    send_card_blocked_email,
    send_high_value_transaction_email,
    send_low_credit_limit_email,
)


@receiver(pre_save, sender=Card)
def track_card_block_status(
    sender,
    instance,
    **kwargs,
):
    """
    Stores the previous blocked status before saving the card.
    """

    if not instance.pk:
        instance._was_blocked = False
        return

    try:
        previous_card = Card.objects.get(
            pk=instance.pk
        )

        instance._was_blocked = (
            previous_card.is_blocked
        )

    except Card.DoesNotExist:
        instance._was_blocked = False


@receiver(post_save, sender=Card)
def card_notification(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Sends an email only when the card changes
    from unblocked to blocked.
    """

    was_blocked = getattr(
        instance,
        "_was_blocked",
        False,
    )

    newly_blocked = (
        instance.is_blocked
        and not was_blocked
    )

    if newly_blocked:
        db_transaction.on_commit(
            lambda: send_card_blocked_email(instance)
        )


@receiver(post_save, sender=Transaction)
def transaction_notification(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Sends notification emails for successful transactions.
    """

    if instance.status != "SUCCESS":
        return

    # --------------------------------------------------------
    # HIGH VALUE TRANSACTION
    # --------------------------------------------------------

    if instance.amount > 5000:
        db_transaction.on_commit(
            lambda: send_high_value_transaction_email(
                instance
            )
        )

    # --------------------------------------------------------
    # LOW AVAILABLE CREDIT
    # --------------------------------------------------------

    if instance.card:
        percentage = (
            instance.card.available_credit_percentage
        )

        if (
            percentage is not None
            and percentage < 10
        ):
            db_transaction.on_commit(
                lambda: send_low_credit_limit_email(
                    instance.card
                )
            )