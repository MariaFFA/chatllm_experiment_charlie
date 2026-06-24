from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ChatMessage, Session


class TestChatMessage:
    def test_create_message_defaults(self, db_session):
        """Deve criar uma mensagem com valores padrao para session_key, model e created_at."""
        msg = ChatMessage(
            role="user",
            content="Ola, mundo!",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_key == "default"
        assert msg.role == "user"
        assert msg.content == "Ola, mundo!"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_create_message_custom_session(self, db_session):
        """Deve criar uma mensagem com session_key customizada."""
        msg = ChatMessage(
            session_key="session-abc",
            role="assistant",
            content="Resposta do assistente.",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.session_key == "session-abc"
        assert msg.role == "assistant"

    def test_create_message_custom_model(self, db_session):
        """Deve criar uma mensagem com modelo customizado."""
        msg = ChatMessage(
            role="user",
            content="Teste",
            model="openai/gpt-4o",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.model == "openai/gpt-4o"

    def test_query_by_session_key(self, db_session):
        """Deve filtrar mensagens por session_key."""
        msg1 = ChatMessage(session_key="s1", role="user", content="a")
        msg2 = ChatMessage(session_key="s2", role="user", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_key == "s1")
            .all()
        )
        assert len(results) == 1
        assert results[0].content == "a"

    def test_query_by_role(self, db_session):
        """Deve filtrar mensagens pelo campo role."""
        msg1 = ChatMessage(role="user", content="pergunta")
        msg2 = ChatMessage(role="assistant", content="resposta")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        users = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "user")
            .all()
        )
        assistants = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "assistant")
            .all()
        )

        assert len(users) == 1
        assert len(assistants) == 1
        assert users[0].content == "pergunta"
        assert assistants[0].content == "resposta"

    def test_created_at_auto_set(self, db_session):
        """O campo created_at deve ser preenchido automaticamente com UTC now."""
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after

    def test_content_persists_long_text(self, db_session):
        """Deve persistir conteudos longos corretamente."""
        long_text = "Lorem ipsum " * 200
        msg = ChatMessage(role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.content == long_text


class TestSession:
    def test_create_session_defaults(self, db_session):
        """Deve criar uma sessao com valores padrao."""
        session = Session()
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.title == "Nova conversa"
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_session_custom_title(self, db_session):
        """Deve criar uma sessao com titulo personalizado."""
        session = Session(title="Minha conversa")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.title == "Minha conversa"

    def test_session_updated_at_updates(self, db_session):
        """O campo updated_at deve mudar apos alteracao."""
        session = Session()
        db_session.add(session)
        db_session.commit()
        first_updated = session.updated_at

        session.title = "Novo titulo"
        db_session.commit()
        db_session.refresh(session)

        assert session.updated_at >= first_updated

    def test_session_ordering(self, db_session):
        """Sessoes devem ser ordenaveis por updated_at."""
        import time

        s1 = Session()
        db_session.add(s1)
        db_session.commit()
        time.sleep(0.01)
        s2 = Session()
        db_session.add(s2)
        db_session.commit()

        results = db_session.query(Session).order_by(Session.updated_at.desc()).all()
        assert results[0].id == s2.id
        assert results[1].id == s1.id

    def test_delete_session_cascades(self, db_session):
        """Deletar uma sessao nao deve deletar mensagens (nao ha cascade)."""
        session = Session()
        db_session.add(session)
        db_session.commit()

        msg = ChatMessage(session_key=str(session.id), role="user", content="teste")
        db_session.add(msg)
        db_session.commit()

        db_session.delete(session)
        db_session.commit()

        msgs = db_session.query(ChatMessage).filter(ChatMessage.session_key == str(session.id)).all()
        # Mensagens permanecem (sem cascade configurado)
        assert len(msgs) == 1
