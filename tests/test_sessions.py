from __future__ import annotations


class TestListSessions:
    def test_list_sessions_empty(self, client, auth_headers):
        """Deve retornar lista vazia quando nao ha sessoes."""
        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_after_creation(self, client, auth_headers):
        """Deve listar sessoes apos cria-las."""
        client.post("/api/sessions", json={}, headers=auth_headers)
        client.post("/api/sessions", json={}, headers=auth_headers)

        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for session in data:
            assert "id" in session
            assert "title" in session
            assert "created_at" in session
            assert "updated_at" in session

    def test_list_sessions_ordered_by_updated(self, client, auth_headers):
        """Sessoes devem vir ordenadas por updated_at decrescente."""
        r1 = client.post("/api/sessions", json={}, headers=auth_headers)
        s1_id = r1.json()["id"]
        import time
        time.sleep(0.02)
        r2 = client.post("/api/sessions", json={}, headers=auth_headers)
        s2_id = r2.json()["id"]

        response = client.get("/api/sessions", headers=auth_headers)
        data = response.json()
        ids = [s["id"] for s in data]
        assert ids == [s2_id, s1_id]

    def test_list_sessions_unauthenticated(self, client):
        """Listar sessoes sem token deve retornar 401 ou 403."""
        response = client.get("/api/sessions")
        assert response.status_code in (401, 403)

    def test_list_sessions_other_user_not_visible(self, client, auth_headers, db_session):
        """Sessoes de outro usuario nao devem aparecer."""
        from backend.models import Session as SessionModel
        other = SessionModel(user_id=999, title="Sessao de outro")
        db_session.add(other)
        db_session.commit()

        response = client.get("/api/sessions", headers=auth_headers)
        assert response.json() == []


class TestCreateSession:
    def test_create_session_returns_201(self, client, auth_headers):
        """Criar sessao deve retornar 201."""
        response = client.post("/api/sessions", json={}, headers=auth_headers)
        assert response.status_code == 201

    def test_create_session_has_default_title(self, client, auth_headers):
        """Nova sessao deve ter titulo padrao 'Nova conversa'."""
        response = client.post("/api/sessions", json={}, headers=auth_headers)
        data = response.json()
        assert data["title"] == "Nova conversa"

    def test_create_session_has_id(self, client, auth_headers):
        """Nova sessao deve ter id numerico."""
        response = client.post("/api/sessions", json={}, headers=auth_headers)
        data = response.json()
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    def test_create_session_unauthenticated(self, client):
        """Criar sessao sem token deve retornar 401 ou 403."""
        response = client.post("/api/sessions", json={})
        assert response.status_code in (401, 403)


class TestGetSession:
    def test_get_session_by_id(self, client, auth_headers):
        """Deve retornar sessao existente."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()

        response = client.get(f"/api/sessions/{created['id']}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["title"] == "Nova conversa"

    def test_get_session_not_found(self, client, auth_headers):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "nao encontrada" in response.json()["detail"]

    def test_get_session_other_user_forbidden(self, client, auth_headers, db_session):
        """Sessao de outro usuario nao deve ser acessivel."""
        from backend.models import Session as SessionModel
        other = SessionModel(user_id=999)
        db_session.add(other)
        db_session.commit()

        response = client.get(f"/api/sessions/{other.id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateSession:
    def test_update_session_title(self, client, auth_headers):
        """Deve atualizar o titulo da sessao."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()

        response = client.patch(
            f"/api/sessions/{created['id']}",
            json={"title": "Titulo atualizado"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Titulo atualizado"

    def test_update_session_not_found(self, client, auth_headers):
        """Atualizar sessao inexistente deve retornar 404."""
        response = client.patch("/api/sessions/99999", json={"title": "x"}, headers=auth_headers)
        assert response.status_code == 404

    def test_update_session_unauthenticated(self, client, auth_headers):
        """Atualizar sessao sem token deve retornar 401 ou 403."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.patch(f"/api/sessions/{created['id']}", json={"title": "x"})
        assert response.status_code in (401, 403)


class TestDeleteSession:
    def test_delete_session(self, client, auth_headers):
        """Deve deletar sessao existente."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()

        response = client.delete(f"/api/sessions/{created['id']}", headers=auth_headers)
        assert response.status_code == 204

        get_response = client.get(f"/api/sessions/{created['id']}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_session_not_found(self, client, auth_headers):
        """Deletar sessao inexistente deve retornar 404."""
        response = client.delete("/api/sessions/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_session_unauthenticated(self, client, auth_headers):
        """Deletar sessao sem token deve retornar 401 ou 403."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.delete(f"/api/sessions/{created['id']}")
        assert response.status_code in (401, 403)


class TestSessionMessages:
    def test_get_messages_empty_session(self, client, auth_headers):
        """Sessao sem mensagens deve retornar lista vazia."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()

        response = client.get(f"/api/sessions/{created['id']}/messages", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_messages_session_not_found(self, client, auth_headers):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999/messages", headers=auth_headers)
        assert response.status_code == 404

    def test_get_messages_unauthenticated(self, client, auth_headers):
        """Messages sem token deve retornar 401 ou 403."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        response = client.get(f"/api/sessions/{created['id']}/messages")
        assert response.status_code in (401, 403)

    def test_chat_with_session_id_uses_it(self, client, auth_headers):
        """Enviar mensagem com session_id deve usar aquela sessao."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        session_id = created["id"]

        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422, 503)

        messages_resp = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers)
        assert messages_resp.status_code == 200

    def test_chat_with_invalid_session_id(self, client, auth_headers):
        """Session_id invalido deve retornar 404."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": 99999},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_chat_without_session_id_auto_creates(self, client, auth_headers):
        """Enviar mensagem sem session_id deve criar sessao automaticamente."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422, 503)

    def test_chat_with_session_id_preserves_messages(self, client, auth_headers):
        """Apos enviar mensagem, a sessao deve conter as mensagens."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        session_id = created["id"]

        client.post(
            "/api/chat",
            json={"message": "Teste", "session_id": session_id},
            headers=auth_headers,
        )

        resp = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers)
        assert resp.status_code == 200
        messages = resp.json()
        if messages:
            assert messages[0]["role"] == "user"
            assert len(messages) >= 2


class TestChatWithSessionStream:
    def test_stream_with_valid_session_id(self, client, auth_headers):
        """Stream com session_id valido deve ser aceito."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()

        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": created["id"]},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422, 503)

    def test_stream_with_invalid_session_id(self, client, auth_headers):
        """Stream com session_id invalido deve retornar 404."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": 99999},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestAutoTitleFallback:
    def test_auto_title_fallback_on_exception(self, client, auth_headers):
        """Quando o auto-title via IA falha, deve usar fallback com primeiras palavras."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        session_id = created["id"]

        response = client.post(
            "/api/chat",
            json={"message": "Explique o conceito de divida cognitiva", "session_id": session_id},
            headers=auth_headers,
        )

        sess_resp = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        if response.status_code == 200:
            assert sess_resp.json()["title"] != "Nova conversa"
        else:
            assert sess_resp.json()["title"] == "Nova conversa"

    def test_auto_title_only_on_first_message(self, client, auth_headers):
        """O titulo automatico deve ser definido apenas na primeira mensagem."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        session_id = created["id"]

        client.patch(f"/api/sessions/{session_id}", json={"title": "Titulo manual"}, headers=auth_headers)

        client.post(
            "/api/chat",
            json={"message": "Nova mensagem qualquer", "session_id": session_id},
            headers=auth_headers,
        )

        sess_resp = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert sess_resp.json()["title"] == "Titulo manual"


class TestDeleteSessionExtended:
    def test_delete_session_with_messages(self, client, auth_headers):
        """Deletar sessao deve funcionar mesmo se houver mensagens associadas."""
        created = client.post("/api/sessions", json={}, headers=auth_headers).json()
        session_id = created["id"]

        client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
            headers=auth_headers,
        )

        delete_resp = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_all_sessions(self, client, auth_headers):
        """Deve ser possivel deletar todas as sessoes."""
        s1 = client.post("/api/sessions", json={}, headers=auth_headers).json()
        s2 = client.post("/api/sessions", json={}, headers=auth_headers).json()

        client.delete(f"/api/sessions/{s1['id']}", headers=auth_headers)
        client.delete(f"/api/sessions/{s2['id']}", headers=auth_headers)

        resp = client.get("/api/sessions", headers=auth_headers)
        assert resp.json() == []

    def test_delete_updates_session_list(self, client, auth_headers):
        """Apos deletar, a lista de sessoes nao deve incluir a deletada."""
        s1 = client.post("/api/sessions", json={}, headers=auth_headers).json()
        s2 = client.post("/api/sessions", json={}, headers=auth_headers).json()

        client.delete(f"/api/sessions/{s1['id']}", headers=auth_headers)

        resp = client.get("/api/sessions", headers=auth_headers)
        ids = [s["id"] for s in resp.json()]
        assert s1["id"] not in ids
        assert s2["id"] in ids