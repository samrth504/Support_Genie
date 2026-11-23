from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserOut


def check_password_strength(v: str) -> str:
    """Same rule for signup and password change: 8-72 chars, at least one letter and one number."""
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one letter and one number")
    return v


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    # bcrypt only uses the first 72 bytes, so we cap the length explicitly
    password: str = Field(min_length=8, max_length=72)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must have at least 2 characters")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return check_password_strength(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        return check_password_strength(v)
