from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserResponse
from backend.app.core.security import (
    hash_password,
    get_current_user_id,
    require_role,
)
from backend.app.core.security import (
    hash_password,
    get_current_user_id,
    require_role,
    require_permission,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post("", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User with this email already exists",
        )

    user = User(
    email=user_data.email,
    role_id=user_data.role_id,
    password_hash=hash_password(user_data.password),
)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

TEST_ROLE_ID = "9fce315b-68a5-4084-893f-d3130863c8b0"





@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user

