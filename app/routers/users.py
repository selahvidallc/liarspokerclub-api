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


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()

    if existing:
        return existing

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/sync", response_model=UserSyncOut)
def sync_user(payload: UserSyncIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()

    if existing:
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

    user = User(
        email=payload.email,
        display_name=payload.display_name.strip(),
        role="player",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "created": True,
    }