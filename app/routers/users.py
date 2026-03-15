from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import User
from app.schemas import UserCreate, UserOut, UserSyncIn, UserSyncOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.display_name.asc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
        }
        for u in rows
    ]


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()

    if existing:
        return existing

    user = User(
        email=payload.email,
        display_name=payload.display_name,
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

        if existing.display_name != payload.display_name:
            existing.display_name = payload.display_name
            updated = True

        if updated:
            db.add(existing)
            db.commit()
            db.refresh(existing)

        return {
            "id": existing.id,
            "email": existing.email,
            "display_name": existing.display_name,
            "created": False,
        }

    user = User(
        email=payload.email,
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "created": True,
    }