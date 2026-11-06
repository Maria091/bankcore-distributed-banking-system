"""Typed API contracts. Monetary amounts are integer cents."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class AccountCreate(BaseModel):
    owner_label: str = Field(min_length=2, max_length=80)
    currency: Literal["USD"] = "USD"

class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    owner_label: str
    currency: str
    balance_minor: int
    status: str

class FundingRequest(BaseModel):
    account_id: str
    amount_minor: int = Field(gt=0, le=5_000_000, strict=True)

class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount_minor: int = Field(gt=0, le=10_000_000, strict=True)
    reference: str = Field(default="", max_length=100)

class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_account_id: str
    destination_account_id: str
    amount_minor: int
    status: Literal["POSTED", "REVIEW_REQUIRED"]
    kind: Literal["TRANSFER", "DEMO_FUND"]
    reference: str

class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    transfer_id: str
    amount_minor: int
    account_id: str
