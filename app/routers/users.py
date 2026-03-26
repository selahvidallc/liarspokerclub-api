from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import User
from app.schemas import (
    UserCreate,
    UserOut,
    UserSyncIn,
    UserSyncOut,
    UserProfileUpdate,
    UserAdminUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.display_name.asc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
        }
        for u in rows
    ]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user_profile(user_id: str, payload: UserProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.display_name = payload.display_name.strip()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}/admin", response_model=UserOut)
def update_user_admin(user_id: str, payload: UserAdminUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.display_name = payload.display_name.strip()
    user.role = payload.role

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()

    if existing:
        return existing

    user = User(
        email=email,
        display_name=payload.display_name,
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/sync", response_model=UserSyncOut)
def sync_user(payload: UserSyncIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()

    if not existing:
        raise HTTPException(
            status_code=403,
            detail="This email address is not invited to Liar's Poker Club."
        )

    updated = False

    if (
        payload.display_name
        and payload.display_name.strip()
        and (
            not existing.display_name
            or existing.display_name.strip() == "Player"
        )
    ):
        existing.display_name = payload.display_name.strip()
        updated = True

    if updated:
        db.add(existing)
        db.commit()
        db.refresh(existing)

    return {
        "id": existing.id,
        "email": existing.email,
        "display_name": existing.display_name,
        "role": existing.role,
        "created": False,
    }