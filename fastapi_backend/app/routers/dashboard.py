from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..auth import get_current_user_id
from ..database import engine


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
def dashboard_summary(
    user_id: int = Depends(get_current_user_id),
):
    with engine.connect() as connection:

        # Total transaction count
        total_transactions = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM transactions_transaction
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        ).scalar() or 0

        # Total amount spent
        total_amount_spent = connection.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions_transaction
                WHERE user_id = :user_id
                  AND status = 'SUCCESS'
            """),
            {"user_id": user_id},
        ).scalar() or Decimal("0.00")

        # Current month spending
        current_month_spending = connection.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions_transaction
                WHERE user_id = :user_id
                  AND status = 'SUCCESS'
                  AND YEAR(created_at) = YEAR(CURRENT_DATE)
                  AND MONTH(created_at) = MONTH(CURRENT_DATE)
            """),
            {"user_id": user_id},
        ).scalar() or Decimal("0.00")

        # Last 5 transactions
        rows = connection.execute(
            text("""
                SELECT
                    t.amount,
                    c.last4,
                    t.created_at,
                    t.status
                FROM transactions_transaction t
                LEFT JOIN cards_card c
                    ON t.card_id = c.id
                WHERE t.user_id = :user_id
                ORDER BY t.created_at DESC
                LIMIT 5
            """),
            {"user_id": user_id},
        ).mappings().all()

    last_5_transactions = [
        {
            "amount": float(row["amount"]),
            "masked_card_number": (
                f"**** **** **** {row['last4']}"
                if row["last4"]
                else "****"
            ),
            "date": row["created_at"].isoformat()
            if row["created_at"]
            else None,
            "status": row["status"],
        }
        for row in rows
    ]

    return {
        "total_transactions": total_transactions,
        "total_amount_spent": float(total_amount_spent),
        "current_month_spending": float(current_month_spending),
        "available_credit_limit": None,
        "last_5_transactions": last_5_transactions,
    }