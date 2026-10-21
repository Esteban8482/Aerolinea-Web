import React, { useState } from "react";
import { api } from "../api";
import { SessionState } from "../types";

interface AuthBarProps {
  session: SessionState | null;
  onSessionChange: (session: SessionState) => void;
}

export const AuthBar: React.FC<AuthBarProps> = ({ session, onSessionChange }) => {
  const [email, setEmail] = useState("admin.vuelos@example.invalid");
  const [password, setPassword] = useState("admin-password-pruebas-2026");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.login(email, password);
      const newSession = await api.getSession();
      onSessionChange(newSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    try {
      await api.logout();
      const newSession = await api.getSession();
      onSessionChange(newSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cerrar sesión.");
    } finally {
      setLoading(false);
    }
  };

  const isAdmin = session?.authenticated && session.role === "ADMINISTRADOR";

  return (
    <div className="header-bar">
      <div>
        <h1>Aerolínea Web</h1>
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          🔒 Consola de Administración de Vuelos (CU-01, CU-02, CU-03)
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        {isAdmin ? (
          <div className="auth-badge">
            <span style={{ color: "var(--success)", fontWeight: 700 }}>● Administrador</span>
            <span>{session.email || "Administrador activo"}</span>
            <button className="btn o" onClick={handleLogout} disabled={loading} style={{ padding: "4px 10px" }}>
              Cerrar sesión
            </button>
          </div>
        ) : (
          <form onSubmit={handleLogin} style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Acceso admin:</span>
            <input
              type="email"
              placeholder="Correo admin"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{ width: "200px", padding: "6px 8px" }}
            />
            <input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ width: "130px", padding: "6px 8px" }}
            />
            <button className="btn" type="submit" disabled={loading} style={{ padding: "6px 12px" }}>
              {loading ? "Entrando..." : "Acceder"}
            </button>
          </form>
        )}
      </div>

      {error && (
        <div style={{ width: "100%", marginTop: "8px" }} className="alert alert-error">
          {error}
        </div>
      )}
    </div>
  );
};

