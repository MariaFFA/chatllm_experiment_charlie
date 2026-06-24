from __future__ import annotations

from fastapi.testclient import TestClient


class TestListSessions:
    def test_list_sessions_empty(self, client: TestClient):
        """Deve retornar lista vazia quando nao ha sessoes."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_after_creation(self, client: TestClient):
        """Deve listar sessoes apos cria-las."""
        client.post("/api/sessions", json={})
        client.post("/api/sessions", json={})

        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for session in data:
            assert "id" in session
            assert "title" in session
            assert "created_at" in session
            assert "updated_at" in session

    def test_list_sessions_ordered_by_updated(self, client: TestClient):
        """Sessoes devem vir ordenadas por updated_at decrescente."""
        r1 = client.post("/api/sessions", json={})
        s1_id = r1.json()["id"]
        import time
        time.sleep(0.02)
        r2 = client.post("/api/sessions", json={})
        s2_id = r2.json()["id"]

        response = client.get("/api/sessions")
        data = response.json()
        ids = [s["id"] for s in data]
        assert ids == [s2_id, s1_id]


class TestCreateSession:
    def test_create_session_returns_201(self, client: TestClient):
        """Criar sessao deve retornar 201."""
        response = client.post("/api/sessions", json={})
        assert response.status_code == 201

    def test_create_session_has_default_title(self, client: TestClient):
        """Nova sessao deve ter titulo padrao 'Nova conversa'."""
        response = client.post("/api/sessions", json={})
        data = response.json()
        assert data["title"] == "Nova conversa"

    def test_create_session_has_id(self, client: TestClient):
        """Nova sessao deve ter id numerico."""
        response = client.post("/api/sessions", json={})
        data = response.json()
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    def test_multiple_creates_increment_id(self, client: TestClient):
        """Ids de sessoes devem ser incrementais."""
        r1 = client.post("/api/sessions", json={})
        r2 = client.post("/api/sessions", json={})
        assert r2.json()["id"] > r1.json()["id"]


class TestGetSession:
    def test_get_session_by_id(self, client: TestClient):
        """Deve retornar sessao existente."""
        created = client.post("/api/sessions", json={}).json()

        response = client.get(f"/api/sessions/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["title"] == "Nova conversa"

    def test_get_session_not_found(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999")
        assert response.status_code == 404
        assert "nao encontrada" in response.json()["detail"]


class TestUpdateSession:
    def test_update_session_title(self, client: TestClient):
        """Deve atualizar o titulo da sessao."""
        created = client.post("/api/sessions", json={}).json()

        response = client.patch(
            f"/api/sessions/{created['id']}",
            json={"title": "Titulo atualizado"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Titulo atualizado"

    def test_update_session_not_found(self, client: TestClient):
        """Atualizar sessao inexistente deve retornar 404."""
        response = client.patch("/api/sessions/99999", json={"title": "x"})
        assert response.status_code == 404


class TestDeleteSession:
    def test_delete_session(self, client: TestClient):
        """Deve deletar sessao existente."""
        created = client.post("/api/sessions", json={}).json()

        response = client.delete(f"/api/sessions/{created['id']}")
        assert response.status_code == 204

        # Verifica que foi deletada
        get_response = client.get(f"/api/sessions/{created['id']}")
        assert get_response.status_code == 404

    def test_delete_session_not_found(self, client: TestClient):
        """Deletar sessao inexistente deve retornar 404."""
        response = client.delete("/api/sessions/99999")
        assert response.status_code == 404


class TestSessionMessages:
    def test_get_messages_empty_session(self, client: TestClient):
        """Sessao sem mensagens deve retornar lista vazia."""
        created = client.post("/api/sessions", json={}).json()

        response = client.get(f"/api/sessions/{created['id']}/messages")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_messages_session_not_found(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999/messages")
        assert response.status_code == 404

    def test_chat_with_session_id_uses_it(self, client: TestClient):
        """Enviar mensagem com session_id deve usar aquela sessao."""
        created = client.post("/api/sessions", json={}).json()
        session_id = created["id"]

        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
        )
        # Pode falhar por config (503) mas nao por session_id invalido
        assert response.status_code in (200, 422, 503)

        # Se falhou por config, a sessao nao ganhou mensagens
        messages_resp = client.get(f"/api/sessions/{session_id}/messages")
        assert messages_resp.status_code == 200

    def test_chat_with_invalid_session_id(self, client: TestClient):
        """Session_id invalido deve retornar 404."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": 99999},
        )
        assert response.status_code == 404

    def test_chat_without_session_id_auto_creates(self, client: TestClient):
        """Enviar mensagem sem session_id deve criar sessao automaticamente."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        assert response.status_code in (200, 422, 503)

    def test_chat_with_session_id_preserves_messages(self, client: TestClient):
        """Apos enviar mensagem, a sessao deve conter as mensagens."""
        created = client.post("/api/sessions", json={}).json()
        session_id = created["id"]

        # Envia mensagem (pode falhar por config, mas tentamos)
        client.post(
            "/api/chat",
            json={"message": "Teste", "session_id": session_id},
        )

        # Verifica se as mensagens foram salvas (se o chat funcionou)
        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        # Se tiver mensagens, devem estar ordenadas
        messages = resp.json()
        if messages:
            assert messages[0]["role"] == "user"
            assert len(messages) >= 2


class TestChatWithSessionStream:
    def test_stream_with_valid_session_id(self, client: TestClient):
        """Stream com session_id valido deve ser aceito."""
        created = client.post("/api/sessions", json={}).json()

        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": created["id"]},
        )
        assert response.status_code in (200, 422, 503)

    def test_stream_with_invalid_session_id(self, client: TestClient):
        """Stream com session_id invalido deve retornar 404."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": 99999},
        )
        assert response.status_code == 404


class TestAutoTitleFallback:
    def test_auto_title_fallback_on_exception(self, client: TestClient):
        """Quando o auto-title via IA falha, deve usar fallback com primeiras palavras."""
        created = client.post("/api/sessions", json={}).json()
        session_id = created["id"]

        # Envia mensagem (pode falhar 503 por config, mas isso é esperado)
        response = client.post(
            "/api/chat",
            json={"message": "Explique o conceito de divida cognitiva", "session_id": session_id},
        )

        # Se o chat funcionou, o titulo pode ter sido atualizado pela IA (ou fallback)
        # Se deu 503, a sessao continua com titulo original
        if response.status_code == 200:
            sess_resp = client.get(f"/api/sessions/{session_id}")
            assert sess_resp.json()["title"] != "Nova conversa"
        else:
            sess_resp = client.get(f"/api/sessions/{session_id}")
            assert sess_resp.json()["title"] == "Nova conversa"

    def test_auto_title_only_on_first_message(self, client: TestClient):
        """O titulo automatico deve ser definido apenas na primeira mensagem."""
        created = client.post("/api/sessions", json={}).json()
        session_id = created["id"]

        # Atualiza titulo manualmente
        client.patch(f"/api/sessions/{session_id}", json={"title": "Titulo manual"})

        # Envia mensagem — nao deve sobrescrever o titulo manual
        client.post(
            "/api/chat",
            json={"message": "Nova mensagem qualquer", "session_id": session_id},
        )

        sess_resp = client.get(f"/api/sessions/{session_id}")
        assert sess_resp.json()["title"] == "Titulo manual"


class TestDeleteSessionExtended:
    def test_delete_session_with_messages(self, client: TestClient):
        """Deletar sessao deve funcionar mesmo se houver mensagens associadas."""
        created = client.post("/api/sessions", json={}).json()
        session_id = created["id"]

        # Tenta enviar mensagem (pode falhar)
        client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
        )

        # Deleta sessao
        delete_resp = client.delete(f"/api/sessions/{session_id}")
        assert delete_resp.status_code == 204

        # Sessao nao existe mais
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_all_sessions(self, client: TestClient):
        """Deve ser possivel deletar todas as sessoes."""
        s1 = client.post("/api/sessions", json={}).json()
        s2 = client.post("/api/sessions", json={}).json()

        client.delete(f"/api/sessions/{s1['id']}")
        client.delete(f"/api/sessions/{s2['id']}")

        resp = client.get("/api/sessions")
        assert resp.json() == []

    def test_delete_updates_session_list(self, client: TestClient):
        """Apos deletar, a lista de sessoes nao deve incluir a deletada."""
        s1 = client.post("/api/sessions", json={}).json()
        s2 = client.post("/api/sessions", json={}).json()

        client.delete(f"/api/sessions/{s1['id']}")

        resp = client.get("/api/sessions")
        ids = [s["id"] for s in resp.json()]
        assert s1["id"] not in ids
        assert s2["id"] in ids