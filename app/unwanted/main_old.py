"""
FastAPI application for the ImageModify backend. This API provides
authentication endpoints, API key management, usage statistics and
placeholders for Google OAuth. It uses an in‑memory data store for
demonstration purposes. Replace the storage and OAuth handling with
real implementations for production use.
"""


from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional

import secrets

from . import database_old
from .auth import verify_password, create_access_token, decode_access_token
from .config import settings
import importlib
import app.database_old

# force reload of database module
importlib.reload(app.database_old)
import os
print("BACKEND IS RUNNING FROM:", os.getcwd())

app = FastAPI(title="ImageModify Backend API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Allow CORS for local development and the configured front‑end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Return the user if the email and password are valid, else None."""
    user = database_old.get_user_by_email(email)
    if user and verify_password(password, user["hashed_password"]):
        return user
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency that extracts the current user from a JWT token."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    email = payload.get("sub")
    user = database_old.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/")
async def read_root():
    return {"message": "Welcome to the ImageModify API"}


@app.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    """
    Register a new user and return a JWT token.
    """

    # Debug print
    print("Received signup payload:", user_data.dict())

    # Password confirmation
    if user_data.password != user_data.confirmPassword:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    # Try creating user
    try:
        user = database_old.create_user(user_data.email, user_data.password)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    # Create JWT token
    token = create_access_token({"sub": user_data.email})

    print("Signup success, returning token...")

    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Authenticate a user and return a JWT token."""
    user = authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token({"sub": login_data.email})
    return {"access_token": token}


@app.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Placeholder for password reset logic. Always returns success."""
    user = database_old.get_user_by_email(req.email)
    if not user:
        # For security do not reveal user existence
        return {"message": "If an account exists, a reset link has been sent."}
    # In a real implementation you would send an email here.
    return {"message": "If an account exists, a reset link has been sent."}


@app.get("/auth/google")
async def google_login():
    """Initiate Google OAuth by redirecting the user to Google's auth page."""
    # Build Google's OAuth URL; these parameters should match your Google project.
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
    url = f"{base_url}?{query}"
    return RedirectResponse(url)


@app.get("/auth/google/callback")
async def google_callback(code: Optional[str] = None):
    """Handle Google's OAuth callback. This implementation is a stub."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")
    # Normally, exchange the code for an access token and retrieve the user info.
    # Here we'll simulate that a user with a dummy email authenticated via Google.
    dummy_email = f"user_{code[:5]}@example.com"
    user = database_old.get_user_by_email(dummy_email)
    if not user:
        # Create the user if not exists, with a random password
        user = database_old.create_user(dummy_email, secrets.token_hex(8))
    token = create_access_token({"sub": dummy_email})
    # Redirect back to the front‑end with the token as a query parameter
    redirect_url = f"{settings.FRONTEND_URL}?token={token}"
    return RedirectResponse(redirect_url)


@app.get("/user/api-key")
async def get_api_key(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's API key."""
    return {"apiKey": current_user["api_key"]}


@app.post("/user/api-key/regenerate")
async def regenerate_api_key(current_user: dict = Depends(get_current_user)):
    """Generate a new API key for the authenticated user."""
    new_key = database_old.regenerate_api_key(current_user["email"])
    return {"apiKey": new_key}


@app.get("/user/usage")
async def get_usage(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's usage statistics and plan details."""
    return {
        "monthlyEdits": current_user["usage"]["monthlyEdits"],
        "totalEdits": current_user["usage"]["totalEdits"],
        "plan": current_user["plan"],
    }