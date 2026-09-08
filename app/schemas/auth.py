import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    # NOTE: intentionally no `role` field. Public registration always
    # creates a MEMBER; a client sending "role": "ADMIN" is simply ignored
    # because this model has no such field to bind to (no mass assignment).


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=128)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordResponse(BaseModel):
    message: str
    # Only ever populated when DEBUG=true, to make local/test password-reset
    # flows testable without a real email provider. A declared
    # `response_model` filters out any field not present on the model, so
    # this must be declared here rather than reusing the plain
    # MessageResponse — otherwise the field is silently dropped by FastAPI
    # regardless of what the endpoint returns.
    debug_reset_token: str | None = None


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    is_email_verified: bool
