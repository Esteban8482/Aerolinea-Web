import React, { useState } from "react";
import { VueloDetalle } from "../types";
import { api } from "../api";

interface FlightEditProps {
  flight: VueloDetalle;
  onFlightUpdated: () => void;
  onCancel: () => void;
}

export const FlightEdit: React.FC<FlightEditProps> = ({
  flight,
  onFlightUpdated,
  onCancel,
}) => {
  const [fechaSalida, setFechaSalida] = useState<string>(flight.fecha_salida);
  const [horaSalida, setHoraSalida] = useState<string>(flight.hora_salida.slice(0, 5));
  const [costoEconomica, setCostoEconomica] = useState<string>(flight.costo_persona_economica);
  const [costoPrimera, setCostoPrimera] = useState<string>(flight.costo_persona_primera);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.updateFlight(flight.id, {
        fecha_salida: fechaSalida,
        hora_salida: horaSalida.length === 5 ? `${horaSalida}:00` : horaSalida,
        costo_persona_economica: costoEconomica,
        costo_persona_primera: costoPrimera,
      });
      onFlightUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al editar el vuelo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Editar vuelo {flight.codigo_vuelo} (CU-02)</h2>
        <button className="btn o" onClick={onCancel}>
          ✕ Volver
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="grid-3">
          <label>
            Código de vuelo (inmutable)
            <input disabled value={flight.codigo_vuelo} />
          </label>
          <label>
            Origen (inmutable)
            <input disabled value={flight.ruta.origen.nombre} />
          </label>
          <label>
            Destino (inmutable)
            <input disabled value={flight.ruta.destino.nombre} />
          </label>
          <label>
            Tipo de vuelo (inmutable)
            <input disabled value={flight.tipo_vuelo} />
          </label>
          <label>
            Fecha de salida (local origen)
            <input
              type="date"
              value={fechaSalida}
              onChange={(e) => setFechaSalida(e.target.value)}
              required
            />
          </label>
          <label>
            Hora de salida (local origen)
            <input
              type="time"
              value={horaSalida}
              onChange={(e) => setHoraSalida(e.target.value)}
              required
            />
          </label>
          <label>
            Costo clase económica (COP)
            <input
              type="number"
              min="1000"
              step="1000"
              value={costoEconomica}
              onChange={(e) => setCostoEconomica(e.target.value)}
              required
            />
          </label>
          <label>
            Costo primera clase (COP)
            <input
              type="number"
              min="1000"
              step="1000"
              value={costoPrimera}
              onChange={(e) => setCostoPrimera(e.target.value)}
              required
            />
          </label>
          <label>
            Estado del vuelo
            <input disabled value={flight.estado} />
          </label>
        </div>

        <p style={{ margin: "16px 0", color: "var(--text-muted)", fontSize: "0.9rem" }}>
          ℹ️ La fecha y hora de llegada se recalcularán automáticamente en la hora local del destino al confirmar.
        </p>

        <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Guardando cambios..." : "Guardar cambios"}
          </button>
          <button className="btn o" type="button" onClick={onCancel} disabled={loading}>
            Volver
          </button>
        </div>
      </form>
    </div>
  );
};

