import React from "react";
import { Vuelo } from "../types";

interface FlightListProps {
  flights: Vuelo[];
  filtroEstado: string;
  onFiltroChange: (estado: string) => void;
  onOpenCreate: () => void;
  onOpenEdit: (flight: Vuelo) => void;
  onOpenCancel: (flight: Vuelo) => void;
  isAdmin: boolean;
  loading: boolean;
}

export const FlightList: React.FC<FlightListProps> = ({
  flights,
  filtroEstado,
  onFiltroChange,
  onOpenCreate,
  onOpenEdit,
  onOpenCancel,
  isAdmin,
  loading,
}) => {
  return (
    <div className="card">
      <div className="controls-bar">
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {isAdmin ? (
            <button className="btn" onClick={onOpenCreate}>
              + Programar vuelo
            </button>
          ) : (
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              🔒 Inicia sesión como Administrador para programar, editar o cancelar vuelos.
            </span>
          )}
        </div>

        <div className="filter-group">
          <label style={{ margin: 0, flexDirection: "row", alignItems: "center", gap: "8px" }}>
            Estado:
            <select
              value={filtroEstado}
              onChange={(e) => onFiltroChange(e.target.value)}
              style={{ margin: 0 }}
            >
              <option value="TODOS">Todos</option>
              <option value="PROGRAMADO">Programado</option>
              <option value="REALIZADO">Realizado</option>
              <option value="CANCELADO">Cancelado</option>
            </select>
          </label>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Cargando catálogo de vuelos...
        </div>
      ) : flights.length === 0 ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          No hay vuelos registrados para el filtro seleccionado.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Tipo</th>
                <th>Ruta</th>
                <th>Salida (Origen)</th>
                <th>Llegada (Destino)</th>
                <th>Estado</th>
                <th>Cupos</th>
                <th>Tarifa Económica</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {flights.map((f) => {
                const badgeClass =
                  f.estado === "PROGRAMADO"
                    ? "badge-programado"
                    : f.estado === "REALIZADO"
                    ? "badge-realizado"
                    : "badge-cancelado";

                const isProgramado = f.estado === "PROGRAMADO";

                return (
                  <tr key={f.id}>
                    <td>
                      <strong>{f.codigo_vuelo}</strong>
                    </td>
                    <td>{f.tipo_vuelo}</td>
                    <td>
                      {f.origen} → {f.destino}
                    </td>
                    <td>
                      {f.fecha_salida} <br />
                      <small style={{ color: "var(--text-muted)" }}>{f.hora_salida}</small>
                    </td>
                    <td>
                      {f.fecha_llegada} <br />
                      <small style={{ color: "var(--text-muted)" }}>{f.hora_llegada}</small>
                    </td>
                    <td>
                      <span className={`badge ${badgeClass}`}>{f.estado}</span>
                    </td>
                    <td>
                      {f.cupos_disponibles_economica + f.cupos_disponibles_primera} /{" "}
                      {f.capacidad_total}
                    </td>
                    <td>${Number(f.costo_persona_economica).toLocaleString("es-CO")}</td>
                    <td>
                      {isProgramado && isAdmin ? (
                        <div className="actions">
                          <button
                            className="btn o"
                            onClick={() => onOpenEdit(f)}
                            style={{ padding: "4px 8px", fontSize: "0.8rem" }}
                          >
                            Editar
                          </button>
                          <button
                            className="btn r"
                            onClick={() => onOpenCancel(f)}
                            style={{ padding: "4px 8px", fontSize: "0.8rem" }}
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                          —
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

