from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, Session
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()

TITLE_MODEL = "google/gemma-4-31b-it"


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _resolve_session(*, session_id: int | None, db: Session) -> Session:
    """Retorna a sessao; cria uma nova se session_id for None."""
    if session_id is not None:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
        return session
    session = Session()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def _auto_title(*, session: Session, user_message: str, db: Session) -> None:
    """Define titulo automatico usando IA na primeira mensagem da sessao."""
    if session.title != "Nova conversa":
        return
    msg_count = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == str(session.id))
        .count()
    )
    if msg_count > 0:
        return

    try:
        title_reply, _ = await generate_reply(
            user_message=f"Gere um titulo curto (maximo 6 palavras) em portugues que resuma o tema principal desta mensagem. Responda APENAS com o titulo, sem aspas ou pontuacao extra.\n\nMensagem: {user_message.strip()[:500]}",
            history=[],
            model=TITLE_MODEL,
        )
        title = title_reply.strip().strip('"').strip("'").strip(".").strip('"').strip("'")[:60]
        if title:
            session.title = title
        else:
            # fallback: primeiras palavras
            title = user_message.strip()[:50]
            session.title = title if title else "Nova conversa"
    except Exception:
        # fallback silencioso em caso de erro na API
        title = user_message.strip()[:50]
        session.title = title if title else "Nova conversa"
    db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=[item.model_dump() for item in payload.history],
            model=payload.model,
        )
    except OpenRouterConfigError:
        raise HTTPException(status_code=503, detail="API nao configurada corretamente. Verifique sua chave OpenRouter.") from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="O servidor do modelo esta temporariamente indisponivel. Tente novamente em alguns instantes.") from None

    resolved_model = payload.model or model_name or OPENROUTER_MODEL_DEFAULT

    session = _resolve_session(session_id=payload.session_id, db=db)
    session_key = str(session.id)
    await _auto_title(session=session, user_message=payload.message, db=db)

    db.add(ChatMessage(session_key=session_key, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_key=session_key, role="assistant", content=reply, model=resolved_model))
    db.commit()

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    # Valida session_id antes de iniciar o stream
    if payload.session_id is not None:
        session = db.query(Session).filter(Session.id == payload.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError:
            yield f"data: {json.dumps({'error': 'API nao configurada corretamente. Verifique sua chave OpenRouter.'}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError:
            yield f"data: {json.dumps({'error': 'O servidor do modelo esta temporariamente indisponivel. Tente novamente em alguns instantes.'}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            session = _resolve_session(session_id=payload.session_id, db=db)
            session_key = str(session.id)
            await _auto_title(session=session, user_message=payload.message, db=db)

            db.add(
                ChatMessage(
                    session_key=session_key,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_key=session_key,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            db.commit()

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == str(session_id))
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {"id": msg.id, "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}
        for msg in messages
    ]
