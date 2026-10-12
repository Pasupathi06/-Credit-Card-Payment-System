from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    card_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    description: str | None = None


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    card_id: int
    amount: Decimal
    description: str | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)