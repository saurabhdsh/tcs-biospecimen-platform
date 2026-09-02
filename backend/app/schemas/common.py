from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class StorageAssignRequest(BaseModel):
    storage_location_id: UUID
    reason: str | None = None


class MoveRequest(BaseModel):
    destination_location_id: UUID
    reason: str


class CustodianAssignRequest(BaseModel):
    custodian_id: UUID
    reason: str | None = None


class CheckoutRequest(BaseModel):
    purpose: str


class ReturnRequest(BaseModel):
    storage_location_id: UUID


class ReprintRequest(BaseModel):
    reason: str


class ChildSampleRequest(BaseModel):
    relationship_type: str
    output_quantity: Decimal
    output_unit: str
    parent_quantity_consumed: Decimal
    child_sample_type: str
    existing_child_id: UUID | None = None


class EnvironmentalEventRequest(BaseModel):
    measured_value: Decimal
    unit: str = "C"
    acceptable_min: Decimal
    acceptable_max: Decimal
    occurred_at: datetime | None = None
    source: str | None = None
    notes: str | None = None
    create_exception: bool = True


class ResolveExceptionRequest(BaseModel):
    resolution_comment: str
    disposition: str


class CreateUserRequest(BaseModel):
    email: str
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    roles: list[str] = Field(min_length=1)
