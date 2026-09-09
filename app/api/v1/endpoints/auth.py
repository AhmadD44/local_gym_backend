from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)
from app.schemas.common import MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenPairResponse,
    status_code=201,
    summary="Register a new MEMBER account",
    description="Public registration always creates a MEMBER account. Any `role` field sent by "
    "the client is ignored/rejected — there is no way to self-register as TRAINER or ADMIN.",
    dependencies=[
        Depends(RateLimiter(times=settings.rate_limit_register_per_minute, seconds=60, scope="register"))
    ],
)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_member(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
    access, refresh = await auth_service.issue_token_pair(
        db, user=user, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
    )
    return TokenPairResponse(access_token=access, refresh_token=refresh, role=user.role)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Login with email and password",
    dependencies=[Depends(RateLimiter(times=settings.rate_limit_login_per_minute, seconds=60, scope="login"))],
)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    access, refresh = await auth_service.issue_token_pair(
        db, user=user, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
    )
    return TokenPairResponse(access_token=access, refresh_token=refresh, role=user.role)


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Rotate an access/refresh token pair",
    description="Refresh tokens are single-use and rotate on every call. Presenting an "
    "already-used (revoked) refresh token is treated as token theft and revokes the entire "
    "session family, forcing re-authentication.",
    dependencies=[Depends(RateLimiter(times=20, seconds=60, scope="refresh"))],
)
async def refresh(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    access, refresh_token, role = await auth_service.refresh_token_pair(
        db,
        refresh_token=payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    return TokenPairResponse(access_token=access, refresh_token=refresh_token, role=role)


@router.post("/logout", response_model=MessageResponse, summary="Revoke a single refresh session")
async def logout_endpoint(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.logout(db, refresh_token=payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Revoke every refresh session for the current user",
)
async def logout_all_endpoint(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    await auth_service.logout_all(db, user_id=user.id)
    return MessageResponse(message="All sessions logged out")


@router.get("/me", response_model=CurrentUserResponse, summary="Get the authenticated user's account")
async def me(user: User = Depends(get_current_active_user)):
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
    )


@router.post("/change-password", response_model=MessageResponse, summary="Change the current user's password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await auth_service.change_password(
        db, user=user, current_password=payload.current_password, new_password=payload.new_password
    )
    return MessageResponse(message="Password changed. Please log in again on all devices.")


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset token",
    description="Always returns a generic success message regardless of whether the email "
    "exists, to avoid account enumeration. In non-production environments the raw reset "
    "token is included in the response to simplify local testing.",
    dependencies=[Depends(RateLimiter(times=3, seconds=60, scope="forgot_password"))],
)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    token = await auth_service.request_password_reset(db, email=payload.email)
    message = "If that email exists, a password reset link has been sent."
    if settings.debug and token:
        return ForgotPasswordResponse(message=message, debug_reset_token=token)
    return ForgotPasswordResponse(message=message)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset a password using a reset token",
    dependencies=[Depends(RateLimiter(times=5, seconds=60, scope="reset_password"))],
)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(db, token=payload.token, new_password=payload.new_password)
    return MessageResponse(message="Password has been reset. Please log in again.")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
