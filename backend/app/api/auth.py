from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import hashlib
import secrets

from app.storage import json_store as db

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Simple token store (in-memory for now, tokens persist in json file)
TOKENS_COLLECTION = "tokens"


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    if not credentials:
        return None
    token = credentials.credentials
    token_record = db.find_one(TOKENS_COLLECTION, lambda x: x.get("token") == token)
    if not token_record:
        return None
    user = db.find_by_id("users", token_record.get("user_id"))
    return user


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_current_user(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    user = db.find_one("users", lambda x: x.get("email") == request.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("password_hash") != hash_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate token
    token = generate_token()
    db.insert(TOKENS_COLLECTION, {
        "token": token,
        "user_id": user["id"],
    })

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    )


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    # Check if email already exists
    existing = db.find_one("users", lambda x: x.get("email") == request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = db.insert("users", {
        "email": request.email,
        "name": request.name,
        "password_hash": hash_password(request.password)
    })

    # Create default settings
    db.insert("settings", {
        "user_id": user["id"],
        "email_notifications": True,
        "notification_frequency": "daily",
        "critical_alerts_only": False
    })

    # Generate token
    token = generate_token()
    db.insert(TOKENS_COLLECTION, {
        "token": token,
        "user_id": user["id"],
    })

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    )


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials:
        db.delete_many(TOKENS_COLLECTION, lambda x: x.get("token") == credentials.credentials)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(require_auth)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        created_at=user["created_at"]
    )
