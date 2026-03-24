from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserRead


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def register_user(db: Session, payload: RegisterRequest) -> AuthResponse:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise ValueError("An account with that email already exists.")

    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


def authenticate_user(db: Session, payload: LoginRequest) -> AuthResponse | None:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        return None

    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )
