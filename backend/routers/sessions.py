from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Session as SessionModel
from backend.routers.auth import get_current_user
from backend.models import User
from backend.schemas.session import SessionCreate, SessionOut, SessionUpdate


router = APIRouter()


@router.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user.id)
        .order_by(SessionModel.updated_at.desc())
        .all()
    )
    return sessions


@router.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = SessionModel(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")
    return session


@router.patch("/api/sessions/{session_id}", response_model=SessionOut)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return session


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")
    db.delete(session)
    db.commit()