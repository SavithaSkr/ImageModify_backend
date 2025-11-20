"""
FastAPI application for the ImageModify backend.
Provides Google OAuth login, JWT authentication, API key management,
and usage statistics. Uses SQLite + SQLAlchemy for persistence.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import os
import requests
from jose import jwt

from . import database
from .auth import (
    verify_password,
    create_access_token,
    decode_access_token,
)
from .config import settings
from app.integrations.automation_client import trigger_automation
from .database import increment_usage

print("BACKEND IS RUNNING FROM:", os.getcwd())

app = FastAPI(title="ImageModify Backend API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# -----------------------------------------------------------
#                CORS CONFIGURATION
# -----------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------
#                PYDANTIC MODELS
# -----------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirmPassword: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

# -----------------------------------------------------------
#                AUTH HELPERS
# -----------------------------------------------------------

def authenticate_user(email: str, password: str):
    """Validate login credentials."""
    user = database.get_user_by_email(email)
    if user and verify_password(password, user["hashed_password"]):
        return user
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode JWT and return authenticated user."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    email = payload.get("sub")
    user = database.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

# -----------------------------------------------------------
#                ROOT ENDPOINT
# -----------------------------------------------------------

@app.get("/")
async def read_root():
    return {"message": "Welcome to the ImageModify API"}

# -----------------------------------------------------------
#                PASSWORD SIGNUP (OPTIONAL)
#       (You may KEEP or DELETE this if using Google only)
# -----------------------------------------------------------

@app.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    print("SIGNUP REQUEST:", user_data.email)

    if user_data.password != user_data.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    try:
        database.create_user(user_data.email, user_data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = create_access_token({"sub": user_data.email})
    return {"access_token": token, "token_type": "bearer"}

# -----------------------------------------------------------
#                PASSWORD LOGIN (OPTIONAL)
# -----------------------------------------------------------

@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    user = authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    token = create_access_token({"sub": login_data.email})
    return {"access_token": token}
# -----------------------------------------------------------
#                INTEGRATE AUTOMATION BACKEND
# -----------------------------------------------------------


@app.post("/automation/run")
async def automation_run(current_user: dict = Depends(get_current_user)):
    """
    Trigger the automation backend using the user's API key.
    """
    api_key = current_user["api_key"]

    # Call automation API
    result = await trigger_automation(api_key)

    # Increment usage in database
    increment_usage(current_user["email"], 1)

    return {
        "status": "started",
        "automationResponse": result
    }


# -----------------------------------------------------------
#                GOOGLE OAUTH LOGIN
# -----------------------------------------------------------

@app.get("/auth/google")
async def google_login():
    """Send user to Google's OAuth screen."""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{base_url}?{query}")


@app.get("/auth/google/callback")
async def google_callback(code: Optional[str] = None):
    """Handle Google's OAuth redirect."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing Google code")

    # Exchange auth code for Google token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        },
    ).json()

    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="Google token exchange failed")

    # Decode Google JWT
    google_user = jwt.decode(id_token, options={"verify_signature": False})
    email = google_user["email"]

    # Auto-create user if doesn't exist
    user = database.get_user_by_email(email)
    if not user:
        database.create_user(email, secrets.token_hex(8))

    # Issue our own JWT
    token = create_access_token({"sub": email})

    return RedirectResponse(f"{settings.FRONTEND_URL}/login?token={token}")

# -----------------------------------------------------------
#                USER API KEY ENDPOINTS
# -----------------------------------------------------------

@app.get("/user/api-key")
async def get_api_key(current_user: dict = Depends(get_current_user)):
    return {"apiKey": current_user["api_key"]}

@app.post("/user/api-key/regenerate")
async def regenerate_api_key(current_user: dict = Depends(get_current_user)):
    new_key = database.regenerate_api_key(current_user["email"])
    return {"apiKey": new_key}

@app.get("/user/usage")
async def get_usage(current_user: dict = Depends(get_current_user)):
    return {
        "monthlyEdits": current_user["usage"]["monthlyEdits"],
        "totalEdits": current_user["usage"]["totalEdits"],
        "plan": current_user["plan"],
    }

# -----------------------------------------------------------
#                GLOBAL ERROR HANDLER
# -----------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("Unhandled Exception:", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
