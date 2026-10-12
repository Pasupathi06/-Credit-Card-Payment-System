import requests

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.payment import Payment
from ..schemas.payment import PaymentCreate, PaymentResponse


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


def get_django_sync_url() -> str:
    """
    Return the configured Django payment-sync URL.

    Expected URL:
    http://127.0.0.1:8000/api/transactions/sync/
    """

    sync_url = settings.django_sync_url.strip().rstrip("/")

    if not sync_url.endswith("/sync"):
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Invalid Django sync URL configuration.",
                "expected_format": (
                    "http://127.0.0.1:8000/"
                    "api/transactions/sync/"
                ),
                "configured_url": sync_url,
            },
        )

    return sync_url + "/"


def validate_card_with_django(
    user_id: int,
    card_id: int,
    amount: Decimal,
) -> dict:
    """
    Ask Django to validate:
    - Card ownership
    - Blocked status
    - Expiry
    - Available credit
    """

    sync_url = get_django_sync_url()

    # Convert:
    # /api/transactions/sync/
    # into:
    # /api/transactions/internal-validate-card/
    validation_url = (
        sync_url.rsplit("/sync/", 1)[0]
        + "/internal-validate-card/"
    )

    validation_payload = {
        "user_id": user_id,
        "card_id": card_id,
        "amount": str(amount),
    }

    try:
        response = requests.post(
            validation_url,
            json=validation_payload,
            headers={
                "X-Internal-API-Key": settings.internal_api_key,
            },
            timeout=10,
        )

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Unable to contact Django for card validation."
                ),
                "error": str(exc),
            },
        ) from exc

    try:
        response_data = response.json()
    except ValueError:
        response_data = {
            "message": response.text,
        }

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Card validation failed. "
                    "Payment was not processed."
                ),
                "django_status_code": response.status_code,
                "django_response": response_data,
            },
        )

    if (
        not isinstance(response_data, dict)
        or response_data.get("valid") is not True
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Django did not confirm that the card is valid."
                ),
                "django_response": response_data,
            },
        )

    return response_data


def sync_payment_to_django(payment: Payment) -> None:
    """
    Send the saved FastAPI payment record to Django.
    """

    sync_url = get_django_sync_url()

    sync_payload = {
        "payment_id": payment.id,
        "user_id": payment.user_id,
        "card_id": payment.card_id,
        "amount": str(payment.amount),
        "status": payment.status,
        "description": payment.description,
    }

    try:
        response = requests.post(
            sync_url,
            json=sync_payload,
            headers={
                "X-Internal-API-Key": settings.internal_api_key,
            },
            timeout=10,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Payment was saved in FastAPI, but "
                    "Django transaction synchronization failed."
                ),
                "payment_id": payment.id,
                "payment_status": payment.status,
                "error": str(exc),
            },
        ) from exc


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=201,
)
def make_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
):
    """
    Validate the card using Django, create a payment record,
    and synchronize it with Django.

    This is a simulated payment application.
    No real bank or payment gateway is contacted.
    """

    # Step 1: Validate the amount.
    try:
        amount = Decimal(str(payment_data.amount))

    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment amount.",
        ) from exc

    if not amount.is_finite() or amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Payment amount must be greater than zero.",
        )

    # Step 2: Validate the card before creating the payment.
    validate_card_with_django(
        user_id=payment_data.user_id,
        card_id=payment_data.card_id,
        amount=amount,
    )

    # Step 3: Create the payment record.
    payment = Payment(
        user_id=payment_data.user_id,
        card_id=payment_data.card_id,
        amount=amount,
        description=payment_data.description,
        status="PENDING",
    )

    try:
        db.add(payment)
        db.commit()
        db.refresh(payment)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create the payment record.",
        ) from exc

    # Step 4: Synchronize the payment with Django.
    try:
        sync_payment_to_django(payment)

    except HTTPException:
        # The FastAPI record has already been committed.
        # Do not delete it or change its status automatically.
        raise

    # Step 5: Return the created payment.
    return payment


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a payment by its ID.
    """

    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    return payment