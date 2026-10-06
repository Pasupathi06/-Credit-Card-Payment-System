from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    user_id: int
    card_id: int
    amount: Decimal = Field(gt=0)
    description: str | None = None


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    card_id: int
    amount: Decimal
    status: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True