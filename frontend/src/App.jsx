const { useEffect, useMemo, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [messages, setMessages] = useState([
    {
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (localStorage.getItem("auth_token")) {
      loadSessions();
    }
  }, []);

  function handleLogout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_email");
    localStorage.removeItem("auth_user_id");
    window.location.reload();
  }

  async function loadSessions() {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch (err) {
      console.error("Erro ao carregar sessoes:", err);
    }
  }

  async function loadSessionMessages(sessionId) {
    try {
      const data = await getSessionMessages(sessionId);
      if (data.length === 0) {
        setMessages([{
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        }]);
      } else {
        setMessages(data.map((m) => ({
          id: createMessageId(),
          role: m.role,
          content: m.content,
        })));
      }
    } catch (err) {
      console.error("Erro ao carregar mensagens:", err);
    }
  }

  async function handleNewSession() {
    setCurrentSessionId(null);
    setMessages([{
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    }]);
  }

  function handleSelectSession(sessionId) {
    if (busy) return;
    setCurrentSessionId(sessionId);
    loadSessionMessages(sessionId);
  }

  function handleDeleteClick(sessionId, event) {
    event.stopPropagation();
    setDeleteTarget(sessionId);
  }

  async function handleConfirmDelete() {
    if (deleteTarget === null) return;
    try {
      await deleteSession(deleteTarget);
      setSessions((prev) => prev.filter((s) => s.id !== deleteTarget));
      if (currentSessionId === deleteTarget) {
        setCurrentSessionId(null);
        setMessages([{
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        }]);
      }
    } catch (err) {
      console.error("Erro ao excluir sessao:", err);
    } finally {
      setDeleteTarget(null);
    }
  }

  function handleCancelDelete() {
    setDeleteTarget(null);
  }

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");
    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
    setText("");
    setBusy(true);

    // Cria sessao automaticamente se for uma conversa nova
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const session = await createSession();
        sessionId = session.id;
        setCurrentSessionId(sessionId);
        setSessions((prev) => [session, ...prev]);
      } catch (err) {
        setBusy(false);
        return;
      }
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        sessionId,
        signal: abortController.signal,
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `${msg.content}${delta}` }
                : msg
            )
          );
        },
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );

      // Recarrega sessoes para pegar titulo automatico
      await loadSessions();
    } catch (err) {
      const aborted = err?.name === "AbortError";
      if (!aborted) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content.trim() ? msg.content : "Nao foi possivel obter resposta do modelo agora." }
              : msg
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId && !msg.content.trim()
              ? { ...msg, content: "Resposta interrompida." }
              : msg
          )
        );
      }
    } finally {
      abortControllerRef.current = null;
      setBusy(false);
    }
  };

  return (
    <div className="app-layout">
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
        <div className="sidebar-header">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)} title="Fechar sidebar">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="12" y1="4" x2="4" y2="12" />
              <line x1="4" y1="4" x2="12" y2="12" />
            </svg>
          </button>
          <button className="logout-btn" onClick={handleLogout} title="Sair">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 2H3a1 1 0 00-1 1v10a1 1 0 001 1h3" />
              <polyline points="10,12 14,8 10,4" />
              <line x1="14" y1="8" x2="6" y2="8" />
            </svg>
          </button>
        </div>
        <button className="new-chat-btn" onClick={handleNewSession}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="8" y1="3" x2="8" y2="13" />
            <line x1="3" y1="8" x2="13" y2="8" />
          </svg>
          Nova conversa
        </button>
        <nav className="session-list">
          {sessions.map((s) => (
            <div key={s.id} className="session-item-wrap">
              <button
                className={`session-item ${currentSessionId === s.id ? "active" : ""}`}
                onClick={() => handleSelectSession(s.id)}
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 0H2a2 2 0 00-2 2v10a2 2 0 002 2h3.5l2 2 2-2H14a2 2 0 002-2V2a2 2 0 00-2-2z" />
                </svg>
                <span className="session-title">{s.title}</span>
              </button>
              <button
                className="session-delete-btn"
                onClick={(e) => handleDeleteClick(s.id, e)}
                title="Excluir conversa"
              >
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <line x1="12" y1="4" x2="4" y2="12" />
                  <line x1="4" y1="4" x2="12" y2="12" />
                </svg>
              </button>
            </div>
          ))}
        </nav>
      </aside>

      {deleteTarget !== null && (
        <div className="modal-overlay" onClick={handleCancelDelete}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <p className="modal-text">Tem certeza que deseja excluir esta conversa?</p>
            <div className="modal-actions">
              <button className="modal-btn modal-cancel" onClick={handleCancelDelete}>Cancelar</button>
              <button className="modal-btn modal-confirm" onClick={handleConfirmDelete}>Excluir</button>
            </div>
          </div>
        </div>
      )}

      {!sidebarOpen && (
        <button className="sidebar-open-btn" onClick={() => setSidebarOpen(true)} title="Abrir sidebar">
          <svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="4" x2="13" y2="4" />
            <line x1="3" y1="8" x2="13" y2="8" />
            <line x1="3" y1="12" x2="13" y2="12" />
          </svg>
        </button>
      )}

      <main className="app-shell">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {messages.map((msg) => (
              <article key={msg.id} className={`bubble ${msg.role}`}>
                <MessageContent content={msg.content} />
              </article>
            ))}
          </div>
        </section>

        <Composer
          text={text}
          busy={busy}
          error={error}
          onChangeText={setText}
          onSubmit={onSubmit}
          onStop={onStop}
        />

        <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));

// Verifica se usuario esta autenticado
const token = localStorage.getItem("auth_token");
if (token) {
  root.render(<App />);
} else {
  root.render(<AuthPage onAuthSuccess={(token, email, userId) => {
    root.render(<App />);
  }} />);
}

