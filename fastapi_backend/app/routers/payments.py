import random
import requests

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


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=201,
)
def make_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
):
    # Step 1: Create payment with PENDING status
    payment = Payment(
        user_id=payment_data.user_id,
        card_id=payment_data.card_id,
        amount=payment_data.amount,
        description=payment_data.description,
        status="PENDING",
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Step 2: Simulate payment processing
    payment.status = random.choice(["SUCCESS", "FAILED"])

    db.commit()
    db.refresh(payment)

    # Step 3: Sync payment result to Django
    sync_payload = {
        "payment_id": payment.id,
        "user_id": payment.user_id,
        "card_id": payment.card_id,
        "amount": str(payment.amount),
        "status": payment.status,
        "description": payment.description,
    }

    try:
        sync_response = requests.post(
            settings.django_sync_url,
            json=sync_payload,
            headers={
                "X-Internal-API-Key": settings.internal_api_key
            },
            timeout=10,
        )

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Payment completed, but Django "
                    "transaction sync failed."
                ),
                "error": str(exc),
            },
        )

    # Step 4: Check Django sync response
    if sync_response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Payment completed, but Django "
                    "transaction sync failed."
                ),
                "django_status": sync_response.status_code,
                "django_response": sync_response.text,
            },
        )

    # Step 5: Return payment response
    return payment


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return payment