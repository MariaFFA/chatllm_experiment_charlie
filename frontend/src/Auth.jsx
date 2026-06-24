const { useState } = React;

function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanedEmail = email.trim();
    if (!cleanedEmail || !password) return;

    setAuthError("");
    setAuthBusy(true);

    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: cleanedEmail, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setAuthError(data.detail || "Erro ao autenticar.");
        setAuthBusy(false);
        return;
      }

      // Salva token e dados do usuario
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("auth_email", data.email);
      localStorage.setItem("auth_user_id", String(data.user_id));
      onAuthSuccess(data.token, data.email, data.user_id);
    } catch (err) {
      setAuthError("Erro de conexao com o servidor.");
      setAuthBusy(false);
    }
  }

  function toggleMode() {
    setMode(mode === "login" ? "register" : "login");
    setAuthError("");
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <h2 className="auth-subtitle">{mode === "login" ? "Entrar" : "Criar conta"}</h2>

        {authError && <div className="auth-error">{authError}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Seu email"
            maxLength={255}
            disabled={authBusy}
            autoFocus
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Sua senha"
            maxLength={128}
            disabled={authBusy}
            required
          />
          <button type="submit" disabled={authBusy || !email.trim() || !password}>
            {authBusy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
          </button>
        </form>

        <p className="auth-toggle">
          {mode === "login" ? (
            <>Nao tem conta? <a href="#" onClick={(e) => { e.preventDefault(); toggleMode(); }}>Crie uma</a></>
          ) : (
            <>Ja tem conta? <a href="#" onClick={(e) => { e.preventDefault(); toggleMode(); }}>Faca login</a></>
          )}
        </p>
      </div>
    </div>
  );
}