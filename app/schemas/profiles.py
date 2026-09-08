import uuid
from datetime import date

from pydantic import EmailStr, Field

from app.models.enums import FitnessLevel, UserRole
from app.schemas.common import ORMModel


class MemberProfileRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    photo_url: str | None
    date_of_birth: date | None
    phone: str | None
    height_cm: float | None
    weight_kg: float | None
    fitness_level: FitnessLevel | None
    fitness_goal: str | None
    member_code: str


class MemberProfileUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=30)
    height_cm: float | None = Field(default=None, gt=0, lt=300)
    weight_kg: float | None = Field(default=None, gt=0, lt=500)
    fitness_level: FitnessLevel | None = None
    fitness_goal: str | None = Field(default=None, max_length=500)


class MemberAdminUpdate(MemberProfileUpdate):
    is_active: bool | None = None


class MemberWithAccountRead(MemberProfileRead):
    email: EmailStr
    is_active: bool


class TrainerProfileRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    photo_url: str | None
    bio: str | None
    specialization: str | None
    years_experience: int | None
    is_active: bool


class TrainerProfileUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    bio: str | None = Field(default=None, max_length=2000)
    specialization: str | None = Field(default=None, max_length=255)
    years_experience: int | None = Field(default=None, ge=0, le=80)


class CreateStaffRequest(ORMModel):
    """Used by admin-only endpoints to create TRAINER or ADMIN accounts."""

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    role: UserRole

    def validate_creatable_role(self) -> None:
        from app.core.exceptions import BadRequestError

        if self.role == UserRole.MEMBER:
            raise BadRequestError("Use /auth/register for member accounts")


class AssignTrainerRequest(ORMModel):
    member_id: uuid.UUID
    trainer_id: uuid.UUID
