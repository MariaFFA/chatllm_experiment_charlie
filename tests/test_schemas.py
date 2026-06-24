from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.chat import ChatMessageIn, ChatRequest, ChatResponse
from backend.schemas.session import SessionCreate, SessionOut, SessionUpdate


class TestChatMessageIn:
    def test_valid_user_message(self):
        msg = ChatMessageIn(role="user", content="Ola!")
        assert msg.role == "user"
        assert msg.content == "Ola!"

    def test_valid_assistant_message(self):
        msg = ChatMessageIn(role="assistant", content="Resposta.")
        assert msg.role == "assistant"
        assert msg.content == "Resposta."

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="system", content="Nao permitido")

    def test_empty_content(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="user", content="")

    def test_content_too_long(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="user", content="x" * 8001)


class TestChatRequest:
    def test_valid_request_minimal(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.model is None
        assert req.history == []

    def test_valid_request_with_model(self):
        req = ChatRequest(message="Hi", model="openai/gpt-4o")
        assert req.model == "openai/gpt-4o"

    def test_valid_request_with_history(self):
        history = [
            ChatMessageIn(role="user", content="pergunta"),
            ChatMessageIn(role="assistant", content="resposta"),
        ]
        req = ChatRequest(message="continuacao", history=history)
        assert len(req.history) == 2
        assert req.history[0].role == "user"

    def test_empty_message(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 8001)

    def test_history_defaults_to_empty(self):
        req = ChatRequest(message="Hello")
        assert req.history == []

    def test_valid_request_with_session_id(self):
        """ChatRequest deve aceitar session_id opcional."""
        req = ChatRequest(message="Hello", session_id=42)
        assert req.session_id == 42

    def test_valid_request_session_id_none(self):
        """ChatRequest com session_id None deve ser valido."""
        req = ChatRequest(message="Hello", session_id=None)
        assert req.session_id is None


class TestChatResponse:
    def test_valid_response(self):
        resp = ChatResponse(reply="Resposta do modelo.", model="google/gemma-4-31b-it")
        assert resp.reply == "Resposta do modelo."
        assert resp.model == "google/gemma-4-31b-it"


class TestSessionSchemas:
    def test_session_create_empty(self):
        """SessionCreate pode ser instanciado sem campos."""
        payload = SessionCreate()
        assert payload is not None

    def test_session_update_title(self):
        """SessionUpdate deve ter titulo."""
        payload = SessionUpdate(title="Novo titulo")
        assert payload.title == "Novo titulo"

    def test_session_update_title_empty(self):
        """SessionUpdate aceita titulo vazio."""
        payload = SessionUpdate(title="")
        assert payload.title == ""

    def test_session_out_from_attributes(self):
        """SessionOut deve ser construivel a partir de atributos."""
        from datetime import datetime

        data = {
            "id": 1,
            "title": "Teste",
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 2),
        }
        out = SessionOut.model_validate(data)
        assert out.id == 1
        assert out.title == "Teste"
        assert out.created_at.year == 2026

    def test_session_out_serialization(self, db_session):
        """SessionOut deve serializar corretamente para dict."""
        from backend.models import Session

        session = Session(title="Serializa")
        db_session.add(session)
        db_session.commit()

        out = SessionOut.model_validate(session)
        data = out.model_dump()
        assert data["id"] == session.id
        assert data["title"] == "Serializa"
        assert "created_at" in data
        assert "updated_at" in data
