import React, { useState } from "react";
import { Vuelo } from "../types";
import { api } from "../api";

interface FlightCancelProps {
  flight: Vuelo;
  onFlightCancelled: () => void;
  onCancel: () => void;
}

export const FlightCancel: React.FC<FlightCancelProps> = ({
  flight,
  onFlightCancelled,
  onCancel,
}) => {
  const [motivo, setMotivo] = useState("");
  const [alternativa, setAlternativa] = useState<"REINTEGRO" | "REUBICACION">("REINTEGRO");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!motivo.trim()) {
      setError("Debes indicar el motivo de la cancelación.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.cancelFlight(flight.id, {
        motivo: motivo.trim(),
        alternativa,
      });
      onFlightCancelled();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cancelar el vuelo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2 style={{ fontSize: "1.2rem", color: "var(--danger)", marginBottom: "12px" }}>
          ¿Cancelar vuelo {flight.codigo_vuelo}? (CU-03)
        </h2>

        <div style={{ background: "var(--bg-subtle)", padding: "12px", borderRadius: "6px", marginBottom: "16px" }}>
          <p><strong>Ruta:</strong> {flight.origen} → {flight.destino}</p>
          <p><strong>Salida:</strong> {flight.fecha_salida} a las {flight.hora_salida}</p>
          <p><strong>Tipo:</strong> {flight.tipo_vuelo}</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label>
            Motivo de cancelación (obligatorio)
            <textarea
              rows={3}
              placeholder="Explica la causa de la cancelación (ej. mantenimiento aeronáutico, meteorología...)"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              required
            />
          </label>

          <div style={{ margin: "16px 0" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "8px" }}>
              Alternativa aplicable para pasajeros afectados:
            </div>
            <label style={{ flexDirection: "row", alignItems: "center", gap: "8px", fontWeight: "normal", cursor: "pointer" }}>
              <input
                type="radio"
                name="alternativa"
                value="REINTEGRO"
                checked={alternativa === "REINTEGRO"}
                onChange={() => setAlternativa("REINTEGRO")}
              />
              Reintegro directo a la billetera del comprador (Recomendado)
            </label>
            <label style={{ flexDirection: "row", alignItems: "center", gap: "8px", fontWeight: "normal", cursor: "pointer" }}>
              <input
                type="radio"
                name="alternativa"
                value="REUBICACION"
                checked={alternativa === "REUBICACION"}
                onChange={() => setAlternativa("REUBICACION")}
              />
              Reubicar en otro vuelo de la misma ruta (o reintegro si no hay cupos)
            </label>
          </div>

          <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
            <button className="btn r" type="submit" disabled={loading}>
              {loading ? "Cancelando..." : "Confirmar cancelación"}
            </button>
            <button className="btn o" type="button" onClick={onCancel} disabled={loading}>
              Volver
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

