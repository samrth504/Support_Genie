"""Signup / login / me."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rate_limit import login_limiter, signup_limiter
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import ChangePasswordRequest, SignupRequest, TokenResponse
from app.schemas.user import UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(signup_limiter)])
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Public signup. Always creates a CUSTOMER — staff accounts are created by an admin script."""
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("New customer signed up: id=%s", user.id)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_limiter)])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """OAuth2 form login (field `username` = email). Works with Swagger's Authorize button."""
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    # Same error for "no such email" and "wrong password" -> attackers can't discover emails
    if user is None or not verify_password(form.password, user.password_hash):
        logger.warning("Failed login attempt for email=%s", form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(login_limiter)])
def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> None:
    """Logged-in user changes their own password (current password required)."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    logger.info("User %s changed their password", user.id)
