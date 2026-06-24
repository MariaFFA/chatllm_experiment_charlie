from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET_KEY
from backend.database import get_db
from backend.models import User
from backend.schemas.auth import AuthResponse, LoginRequest, RegisterRequest


router = APIRouter()
security = HTTPBearer()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido ou expirado")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado")
    return user


@router.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    user = User(
        email=payload.email,
        password_hash=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_token(user.id, user.email)
    return AuthResponse(token=token, email=user.email, user_id=user.id)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos")

    token = _create_token(user.id, user.email)
    return AuthResponse(token=token, email=user.email, user_id=user.id)


@router.post("/api/auth/logout")
def logout():
    # Logout é tratado no frontend (descarta o token)
    return {"message": "Logout realizado com sucesso"}


@router.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}