import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, User
from app.auth import decode_access_token

router = APIRouter(prefix="/user", tags=["User"])


# ------------------------------
# Dependency: Get current user
# ------------------------------

def get_current_user(token: str, db: Session):

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ------------------------------
# Get Profile
# ------------------------------

@router.get("/profile")
def profile(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)

    return {
        "email": user.email,
        "name": user.name,
        "api_key": user.api_key,
        "usage_count": user.usage_count,
    }


# ------------------------------
# Generate API Key
# ------------------------------

@router.post("/generate-api-key")
def generate_api_key(token: str, db: Session = Depends(get_db)):

    user = get_current_user(token, db)

    new_key = secrets.token_hex(32)
    user.api_key = new_key
    db.commit()

    return {"api_key": new_key}


# ------------------------------
# Increment Usage
# ------------------------------

@router.post("/increment-usage")
def increment_usage(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    user.usage_count += 1
    db.commit()
    return {"usage_count": user.usage_count}
