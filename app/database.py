"""
SQLite-backed data storage for the ImageModify backend.
This module uses SQLAlchemy with a local SQLite database file
(imagemodify.db) to persist users, API keys, usage stats and plan
information across restarts.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
)

from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from .auth import hash_password

print("LOADED DATABASE.PY FROM:", __file__)

# ====================================================================
# SQLAlchemy setup
# ====================================================================

DATABASE_URL = "sqlite:///./imagemodify.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + multithreading
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """
    User table.
    We keep usage and plan information directly on the user row to
    keep the schema simple for a small SaaS.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, index=True, nullable=False)
    monthly_edits = Column(Integer, default=0, nullable=False)
    total_edits = Column(Integer, default=0, nullable=False)
    plan_name = Column(String(50), default="Free", nullable=False)
    plan_renewal_date = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def init_db() -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


# Create tables immediately on import
init_db()

# ====================================================================
# Helper functions
# ====================================================================


def _generate_api_key(session: Session) -> str:
    """Generate a unique API key by checking for collisions."""
    while True:
        key = secrets.token_hex(24)
        exists = session.query(User).filter(User.api_key == key).first()
        if not exists:
            return key


def _user_to_dict(user: User) -> dict:
    """
    Convert a User ORM instance into the dict shape expected by main.py.
    This preserves the previous in-memory structure:

    {
        "email": ...,
        "hashed_password": ...,
        "api_key": ...,
        "usage": {
            "monthlyEdits": int,
            "totalEdits": int,
        },
        "plan": {
            "name": str,
            "renewalDate": str | None,
        },
    }
    """
    return {
        "email": user.email,
        "hashed_password": user.hashed_password,
        "api_key": user.api_key,
        "usage": {
            "monthlyEdits": user.monthly_edits,
            "totalEdits": user.total_edits,
        },
        "plan": {
            "name": user.plan_name,
            "renewalDate": user.plan_renewal_date,
        },
    }


def _get_db() -> Session:
    """Convenience helper to get a new DB session."""
    return SessionLocal()


# ====================================================================
# Public API – same function names as before
# ====================================================================


def create_user(email: str, password: str) -> dict:
    """Create a new user in the database."""
    db = _get_db()
    try:
        # Check if user already exists before trying to create
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User already exists")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            api_key=_generate_api_key(db),  # ✅ FIXED: Pass 'db' parameter
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return _user_to_dict(user)

    except IntegrityError as e:
        db.rollback()
        print(f"Database integrity error: {e}")
        raise ValueError("User already exists or database constraint violated")
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {e}")
        raise
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[dict]:
    """Retrieve a user dictionary by email. Returns None if not found."""
    db = _get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        return _user_to_dict(user)
    finally:
        db.close()


def get_user_by_api_key(api_key: str) -> Optional[dict]:
    """Retrieve a user by their API key."""
    db = _get_db()
    try:
        user = db.query(User).filter(User.api_key == api_key).first()
        if not user:
            return None
        return _user_to_dict(user)
    finally:
        db.close()


def update_user(email: str, **updates) -> Optional[dict]:
    """
    Update arbitrary fields on a user and return the updated user.
    Supports:
    - top-level attributes that exist on the User model
    - "usage" dict: {"monthlyEdits": int, "totalEdits": int}
    - "plan" dict: {"name": str, "renewalDate": str | None}
    """
    db = _get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        # Handle nested usage updates if provided
        usage = updates.pop("usage", None)
        if usage:
            if "monthlyEdits" in usage:
                user.monthly_edits = usage["monthlyEdits"]
            if "totalEdits" in usage:
                user.total_edits = usage["totalEdits"]

        # Handle nested plan updates if provided
        plan = updates.pop("plan", None)
        if plan:
            if "name" in plan:
                user.plan_name = plan["name"]
            if "renewalDate" in plan:
                user.plan_renewal_date = plan["renewalDate"]

        # Apply any remaining top-level fields that exist on the model
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return _user_to_dict(user)

    finally:
        db.close()


def regenerate_api_key(email: str) -> str:
    """Generate a new API key for the user and return it."""
    db = _get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("User not found")

        # Generate new unique API key
        new_key = _generate_api_key(db)  # ✅ FIXED: Pass 'db' parameter

        user.api_key = new_key
        db.commit()
        db.refresh(user)
        return new_key

    finally:
        db.close()


def increment_usage(email: str, edits: int) -> None:
    """Increment the user's usage counters."""
    db = _get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return

        user.monthly_edits += edits
        user.total_edits += edits
        db.commit()

    finally:
        db.close()
