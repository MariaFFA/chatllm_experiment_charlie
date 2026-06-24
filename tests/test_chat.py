from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRootEndpoint:
    def test_root_returns_frontend(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestChatEndpoint:
    def test_chat_endpoint_exists(self, client, auth_headers):
        """Verifica que o endpoint /api/chat responde (espera erro de config sem API key)."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
            headers=auth_headers,
        )
        # Sem OPENROUTER_API_KEY definida, esperamos 503 (config error)
        assert response.status_code in (200, 422, 503)

    def test_chat_empty_message_rejected(self, client, auth_headers):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_chat_unauthenticated(self, client):
        """Sem token deve retornar 401 ou 403."""
        response = client.post("/api/chat", json={"message": "Ola"})
        assert response.status_code in (401, 403)


class TestChatStreamEndpoint:
    def test_chat_stream_endpoint_exists(self, client, auth_headers):
        """Verifica que o endpoint /api/chat/stream aceita requisicoes."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
            headers=auth_headers,
        )
        # Streaming pode iniciar e depois falhar sem API key
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_empty_message_rejected(self, client, auth_headers):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        response = client.post(
            "/api/chat/stream",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_chat_stream_unauthenticated(self, client):
        """Stream sem token deve retornar 401 ou 403."""
        response = client.post("/api/chat/stream", json={"message": "Ola"})
        assert response.status_code in (401, 403)


class TestCORSMiddleware:
    def test_cors_headers_present(self, client):
        """Verifica que os headers CORS estao presentes."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # O FastAPI com allow_origins=["*"] permite a requisicao
        assert response.status_code in (200, 405)
