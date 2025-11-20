from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, User
from app.auth import decode_access_token
from app.integrations.automation_client import trigger_automation

router = APIRouter(prefix="/automation", tags=["Automation"])
# ------------------------------
# Dynamic Sheet Automation
# ------------------------------
from pydantic import BaseModel

class DynamicAutomationRequest(BaseModel):
    sheet_id: str
    sheet_name: str | None = None


@router.post("/run-dynamic")
async def run_dynamic(
    payload: DynamicAutomationRequest,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Allows the user to pass sheet_id + sheet_name dynamically.
    Useful when users want to automate multiple Google Sheets.
    """

    user = get_current_user(token, db)

    if not user.api_key:
        raise HTTPException(status_code=400, detail="API key missing")

    body = {
        "sheet_id": payload.sheet_id,
        "sheet_name": payload.sheet_name
    }

    success = await trigger_automation(user.api_key, body)

    if not success:
        raise HTTPException(status_code=500, detail="Automation server failed")

    return {"status": "started", "mode": "dynamic"}


# ------------------------------
# Current user helper
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
# Trigger Automation
# ------------------------------

@router.post("/run")
async def start_processing(token: str, db: Session = Depends(get_db)):

    user = get_current_user(token, db)

    if not user.api_key:
        raise HTTPException(status_code=400, detail="API key missing")

    # Call automation microservice
    success = await trigger_automation(user.api_key)

    if not success:
        raise HTTPException(status_code=500, detail="Automation server failed")

    return {"status": "started"}
